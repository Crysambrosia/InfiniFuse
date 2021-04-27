from abc import ABC, abstractmethod

class Cache(ABC):
    """Defines basic functions for objects that use a cache"""
    
    def __delitem__(self, key):
        """Remove entry <key> from cache"""
        key = self.convert_key(key = key)
        self.discard(key)
    
    def __getitem__(self, key):
        """Return entry <key> from cache, load if absent"""
        key = self.convert_key(key = key)
        
        if key not in self._cache:
            self.load(key)
        
        return self._cache[key]
    
    def __setitem__(self, key, value):
        """Set data in cache for entry <key> to <value>"""
        key = self.convert_key(key = key)
        self._cache[key] = self.convert_value(value = value)
    
    def discard(self, key):
        """Discard cache entry <key>"""
        key = self.convert_key(key = key)
        del self._cache[key]
    
    def discard_all(self):
        """Discard all cache entries"""
        self._cache = {}
    
    def load(self, key):
        """Load data for entry <key> into cache"""
        key = self.convert_key(key = key)
        self._cache[key] = self.read(key)

    @abstractmethod
    def read(self, key):
        """Return data for entry <key> from underlying data source"""
        pass

    def save(self, key):
        """Save changes for enty <key> and remove it from cache"""
        key = self.convert_key(key = key)
        
        if key not in self._cache:
            return
        
        self.write(key = key, value = self._cache[key])
        self.discard(key)
    
    def save_all(self):
        """Save all changes in self._cache"""
        for key in self._cache:
            self.write(key = key, value = self._cache[key])
        
        self.discard_all()
    
    @abstractmethod
    def convert_key(self, key):
        """Return converted <key> for use with this Cache subclass.
        Raise an error if <key> is invalid / incompatible
        """
        pass
    
    @abstractmethod
    def convert_value(self, value):
        """Return converted <value> for use with this Cache subclass
        Raise an error if <value> is invalid / incompatible
        """
        pass
    
    @abstractmethod
    def write(self, key, value):
        """Save <value> as data for entry <key> to underlying data source"""
        pass