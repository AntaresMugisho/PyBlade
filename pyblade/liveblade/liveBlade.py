import importlib
import pkgutil
from django.http import JsonResponse, HttpResponseRedirect
import json
from urllib.parse import urlencode
from .base import Component
from functools import wraps
from typing import Any, Callable, Dict, List, Set
import threading
from django.core.cache import cache
import hashlib
from concurrent.futures import ThreadPoolExecutor

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
        
        self.batch_queue.append({
            'component': component,
            'method': method_name,
            'params': params
        })
    
    def process_batch(self):
        if not self.batch_queue:
            return []
        
        futures = []
        for request in self.batch_queue:
            future = self.executor.submit(
                self._process_single_request,
                request['component'],
                request['method'],
                request['params']
            )
            futures.append(future)
        
        self.batch_queue = []
        return [future.result() for future in futures]
    
    def _process_single_request(self, component, method_name, params):
        try:
            method = getattr(component, method_name)
            return {
                'success': True,
                'component': component.id,
                'method': method_name,
                'result': method(params) if params else method()
            }
        except Exception as e:
            return {
                'success': False,
                'component': component.id,
                'method': method_name,
                'error': str(e)
            }

def cached_blade(timeout=300):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache_instance = BladeCache(timeout=timeout)
            cache_key = cache_instance._generate_key(
                self.id,
                func.__name__,
                args[0] if args else None
            )
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            result = func(self, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator

def initialize_components():
    """
    Initializes all components by dynamically loading them from the 'components' package. 
    It checks if the class is a subclass of Component and instantiates it, adding 
    it to the `components` dictionary.
    """
    package = 'components'
    for _, module_name, _ in pkgutil.iter_modules([package]):
        # Dynamically import each module in the 'components' package
        module = importlib.import_module(f"{package}.{module_name}")
        for name in dir(module):
            # For each class in the module, check if it is a subclass of Component
            cls = getattr(module, name)
            if isinstance(cls, type) and issubclass(cls, Component) and cls is not Component:
                # Create an instance of the component and add it to the components dictionary
                component_instance = cls(name.lower())  
                components[component_instance.id] = component_instance
                print(component_instance.id, ' id')

# Initialize all components when the script is loaded
initialize_components()

# Initialisation du gestionnaire de batch
batch_processor = BatchProcessor(max_batch_size=10)
blade_cache = BladeCache()

def LiveBlade(request):
    if request.method == 'POST':
        try:
            data = request.POST.dict()
            files_data = request.FILES

            print('Received data:', data)

            component_id = data.get('component')
            method_name = data.get('method')
            is_batch = data.get('batch', False)
            is_lazy = data.get('lazy', False)

            print(f"Component ID: {component_id}, Method: {method_name}")

            component = components.get(component_id)

            if component is None:
                error_message = f"Component with ID {component_id} not found"
                print(error_message)
                params = urlencode({'error': error_message})
                return HttpResponseRedirect(f'/bladeError?{params}')
            
            if not hasattr(component, method_name):
                error_message = f"Method {method_name} not found in component {component_id}"
                print(error_message)
                params = urlencode({'error': error_message})
                return HttpResponseRedirect(f'/bladeError?{params}')

            # Vérifier le cache
            cached_result = blade_cache.get(component_id, method_name, data)
            if cached_result and not is_lazy:
                return JsonResponse({'html': cached_result, 'cached': True})

            formatted_params = {}
            print(files_data, 'data')
            
            for key in data.keys():
                if key.startswith('param'):
                    formatted_params[key] = data[key]
                    param = json.loads(formatted_params.get("param0"))
                    param = param.get('param', []) if not isinstance(param, list) else param
                    for i in param:
                        if isinstance(i, dict):
                            value = i.get("value")
                            if value and value.startswith("$"):
                                state_value = component.state.get(value[1:])
                                if state_value is not None:
                                    i['value'] = state_value
                                    i['name'] = i['name'][1:]
                    formatted_params = param

            if files_data:
                print(f"Received files: {files_data}")
                formatted_params['files'] = files_data

            # Traitement par lots si demandé
            if is_batch:
                batch_processor.add_to_batch(component, method_name, formatted_params)
                if len(batch_processor.batch_queue) >= batch_processor.max_batch_size:
                    results = batch_processor.process_batch()
                    return JsonResponse({'batch_results': results})
                return JsonResponse({'queued': True})

            # Exécution normale
            html_response = ''
            if len(formatted_params) == 0:
                html_response = method()
                if html_response.get("redirect"):
                    return HttpResponseRedirect(html_response.get("url"))
            else:
                html_response = method(formatted_params)

            # Mettre en cache le résultat
            if not is_lazy:
                blade_cache.set(component_id, method_name, data, html_response)

            return JsonResponse({'html': html_response})

        except (ValueError, KeyError, TypeError) as e:
            error_message = f"Error processing request: {e}"
            print(error_message)
            params = urlencode({'error': error_message})
            return HttpResponseRedirect(f'/bladeError?{params}')
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
