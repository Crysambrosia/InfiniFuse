from abc import ABC, abstractmethod

class Cache(ABC):
    """Defines basic functions for objects that use a cache"""
    
    def discard(self, key):
        """Discard cache entry <key>"""
        del self._cache[key]
    
    def discard_all(self):
        """Discard all cache entries"""
        self.cache = {}
    
    def save_all(self):
        """Save all changes in self._cache"""
        
        keys = [key for key in self._cache]
        # Copy keys because Python doesn't want the cache to change size during saveing
        
        for key in keys:
            self.save(key)