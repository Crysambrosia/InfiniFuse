from .mcafile import McaFile
import os

class Dimension():
    """A dimension of a minecraft world"""
    
    def __init__(self, folder : str):
    
        self.folder = folder
        """Folder containing this dimension's .mca files"""
    
        self._cache = {}
        """Cache containing loaded chunks files"""
    
    def __delitem__(self, key):
        """Remove item from cache"""
        if isinstance(key, tuple) and len(key) == 2:
            x, z = key
            del self._cache[(x, z)]
    
    def __getitem__(self, key):
        if isinstance(key, tuple) and len(key) == 2:
            x, z = key
            if (x, z) not in self._cache:
                self.load(x, z)
            return self._cache[(x, z)]
    
    def __setitem__(self, key, value):
        if not isinstance(value, Chunk):
            raise ValueError(f'Value must be minecraft.Chunk, not {value}')
        
        if isinstance(key, tuple) and len(key) == 2:
            x, z = key
            self._cache[(x, z)] = value
    
    def load(self, x : int, z : int):
        """Load chunk at <x> <y> to cache"""
        self[(x, z)] = Chunk.open(folder = self.folder, x = x, z = z)
    
    def load_all(self):
        """Load all chunks from this dimension
        
        Warning : This can easily overload RAM
        """
        for fileName in os.listdir(self.folder):
        
            if os.path.splitext(fileName)[1] == '.mca':
            
                file = McaFile(path = os.path.join(self.folder, fileName))
                _, regionX, regionZ, _ = fileName.split('.')
                print(f'Found region {regionX} {regionZ}')
    
    def unload(self, x : int, z : int):
        """Save chunk at <x> <z> and remove it from cache"""
        self[(x, z)].save(folder = self.folder)
        del self[(x, z)]
    
    def unload_all(self):
    
        keys = [key for key in self._cache]
        # Copy keys because Python doesn't want the cache to change size during unloading
        
        for key in keys:
            x, y, z = key
            self.unload(x, y, z)