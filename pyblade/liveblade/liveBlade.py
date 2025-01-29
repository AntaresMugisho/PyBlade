import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any, Callable, Dict, List, Set

from django.core.cache import cache
from django.http import JsonResponse

from .base import Component

# Dictionary to store initialized components by their IDs
components = {}


class Computed:
    def __init__(self, func: Callable):
        self.func = func
        self.cache = None
        self.dirty = True
        self.dependencies: Set[str] = set()


class Watcher:
    def __init__(self, callback: Callable, immediate: bool = False):
        self.callback = callback
        self.immediate = immediate
        self.old_value = None


class StateManager:
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._computed: Dict[str, Computed] = {}
        self._watchers: Dict[str, List[Watcher]] = {}
        self._dependencies: Set[str] = set()
        self._lock = threading.Lock()

    def _track_dependency(self, key: str):
        self._dependencies.add(key)

    def get(self, key: str) -> Any:
        self._track_dependency(key)
        return self._state.get(key)

    def set(self, key: str, value: Any):
        with self._lock:
            old_value = self._state.get(key)
            if old_value != value:
                self._state[key] = value
                self._trigger_computed_updates(key)
                self._trigger_watchers(key, old_value, value)

    def computed(self, name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._computed[name] = Computed(func)
            return func

        return decorator

    def watch(self, key: str, callback: Callable, immediate: bool = False):
        if key not in self._watchers:
            self._watchers[key] = []
        watcher = Watcher(callback, immediate)
        self._watchers[key].append(watcher)
        if immediate:
            callback(self.get(key), None)

    def _trigger_computed_updates(self, changed_key: str):
        for name, computed in self._computed.items():
            if changed_key in computed.dependencies:
                computed.dirty = True
                computed.cache = None

    def _trigger_watchers(self, key: str, old_value: Any, new_value: Any):
        if key in self._watchers:
            for watcher in self._watchers[key]:
                watcher.callback(new_value, old_value)

    def evaluate_computed(self, name: str) -> Any:
        computed = self._computed.get(name)
        if not computed:
            raise KeyError(f"No computed property named {name}")

        if computed.dirty or computed.cache is None:
            self._dependencies = set()
            computed.cache = computed.func(self)
            computed.dependencies = self._dependencies.copy()
            computed.dirty = False
            self._dependencies = set()

        return computed.cache


class BladeCache:
    def __init__(self, timeout=300):
        self.timeout = timeout
        self.prefix = "blade_cache:"

    def _generate_key(self, component_id, method_name, params):
        key_parts = [str(component_id), method_name]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        key_string = ":".join(key_parts)
        return f"{self.prefix}{hashlib.md5(key_string.encode()).hexdigest()}"

    def get(self, component_id, method_name, params=None):
        key = self._generate_key(component_id, method_name, params)
        return cache.get(key)

    def set(self, component_id, method_name, params, value):
        key = self._generate_key(component_id, method_name, params)
        cache.set(key, value, self.timeout)

    def invalidate(self, component_id, method_name=None):
        if method_name:
            key = self._generate_key(component_id, method_name, None)
            cache.delete(key)


class BatchProcessor:
    def __init__(self, max_batch_size=10):
        self.max_batch_size = max_batch_size
        self.batch_queue = []
        self.executor = ThreadPoolExecutor(max_workers=3)

    def add_to_batch(self, component, method_name, params):
        if len(self.batch_queue) >= self.max_batch_size:
            self.process_batch()

        self.batch_queue.append({"component": component, "method": method_name, "params": params})

    def process_batch(self):
        if not self.batch_queue:
            return []

        futures = []
        for request in self.batch_queue:
            future = self.executor.submit(
                self._process_single_request, request["component"], request["method"], request["params"]
            )
            futures.append(future)

        self.batch_queue = []
        return [future.result() for future in futures]

    def _process_single_request(self, component, method_name, params):
        try:
            method = getattr(component, method_name)
            return {
                "success": True,
                "component": component.id,
                "method": method_name,
                "result": method(params) if params else method(),
            }
        except Exception as e:
            return {"success": False, "component": component.id, "method": method_name, "error": str(e)}


def cached_blade(timeout=300):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache_instance = BladeCache(timeout=timeout)
            cache_key = cache_instance._generate_key(self.id, func.__name__, args[0] if args else None)
            cached_result = cache.get(cache_key)

            if cached_result is not None:
                return cached_result

            result = func(self, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator


# def initialize_components():
#     """
#     Initializes all components by dynamically loading them from the 'components' package.
#     It checks if the class is a subclass of Component and instantiates it, adding
#     it to the `components` dictionary.
#     """
#     package = "liveblade"
#     for _, module_name, _ in pkgutil.iter_modules([package]):
#         # Dynamically import each module in the 'components' package
#         module = importlib.import_module(f"{package}.{module_name}")
#         for name in dir(module):
#             # For each class in the module, check if it is a subclass of Component
#             cls = getattr(module, name)
#             if isinstance(cls, type) and issubclass(cls, Component) and cls is not Component:
#                 # Create an instance of the component and add it to the components dictionary
#                 component_instance = cls(name.lower())
#                 components[component_instance.id] = component_instance
#                 print(component_instance.id, ' id')


# # Initialize all components when the script is loaded
# initialize_components()


def LiveBlade(request):
    """
    Handles the POST request to interact with a specific component's method.
    It extracts data from the request, locates the appropriate component,
    and calls the requested method with the provided parameters.

    Args:
        request: The HTTP request object containing POST data.
    """
    if request.method == "POST":
        try:
            # Lire les données JSON du corps de la requête
            data = json.loads(request.body.decode("utf-8"))
            print("Received data:", data)

            # Get the component ID and method name from the request
            component_id = data.get("componentId")
            method_name = data.get("method")
            print(f"Component ID: {component_id}, Method: {method_name}")

            # Get the component instance
            component = Component.instances.get(f"liveblade.{component_id}")
            print(f"Component instances: {Component.instances}")
            print(f"Component comp: {component}")

            if component is None:
                error_message = f"Component with ID {component_id} not found"
                print(error_message)
                return JsonResponse({"error": error_message}, status=404)

            if not hasattr(component, method_name):
                error_message = f"Method {method_name} not found in component {component_id}"
                print(error_message)
                return JsonResponse({"error": error_message}, status=404)

            # Call the component method
            method = getattr(component, method_name)
            method()

            # Re-render the component
            result = component.render()
            return JsonResponse({"data": result}, status=200)

        except json.JSONDecodeError as e:
            print("JSON Decode Error:", str(e))
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)
