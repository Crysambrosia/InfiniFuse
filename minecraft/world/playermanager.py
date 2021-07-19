from collections.abc import MutableMapping
from minecraft.datfile import DatFile
import json
import logging
import minecraft.TAG as TAG
import os

class PlayerManager(MutableMapping):
    """Handles accessing and modifying player data and stats"""
    
    def __init__(self, folder : str):
        self.folder = folder
    
    def __contains__(self, uuid):
        """Checks whether this map contains player <uuid>"""
        path = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
        return os.path.exists(path)
    
    def __delitem__(self, uuid):
        """Delete a player from a hyphenated-hexadecimal uuid"""
        
        path = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
        if os.path.exists(path):
            os.remove(path)
        
        for subfolder in ['advancements', 'stats']:
            path = os.path.join(self.folder, subfolder, f'{uuid}.json')
            if os.path.exists(path):
                os.remove(path)
    
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
    
    def __getitem__(self, uuid):
        """Return player <uuid>'s data
        
        <uuid> : A hyphenated-hexadecinal Minecraft Player UUID
        """
        
        if uuid not in self:
            raise KeyError(f'Player {uuid} has no playerdata')
        
        player = {}
        
        path = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
        with DatFile(path) as f:
            player['playerdata'] = TAG.Compound(f)
        
        for subfolder in ['advancements', 'stats']:
            path = os.path.join(self.folder, subfolder, f'{uuid}.json')
            if os.path.exists(path):
                with open(path, mode = 'r') as f:
                    player[subfolder] = json.load(f)
            else:
                player[subfolder] = {}
        
        return player
    
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
    
    def  __setitem__(self, uuid, player):
        """Write data for player <uuid>
        
        <uuid>   : A hyphenated-hexadecinal Minecraft Player UUID
        <player> : A dict representing a player, as returned by playermanager.__getitem__
        """
        
        if 'playerdata' in player:
            path = os.path.join(self.folder, 'playerdata', f'{uuid}.dat')
            with DatFile(path) as f:
                f.value = player['playerdata']
        
        for subfolder in ['advancements', 'stats']:
            if subfolder in player:
                path = os.path.join(self.folder, subfolder, f'{uuid}.json')
                with open(path, mode = 'w') as f:
                    json.dump(player[subfolder], f)
    
    def setup_conversion(self, target_uuid : str, replacement_uuid : str):
        """Rename all files of player <target_uuid> to <replacement_uuid>
        
        You should use your own uuid as <replacement_uuid>.
        Load the map to make the game convert <target_uuid>'s files to the latest format
        and then run teardown_conversion to finish up !
        """
        temp_folder = os.path.join(os.environ['temp'], 'InfiniFuse')
        os.mkdir(temp_folder)
        
    