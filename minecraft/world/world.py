from .dimension import Dimension
from .mapmanager import MapManager
from minecraft.datfile import DatFile
import os

class World():
    """Interface for minecraft worlds"""
    
    __slots__ = ['folder', 'dimensions', 'maps']
    
    def __init__(self, folder : str):
        
        self.folder = folder
        """Folder containing the world files"""
        
        self.dimensions = {}
        self.dimensions['minecraft:overworld'] = Dimension(os.path.join(folder, 'region'))
        self.dimensions['minecraft:the_end'] = Dimension(os.path.join(folder, 'DIM1','region'))
        self.dimensions['minecraft:the_nether'] = Dimension(os.path.join(folder, 'DIM-1', 'region'))
        self.maps = MapManager(folder = os.path.join(self.folder, 'data'))
    
    @classmethod
    def from_saves(cls, name : str):
        """Open a world from name of save folder"""
        appdata = os.environ['APPDATA']
        folder = os.path.join(appdata, '.minecraft', 'saves', name)
        return cls(folder)