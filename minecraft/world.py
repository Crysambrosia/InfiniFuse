from .dimension import Dimension
from .datfile import DatFile
import os

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
    
    @property
    def map_idcounts(self):
        """Returns last used map ID"""
        path = os.path.join(self.folder, 'data', 'idcounts.dat')
        return DatFile.open(path)['']['data']['map']