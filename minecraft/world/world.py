from .dimension import Dimension
from .mapmanager import MapManager
from .playermanager import PlayerManager
import logging
import os

class World():
    """Interface for minecraft worlds"""
    
    __slots__ = ['folder', 'dimensions', 'maps', 'players']
    
    def __init__(self, folder : str):
        
        self.folder = folder
        """Folder containing the world files"""
        
        self.dimensions = {}
        self.dimensions['minecraft:overworld'] = Dimension(os.path.join(folder, 'region'))
        self.dimensions['minecraft:the_end'] = Dimension(os.path.join(folder, 'DIM1','region'))
        self.dimensions['minecraft:the_nether'] = Dimension(os.path.join(folder, 'DIM-1', 'region'))
        self.maps = MapManager(folder = os.path.join(self.folder, 'data'))
        self.players = PlayerManager(folder = self.folder)
    
    @classmethod
    def from_saves(cls, name : str):
        """Open a world from name of save folder"""
        appdata = os.environ['appdata']
        folder = os.path.join(appdata, '.minecraft', 'saves', name)
        return cls(folder)
    
    def png_maps(self, folder : str = None, size : int = 256, skipEnd : bool = False):
        """Make PNG maps of all dimensions of this world. Each pixel will represent a chunk.
        
        <folder>  : path to folder in which to save the PNGs. Defaults to this world's folder
        <size>    : Side length of the nether map will be the closest multiple of 32 to this
                    Overworld will be 8 times larger to cover the same area
                    Defaults to 256
        <skipEnd> : Whether the end dimension should be skipped, defaults to False
        """
        folder = folder or self.folder
        
        for dimensionName, dimension in self.dimensions.items():
            if skipEnd and dimensionName == 'minecraft:the_end':
                continue
            
            if dimensionName == 'minecraft:overworld':
                actualSize = size * 8
            else:
                actualSize = size
            
            path = os.path.join(folder, f'{dimensionName.split(":")[1]}_map.png')
            
            logging.info(f'Making map of {dimensionName}...')
            with open(path, mode = 'wb') as f:
                f.write(dimension.png_map(size = actualSize).content())
        
        logging.info('Done !')