from minecraft.datfile import DatFile
import json
import minecraft.TAG as TAG
import os

class PlayerManager():
    """Handles accessing and modifying player data and stats"""
    
    def __init__(self, folder : str):
        self.folder = folder
    
    def __iter__(self):
        """Return all players from this world
        
        Iterates through UUIDs found in the playerdata folder
        """
        
        for name in os.listdir(os.path.join(self.folder, 'playerdata')):
            basename = os.path.basename(name)
            uuid, ext = os.path.splitext(basename)
            if ext == '.dat':
                yield self[uuid]
            else:
                continue
    
    def __getitem__(self, key):
        """Return a player's data from a hyphenated-hexadecimal formatted UUID"""
        
        uuid = key
        
        dataPath = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
        with DatFile(dataPath) as f:
            playerdata = TAG.Compound(f)
        
        statsPath = os.path.join(self.folder, 'stats', f'{uuid}.json')
        with open(statsPath, mode = 'r') as f:
            stats = json.load(f)
        
        return {'playerdata' : playerdata, 'stats' : stats, 'uuid' : uuid}
    
    def  __setitem__(self, key, value):
        """Write player data for given UUID in <key>
        
        Please provide data in the same format as __getitem__ returns
        """
        uuid = key
        
        if 'playerdata' in value:
            dataPath = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
            with DatFile(dataPath) as f:
                f.value = value['playerdata']
        
        if 'stats' in value:
            statsPath = os.path.join(self.folder, 'stats', f'{uuid}.json')
            with open(statsPath, mode = 'w') as f:
                json.dump(value['stats'], f)
    
    
    