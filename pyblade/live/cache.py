from functools import wraps
import hashlib
import json
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor

class BladeCache:
    def __init__(self, timeout=300): 
        self.timeout = timeout
        self.prefix = "blade_cache:"
    
    def _generate_key(self, component_id, method_name, params):
        # Create a unique key based on component, method and params
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
        else:
            # Invalidate all cache for this component
            # Note: This is a simplified version. In production, you might want to
            # keep track of all keys for a component for proper invalidation
            pass

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
        
        # Process all requests in parallel
        futures = []
        for request in self.batch_queue:
            future = self.executor.submit(
                self._process_single_request,
                request['component'],
                request['method'],
                request['params']
            )
            futures.append(future)
        
        # Clear the queue
        self.batch_queue = []
        
        # Return results
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

# Decorator for caching component methods
def cached_blade(timeout=300):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache_instance = BladeCache(timeout=timeout)
            
            # Try to get from cache
            cache_key = cache_instance._generate_key(
                self.id,
                func.__name__,
                args[0] if args else None
            )
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # If not in cache, compute and store
            result = func(self, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator
