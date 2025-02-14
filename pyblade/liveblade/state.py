from functools import partial
from typing import Any, Callable, Dict, List, Set
import threading

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
        """Track dependencies for computed properties"""
        self._dependencies.add(key)
    
    def get(self, key: str) -> Any:
        """Get a value from state, tracking dependencies"""
        self._track_dependency(key)
        return self._state.get(key)
    
    def set(self, key: str, value: Any):
        """Set a value in state and trigger updates"""
        with self._lock:
            old_value = self._state.get(key)
            if old_value != value:
                self._state[key] = value
                self._trigger_computed_updates(key)
                self._trigger_watchers(key, old_value, value)
    
    def computed(self, name: str) -> Callable:
        """Decorator for computed properties"""
        def decorator(func: Callable) -> Callable:
            self._computed[name] = Computed(func)
            return func
        return decorator
    
    def watch(self, key: str, callback: Callable, immediate: bool = False):
        """Add a watcher for a specific key"""
        if key not in self._watchers:
            self._watchers[key] = []
        
        watcher = Watcher(callback, immediate)
        self._watchers[key].append(watcher)
        
        if immediate:
            callback(self.get(key), None)
    
    def _trigger_computed_updates(self, changed_key: str):
        """Trigger updates for computed properties that depend on the changed key"""
        for name, computed in self._computed.items():
            if changed_key in computed.dependencies:
                computed.dirty = True
                # Clear cache
                computed.cache = None
    
    def _trigger_watchers(self, key: str, old_value: Any, new_value: Any):
        """Trigger watchers for a specific key"""
        if key in self._watchers:
            for watcher in self._watchers[key]:
                watcher.callback(new_value, old_value)
    
    def evaluate_computed(self, name: str) -> Any:
        """Evaluate a computed property"""
        computed = self._computed.get(name)
        if not computed:
            raise KeyError(f"No computed property named {name}")
        
        if computed.dirty or computed.cache is None:
            # Clear current dependencies
            self._dependencies = set()
            
            # Evaluate the computed property
            computed.cache = computed.func(self)
            
            # Store dependencies
            computed.dependencies = self._dependencies.copy()
            computed.dirty = False
            
            # Clear current dependencies
            self._dependencies = set()
        
        return computed.cache

# Example usage in a component:
class ComponentState:
    def __init__(self):
        self.state = StateManager()
        
        # Initialize some state
        self.state.set('count', 0)
        
        # Define a computed property
        @self.state.computed('double_count')
        def double_count(state):
            return state.get('count') * 2
        
        # Add a watcher
        self.state.watch('count', self._on_count_change, immediate=True)
    
    def _on_count_change(self, new_value, old_value):
        print(f"Count changed from {old_value} to {new_value}")
    
    def increment(self):
        current = self.state.get('count')
        self.state.set('count', current + 1)
        
    def get_double_count(self):
        return self.state.evaluate_computed('double_count')
