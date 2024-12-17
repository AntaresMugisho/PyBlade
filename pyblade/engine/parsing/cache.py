"""
Template caching implementation for improved performance.
"""
import hashlib
from typing import Dict, Optional, Any
from datetime import datetime, timedelta


class TemplateCache:
    """
    A caching system for parsed templates to improve performance by avoiding
    repeated parsing of unchanged templates.
    """
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self._cache: Dict[str, dict] = {}
        self._max_size = max_size
        self._ttl = ttl  # Time to live in seconds

    def get(self, template: str, context: dict) -> Optional[str]:
        """
        Retrieve a cached template if it exists and is valid.
        
        Args:
            template: The template string
            context: The context dictionary
            
        Returns:
            The cached rendered template or None if not found/invalid
        """
        cache_key = self._generate_cache_key(template, context)
        cached = self._cache.get(cache_key)
        
        if not cached:
            return None
            
        # Check if cache has expired
        if datetime.now() - cached['timestamp'] > timedelta(seconds=self._ttl):
            del self._cache[cache_key]
            return None
            
        return cached['result']

    def set(self, template: str, context: dict, result: str) -> None:
        """
        Cache a template rendering result.
        
        Args:
            template: The template string
            context: The context dictionary
            result: The rendered template result
        """
        # Enforce cache size limit
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest = min(self._cache.items(), key=lambda x: x[1]['timestamp'])
            del self._cache[oldest[0]]
            
        cache_key = self._generate_cache_key(template, context)
        self._cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }

    def invalidate(self, template: str, context: dict) -> None:
        """
        Invalidate a specific template cache entry.
        
        Args:
            template: The template string
            context: The context dictionary
        """
        cache_key = self._generate_cache_key(template, context)
        self._cache.pop(cache_key, None)

    def clear(self) -> None:
        """Clear all cached templates."""
        self._cache.clear()

    def _generate_cache_key(self, template: str, context: dict) -> str:
        """
        Generate a unique cache key for a template and its context.
        
        Args:
            template: The template string
            context: The context dictionary
            
        Returns:
            A unique hash string for the template and context
        """
        # Convert context to a stable string representation
        context_str = str(sorted(context.items()))
        combined = f"{template}:{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    @property
    def size(self) -> int:
        """Get the current number of cached templates."""
        return len(self._cache)
