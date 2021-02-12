from .compression import compress, decompress
from .blockstate import BlockState
import collections.abc
import copy
import minecraft.TAG as TAG
import mmap
import os
import time
import util

class Chunk(TAG.Compound):
    """Chunk data model and interface
    
    Chunks are opened and saved directly, abstracting .mca files
    """
    __slots__ = ['_cache', '_value']
    ID = None
    
    def __init__(self,
        value : dict = None
    ):

        self._cache = {}
        """Contains dynamically loaded sections / blocks"""

        self.value = {} if value is None else value
        """NBT data as a TAG.Compound"""

    def __delitem__(self, key):
        """Delete a block if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple):
            cacheID = self.cache_index(*key)
            self._cache[cacheID] = BlockState.create_valid()
        else:
            super().__delitem__(key)

    def __getitem__(self, key):
        """Return a block if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple):
            cacheID = self.cache_index(*key)
            
            if cacheID not in self._cache:
                self.load_block(cacheID)
            
            return self._cache[cacheID] 
        else:
            return super().__getitem__(key)
    
    def __repr__(self):
        """Shows chunk coordinates"""
        xPos = str( self['']['Level']['xPos'] )
        zPos = str( self['']['Level']['zPos'] )
        return (f'Chunk at {xPos},{zPos}')
    
    def __setitem__(self, key, value):
        """Set block if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple):
            cacheID = self.cache_index(*key)
            value = BlockState.create_valid(value)
            self._cache[cacheID] = value
        else:
            super().__setitem__(key, value)
    
    def cache_index(self, x : int, y : int, z : int):
        """Return cache index of block at <x> <y> <z>."""
        
        x = int(x)
        y = int(y)
        z = int(z)
        
        # Raise an exception if <x> <y> <z> are not valid chunk-relative coordinates
        if not 0<= x <=15:
            raise ValueError(f'Invalid chunk-relative x coordinate {x} (must be 0-15)')
        elif not 0<= y <=255:
            raise ValueError(f'Invalid chunk-relative y coordinate {y} (must be 0-255)')
        elif not 0<= z <=15:
            raise ValueError(f'Invalid chunk-relative z coordinate {z} (must be 0-15)')
        
        return y*16*16 + z*16 + x
    
    @staticmethod
    def find_block(section, blockID):
        """Return containing unit and bit indexes of block at <blockID> in <section>"""
        
        if not  0 <= blockID <= 4095:
            raise ValueError(f'Invalid block index {blockID} (must be 0-4095)')
        
        try:
            blockLen = max(4, (len(section['Palette']) - 1).bit_length())
        except KeyError:
            raise KeyError(f'Section {sectionY} has no Palette')
        
        unitLen = section['BlockStates'].elementType().bit_length # Works even if the list is empty
        blocksPerUnit = unitLen // blockLen
        
        unit, offset = divmod(blockID, blocksPerUnit)
        start = offset * blockLen
        end = start + blockLen
        
        return unit, start, end

    @staticmethod
    def find_section(cacheID):
        """Return block and section indexes of cached block <cacheID>"""
        
        if not 0 <= cacheID <= 65535:
            raise KeyError(f'Invalid cache index {block} (must be 0-65535)')
        
        sectionID, blockID = divmod(cacheID, 4096)
        return sectionID, blockID

    def load_block(self, cacheID : int):
        """Load BlockState <cacheID> to self._cache"""
        
        sectionID, blockID = self.find_section(cacheID)
        
        block = BlockState.create_valid()
        
        for section in self['']['Level']['Sections']:
        
            if section['Y'] == sectionID:
                if 'BlockStates' in section:
                    unit, start, end = self.find_block(section, blockID)
                
                    paletteID = util.get_bits(
                        n = section['BlockStates'][unit], 
                        start = start,
                        end = end
                    )
                    
                    block = BlockState(section['Palette'][paletteID])
                break
        
        self._cache[cacheID] = block

    def save(self):
        """Save all blocks in self._cache"""
        for i in self._cache:
            self.save_block(i)

    def save_block(self, cacheID : int):
        """Save block at <cacheID> of <sectionID> to self.value"""
        
        if cacheID not in self._cache:
            return
        newBlock = self._cache[cacheID]
        
        sectionID, blockID = self.find_section(cacheID)
        
        for section in self['']['Level']['Sections']:
            if section['Y'] == sectionID:
                break
        else:
            # Will be able to build new sections
            raise KeyError(f'Section {sectionID} doesn\'t exist')
        
        if newBlock not in section['Palette']:
        
            paletteIsFull = max(4, len(section['Palette']).bit_length()) % 2 > 0
            
            if paletteIsFull:
                
                # Copy BlockState IDs
                blocks = []
                for i in range(4096):
                    unit, start, end = self.find_block(section, i)
                    blocks.append(util.get_bits(section['BlockStates'][unit], start, end))
                
                # Empty BlockState IDs
                unitType = section['BlockStates'].elementType
                section['BlockStates'] = section['BlockStates'].__class__()
            
            section['Palette'].append(newBlock)
            
            if paletteIsFull:
            
                # Rewrite BlockStates with new Palette
                for i, block in enumerate(blocks):
                
                    unit, start, end = self.find_block(section, i)
                    
                    if start == 0:
                        section['BlockStates'].append(unitType())
                    
                    section['BlockStates'][unit] = util.set_bits(
                        section['BlockStates'][unit], 
                        start, 
                        end, 
                        block
                    )
        
        unit, start, end = self.find_block(section, blockID)
        
        section['BlockStates'][unit] = util.set_bits(
            n = section['BlockStates'][unit],
            start = start,
            end = end, 
            value = section['Palette'].index(newBlock)
        )