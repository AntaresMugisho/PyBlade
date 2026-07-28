import importlib
from typing import Type, Dict, Any


class ComponentRegistry:
    """
    Central registry for PyBlade Live components.
    
    Caches Python class references in memory to enable O(1) lookups
    during AJAX requests without requiring re-imports or state persistence.
    """

    def __init__(self) -> None:
        self._components: Dict[str, Type[Any]] = {}

    def register(self, name_or_path: str, component_class: Type[Any]) -> None:
        """
        Registers a component class under a given key or class path.

        :param name_or_path: Component alias or full class path (e.g., 'myapp.components.counter.Counter').
        :param component_class: The actual Python class reference.
        """
        self._components[name_or_path] = component_class

    def get(self, class_path: str) -> Type[Any]:
        """
        Retrieves a component class by its path.
        Uses in-memory cache if available; otherwise, lazily imports the module.

        :param class_path: Full Python path of the component class.
        :return: The resolved Python class object.
        :raises ValueError: If the class or module cannot be imported.
        """
        # 1. Fast lookup from memory cache
        if class_path in self._components:
            return self._components[class_path]

        # 2. Lazy resolution via importlib on first access
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            # Cache the class reference for subsequent requests
            self._components[class_path] = cls
            return cls
        except (ValueError, ImportError, AttributeError) as err:
            raise ValueError(f"PyBlade component '{class_path}' could not be resolved.") from err


# Global singleton instance
registry = ComponentRegistry()