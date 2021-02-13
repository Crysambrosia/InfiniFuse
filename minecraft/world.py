from minecraft import McaFile
import os

class Dimension():
    """A dimension of a minecraft world"""
    
    def __init__(self, folder : str):
    
        self.folder = folder
        """Folder containing this dimension's .mca files"""
    
        self._cache = {}
        """Cache containing loaded region files"""
    
    def __delitem__(self, key):
        """Remove item from cache"""
        del self._cache[x][z]
    
    def __getitem__(self, key):
        x, z = self.check_key(key)
        if x not in self._cache or z not in self._cache[x]:
            self.load_region(x,z)
        return self._cache[x][z]
    
    def __setitem__(self, key, value):
        if not isinstance(value, McaFile):
            raise ValueError(f'Value must be McaFile, not {value}')
        x, z = self.check_key(key)
        self._cache.update({x:{z:value}})
    
    @staticmethod
    def check_key(key):
        """Check if <key> is valid and return it"""
        if not isinstance(key, tuple) and len(key) == 2:
            raise KeyError(f'Key must be coordinates of region, not {key}')
        return key
    
    def load_region(self, x : int, z : int):
        """Load region at <x> <y> to cache"""
        self[x,z] = McaFile(x = x, z = z, folder = self.folder)
    
    def save_region(self, x : int, z : int):
        """Save region at <x> <y> and remove it from cache"""
        self[x,z].save()
        del self[x,z]

class World():
    """Interface for minecraft worlds"""
    def __init__(self, folder : str):
        
        self.folder = folder
        """Folder containing the world files"""
        
        self.dimensions = {}
        self.dimensions['minecraft:overworld'] = Dimension(os.path.join(folder, 'region'))
        self.dimensions['minecraft:the_end'] = Dimension(os.path.join(folder, 'DIM1','region'))
        self.dimensions['minecraft:the_nether'] = Dimension(os.path.join(folder, 'DIM-1', 'region'))
    
    @classmethod
    def from_saves(cls, name : str):
        """Open a world from name of save folder"""
        appdata = os.environ['APPDATA']
        folder = os.path.join(appdata, '.minecraft', 'saves', name)
        return cls(folder)