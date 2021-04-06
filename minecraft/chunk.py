from .compression import compress, decompress
from .blockstate import BlockState
import math
import minecraft.TAG as TAG
import mmap
import os
import time
import util

class Chunk(TAG.Compound, util.Cache):
    """Chunk data model and interface
    
    Chunks are opened and saved directly, abstracting .mca files
    """
    __slots__ = ['_cache', '_value']
    ID = None
    
    def __init__(self, value : dict = None):

        self._cache = {}
        """Contains dynamically loaded blocks"""

        self.value = value or {}
        """NBT data as a TAG.Compound"""

    def __delitem__(self, key):
        """Remove a block from cache if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            key = self.validate_coords(key)
            del self._cache[key]
        else:
            super().__delitem__(key)

    def __getitem__(self, key):
        """Return a block if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            key = self.validate_coords(key)
            
            if key not in self._cache:
                self.load(key)
            
            return self._cache[key]
        else:
            return super().__getitem__(key)
    
    def __repr__(self):
        """Shows chunk coords"""
        try:
            return f'Chunk at block {self.coords}'
        except KeyError:
            return f'Chunk (Invalid position)'
    
    def __setitem__(self, key, value):
        """Set block if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            key = self.validate_coords(key)
            self._cache[key] = BlockState.create_valid(value)
        else:
            super().__setitem__(key, value)
    
    @property
    def coords(self):
        """Coords of origin block of this chunk"""
        return tuple(i * 16 for i in self.coords_chunk)
    
    @property
    def coords_chunk(self):
        """Chunk grid coords of this chunk"""
        return (int(self['']['Level']['xPos']), int(self['']['Level']['zPos']))
    
    @staticmethod
    def validate_coords(coords : tuple):
        """Return <x> <y> <z> as ints if they are valid chunk-relative coords"""
        
        x, y, z = [int(i) for i in coords]
        
        # Raise an exception if <x> <y> <z> are not valid chunk-relative coords
        if not 0 <= x <= 15:
            raise ValueError(f'Invalid chunk-relative x {x} (must be 0-15)')
        elif not 0 <= y <= 255:
            raise ValueError(f'Invalid chunk-relative y {y} (must be 0-255)')
        elif not 0 <= z <= 15:
            raise ValueError(f'Invalid chunk-relative z {z} (must be 0-15)')
        
        return x, y, z
    
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
    def find_section(key):
        """Return block and section indexes of block at coords in key"""
        x, y, z = Chunk.validate_coords(key)
        sectionID, blockID = divmod(y*16*16 + z*16 + x, 4096)
        return sectionID, blockID

    def load(self, key):
        """Load BlockState at <x> <y> <z> to cache"""
        sectionID, blockID = self.find_section(key)
        
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
        
        self[key] = block

    def to_bytes(self):
        """Return NBT data as a bytearray. Will save all cached changes"""
        self.save_all()
        return super().to_bytes()

    def save(self, key):
        """save block at <key> from cache to self.value"""
        
        if key not in self._cache:
            return
        
        newBlock = self[key]
        
        sectionID, blockID = self.find_section(key)
        
        for section in self['']['Level']['Sections']:
            if section['Y'] == sectionID:
                break
        else:
            self['']['Level']['Sections'].append(TAG.Compound({'Y':TAG.Byte(sectionID)}))
            lastIndex = len(self['']['Level']['Sections']) - 1
            section = self['']['Level']['Sections'][lastIndex]
        
        if 'Palette' not in section or 'BlockStates' not in section:
            section['Palette'] = TAG.List([TAG.Compound(BlockState.create_valid())])
            section['BlockStates'] = TAG.Long_Array([TAG.Long(0) for _ in range(256)])
        
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
        del self[key]