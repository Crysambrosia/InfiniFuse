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
    
    def all_chunk_coords(self):
        """Return coord tuples for all chunks present in this dimension"""
        
        allCoords = []
        
        for fileName in os.listdir(self.folder):
            print(f'Dealing with {fileName}...')
            
            if os.path.splitext(fileName)[1] == '.mca':
                with McaFile(os.path.join(self.folder, fileName)) as f:
                    for chunk in f:
                        if chunk is not None:
                            allCoords.append(chunk.coords_chunk)
        return allCoords
    
    def check_key(self, key):
        """Raise an exception if <key> is invalid"""
        if not isinstance(key, tuple):
            raise TypeError(f'Key must be tuple, not {type(key)}')
    
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
    
    def map_test(self):
        """Create a pixel map of contained chunks within this dimension"""
        
        Xcoords = []
        Zcoords = []
        
        for fileName in os.listdir(self.folder):
            if os.path.splitext(fileName)[1] == '.mca':
                print(f'File {fileName}...')
                f = McaFile(os.path.join(self.folder, fileName))
                x, z = f.coords_chunk
                Xcoords.append(x)
                Zcoords.append(z)
        
        minX = min(Xcoords)
        maxX = max(Xcoords)
        minZ = min(Zcoords)
        maxZ = max(Zcoords)
        print(f'From {minX} {minZ} to {maxX} {maxZ}')
        
        width = abs(minX) + abs(maxX)
        height = abs(minZ) + abs(maxZ)
        
        data = []
        for z in range(height): 
            row = []
            print(f'row {z} of {height}')
            for x in range(width):
            
                if (minX + x, minZ + z) in self:
                    row.append(255)
                else:
                    row.append(0)
            
            data.append(row)
        
        with open(r'C:\Users\ambro\Documents\test.png', mode = 'w+b') as f:
            print('Making PNG...')
            f.write(util.png.makePNG(data))
    
    def save(self, key):
        """Save chunk at <x> <z> and remove it from cache"""
        
        if self[key] is not None:
            McaFile.write_chunk(folder = self.folder, value = self[key])
        
        del self[key]