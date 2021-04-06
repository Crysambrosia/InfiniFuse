from .chunk import Chunk
from .mcafile import McaFile
import os
import util

class Dimension(util.Cache):
    """A dimension of a minecraft world"""
    
    def __init__(self, folder : str):
    
        self.folder = folder
        """Folder containing this dimension's .mca files"""
    
        self._cache = {}
        """Cache containing loaded chunks"""
    
    def __contains__(self, key):
        """Returns whether chunk <key> exists in this dimension"""
        if isinstance(key, tuple) and len(key) == 2:
            x, z = key
            return McaFile.chunk_exists(folder = self.folder, x = x, z = z)
    
    def __delitem__(self, key):
        """Remove item from cache"""
        
        if isinstance(key, tuple) and len(key) == 2:
            del self._cache[key]
    
    def __getitem__(self, key):
        """Return a chunk from two coords, and a block from three"""
        self.check_key(key)
        
        if len(key) == 2:
        
            if key not in self._cache:
                self.load(key)
            
            return self._cache[key]
            
        elif len(key) == 3:
            x, y, z = key
            chunkX, x = divmod(x, 16)
            chunkZ, z = divmod(z, 16)
            
            return self[chunkX, chunkZ][x, y, z]
    
    def __setitem__(self, key, value):
        """"""
        self.check_key(key)
        
        if len(key) == 2:
        
            if value is not None and not isinstance(value, Chunk):
                raise ValueError(f'Value must be minecraft.Chunk, not {value}')
            
            self._cache[key] = value
            
        elif len(key) == 3:
            x, y, z = key
            chunkX, x = divmod(x, 16)
            chunkZ, z = divmod(z, 16)
            self[chunkX, chunkZ][x, y, z] = value
    
    def check_key(self, key):
        """Raise an exception if <key> is invalid"""
        if not isinstance(key, tuple):
            raise TypeError(f'Key must be tuple, not {type(key)}')
    
    def borders(self):
        """Return min and max X/Z chunk coords for this dimension"""
        
        minX = 0
        maxX = 0
        minZ = 0
        maxZ = 0
        
        for fileName in os.listdir(self.folder):
            if os.path.splitext(fileName)[1] == '.mca':
                f = McaFile(os.path.join(self.folder, fileName))
                x, z = f.coords_chunk
                minX = min(minX, x)
                minZ = min(minZ, z)
                maxX = max(maxX, x + 512)
                maxZ = max(maxZ, z + 512)
        
        return (minX, minZ, maxX, maxZ)
    
    def load(self, key):
        """Load chunk at <x> <y> to cache"""
        x, z = key
        self[key] = McaFile.read_chunk(folder = self.folder, x = x, z = z)
    
    def load_all(self):
        """Load all chunks from this dimension
        
        Warning : This can easily overload RAM
        """
        for fileName in os.listdir(self.folder):
        
            if os.path.splitext(fileName)[1] == '.mca':
            
                path = os.path.join(self.folder, fileName)
                with McaFile(path) as f:
                    for chunk in f:
                        if chunk is not None:
                            coords = chunk.coords_chunk
                            self[coords] = chunk
    
    def save(self, key):
        """Save chunk at <x> <z> and remove it from cache"""
        
        if self[key] is not None:
            McaFile.write_chunk(folder = self.folder, value = self[key])
        
        del self[key]