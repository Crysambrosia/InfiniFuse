from collections.abc import MutableMapping
from minecraft.datfile import DatFile
import json
import minecraft.TAG as TAG
import os

class PlayerManager(MutableMapping):
    """Handles accessing and modifying player data and stats"""
    
    def __init__(self, folder : str):
        self.folder = folder
    
    def __delitem__(self, key):
        """Delete a player from a hyphenated-hexadecimal UUID"""
        uuid = key
        
        dataPath = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
        if os.path.exists(dataPath):
            os.remove(dataPath)
        
        statsPath = os.path.join(self.folder, 'stats', f'{uuid}.json')
        if os.path.exists(statsPath):
            os.remove(statsPath)
    
    def __iter__(self):
        """Return all contained player UUIDs"""
        path = os.path.join(self.folder, 'playerdata')
        
        if os.path.exists(path):
            for name in os.listdir(path):
                basename = os.path.basename(name)
                uuid, ext = os.path.splitext(basename)
                if ext == '.dat':
                    yield uuid
                else:
                    continue
        else:
            return None
    
    def __getitem__(self, key):
        """Return a player's data from a hyphenated-hexadecimal UUID"""
        
        uuid = key
        
        dataPath = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
        with DatFile(dataPath) as f:
            playerdata = TAG.Compound(f)
        
        statsPath = os.path.join(self.folder, 'stats', f'{uuid}.json')
        if os.path.exists(statsPath):
            with open(statsPath, mode = 'r') as f:
                stats = json.load(f)
        else:
            stats = {}
        
        return {'playerdata' : playerdata, 'stats' : stats, 'uuid' : uuid}
    
    def __len__(self):
        """How many players are contained"""
        count = 0
        path = os.path.join(self.folder, 'playerdata')
        
        if os.path.exists(path):
            for name in os.listdir(path):
                basename = os.path.basename(name)
                uuid, ext = os.path.splitext(basename)
                if ext == '.dat':
                    count += 1
        
        return count
    
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
    
    def update_old_players(self):
        """Update outdated player files to the latest format
        
        This is extremely tedious to program, as it requires a full LUT of IDs to names
        and I can't be bothered to do all that BORING work right now.
        """
        pass