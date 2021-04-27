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
        if len(key) == 2:
            util.Cache.__getitem__(self, key)
            
        elif len(key) == 3:
            x, y, z = key
            chunkX, x = divmod(x, 16)
            chunkZ, z = divmod(z, 16)
            
            return self[chunkX, chunkZ][x, y, z]
    
    def __iter__(self):
        """A generator that extracts every existing chunk from this dimension"""
        for fileName in os.listdir(self.folder):
            if os.path.splitext(fileName)[1] == '.mca':
                with McaFile(os.path.join(self.folder, fileName)) as f:
                    for chunk in f:
                        if chunk is not None:
                            yield chunk
    
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
    
    def convert_key(self, key):
        """Convert <key> to a tuple of ints"""
        key = tuple([int(i) for i in key])
        return key
    
    def convert_value(self, value):
        """Make sure value is a McaFile"""
        if not isinstance(value, McaFile):
            raise TypeError(f'Value must be McaFile, not {value}')
        return value
    
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
    
    def read(self, key):
        """Return McaFile at coords in key"""
        xRegion, zRegion = key
        return McaFile(path = os.path.join(self.folder, f'r.{xRegion}.{zRegion}.mca'))
    
    def save(self, key):
        """Save chunk at <x> <z> and remove it from cache"""
        
        if self[key] is not None:
            McaFile.write_chunk(folder = self.folder, value = self[key])
        
        del self[key]