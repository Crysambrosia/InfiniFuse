from .chunk import Chunk
from .mcafile import McaFile
from util.png import makePNG
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
        self[(x, z)] = McaFile.read_chunk(folder = self.folder, x = x, z = z)
    
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
        
        minX = 0
        maxX = 0
        minZ = 0
        maxZ = 0
        
        all_coords = []
        
        for fileName in os.listdir(self.folder):
            
            print(f'Dealing with {fileName}...')
            
            if os.path.splitext(fileName)[1] == '.mca':
            
                path = os.path.join(self.folder, fileName)
                
                with McaFile(path) as f:
                    for chunk in f:
                        if chunk is not None:
                        
                            newCoords = chunk.coords_chunk
                            all_coords.append(newCoords)
                            
                            if   newCoords[0] < minX:
                                minX = newCoords[0]
                            elif newCoords[0] > maxX:
                                maxX = newCoords[0]
                            
                            if   newCoords[1] < minZ:
                                minZ = newCoords[1]
                            elif newCoords[1] > maxZ:
                                maxZ = newCoords[1]
        
        width = abs(minX) + abs(maxX)
        height = abs(minZ) + abs(maxZ)
        
        data = []
        for z in range(height):
        
            row = []
            
            for x in range(width):
            
                if (minX + x, minZ + z) in all_coords:
                    row.append(255)
                else:
                    row.append(0)
            
            data.append(row)
        
        with open(r'C:\Users\ambro\Documents\test.png', mode = 'w+b') as f:
            f.write(makePNG(data))
    
    def unload(self, x : int, z : int):
        """Save chunk at <x> <z> and remove it from cache"""
        McaFile.write_chunk(folder = self.folder, value = self[(x, z)])
        del self[(x, z)]
    
    def unload_all(self):
    
        keys = [key for key in self._cache]
        # Copy keys because Python doesn't want the cache to change size during unloading
        
        for key in keys:
            x, z = key
            self.unload(x, z)