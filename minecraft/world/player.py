from minecraft.datfile import DatFile
import json
import minecraft.TAG as TAG
import os

class Player():
    """Handles accessing and modifying a player's data and stats"""
    def __init__(self, uuid : str, folder : str):
        """UUID must be in the hyphenated-hexadecimal format"""
        self.folder = folder
        self.uuid = uuid
        
        statsPath = os.path.join(self.folder, 'stats', f'{self.uuid}.json')
        with open(statsPath, mode = 'r') as f:
            self.stats = json.load(f)
        
        dataPath = os.path.join(self.folder, 'playerdata', f'{self.uuid}.dat')
        self.playerdata = DatFile.open(path = dataPath)
    
    def write(self):
        """Write changes to file"""
        statsPath = os.path.join(self.folder, 'stats', f'{self.uuid}.json')
        with open(path, mode = 'w') as f:
            json.dump(self.stats, f)
        
        self.playerdata.write()
    
    
    