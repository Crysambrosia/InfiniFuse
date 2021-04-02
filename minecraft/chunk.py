from .compression import compress, decompress
from .blockstate import BlockState
import math
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
    
    def __init__(self, value : dict = None):

        self._cache = {}
        """Contains dynamically loaded blocks"""

        self.value = value or {}
        """NBT data as a TAG.Compound"""

    def __delitem__(self, key):
        """Remove a block from cache if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            x, y, z = self.validate_coordinates(*key)
            del self._cache[(x,y,z)]
        else:
            super().__delitem__(key)

    def __getitem__(self, key):
        """Return a block if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            x, y, z = self.validate_coordinates(*key)
            
            if (x, y, z) not in self._cache:
                self.load(x, y, z)
            
            return self._cache[(x, y, z)]
        else:
            return super().__getitem__(key)
    
    def __repr__(self):
        """Shows chunk coordinates"""
        xPos = str( self['']['Level']['xPos'] )
        zPos = str( self['']['Level']['zPos'] )
        return (f'Chunk at {xPos},{zPos}')
    
    def __setitem__(self, key, value):
        """Set block if <key> is a tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            x, y, z = self.validate_coordinates(*key)
            self._cache[(x, y, z)] = BlockState.create_valid(value)
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
    def validate_coordinates(x : int, y : int, z : int):
        """Return <x> <y> <z> as ints if they are valid chunk-relative coordinates"""
        
        x = int(x)
        y = int(y)
        z = int(z)
        
        # Raise an exception if <x> <y> <z> are not valid chunk-relative coordinates
        if not 0 <= x <= 15:
            raise ValueError(f'Invalid chunk-relative x coordinate {x} (must be 0-15)')
        elif not 0 <= y <= 255:
            raise ValueError(f'Invalid chunk-relative y coordinate {y} (must be 0-255)')
        elif not 0 <= z <= 15:
            raise ValueError(f'Invalid chunk-relative z coordinate {z} (must be 0-15)')
        
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
    def find_section(x : int, y : int, z : int):
        """Return block and section indexes of block at coordinates in key"""
        x, y, z = Chunk.validate_coordinates(x, y, z)
        sectionID, blockID = divmod(y*16*16 + z*16 + x, 4096)
        return sectionID, blockID

    def load(self, x : int, y : int, z : int):
        """Load BlockState at <x> <y> <z> to cache"""
        sectionID, blockID = self.find_section(x, y, z)
        
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
        
        self[(x, y, z)] = block

    @classmethod
    def open(cls, folder : str, x : int, z : int):
        """Open chunk at <x> <z> from a folder of .mca files"""
        
        regionX, chunkX = divmod(x, 32)
        regionZ, chunkZ = divmod(z, 32)
        file = os.path.join(folder, f'r.{regionX}.{regionZ}.mca')
        header = 32 * chunkZ + chunkX
        
        with open(file, mode = 'r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as fmap:
            
                offset = 4096 * int.from_bytes(fmap[header:header + 3], 'big')
                sectorCount = fmap[header + 3]

                if sectorCount > 0 and offset >= 2:
                    length = int.from_bytes(fmap[offset:offset + 4], 'big')
                    compression = fmap[offset + 4]
                    chunkData = fmap[offset + 5:offset + length + 4]
                
                else:
                    raise FileNotFoundError(f'Chunk doesn\'t exist ({offset},{sectorCount})')
        
        return cls.from_bytes(decompress(chunkData, compression)[0])

    def save_all(self):
        """Save all blocks in self._cache"""
        for key in self._cache:
            x, y, z = key
            self.save(x, y, z)

    def save(self, x : int, y : int, z : int):
        """Save block at <x> <y> <z> from cache to self.value"""
        
        if (x, y, z) not in self:
            return
        newBlock = self[(x, y, z)]
        
        sectionID, blockID = self.find_section(x, y, z)
        
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
    
    def write(self, folder : str):
        """Save this chunk in <folder>, commit all cache changes"""
        self.save_all()
        
        regionX, chunkX = divmod(self['']['Level']['xPos'], 32)
        regionZ, chunkZ = divmod(self['']['Level']['zPos'], 32)
        
        file = os.path.join(folder, f'r.{regionX}.{regionZ}.mca')
        header = 4 * (32 * chunkZ + chunkX)
        
        with open(file, mode='r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_WRITE) as fmap:
                
                offset = int.from_bytes( fmap[header:header+3], 'big')
                
                # If this chunk didn't exist in this file, find the smallest free offset to save it
                # and set compression to the newest spec, 2 (zlib)
                if offset == 0:
                    offset = max(2,*[int.from_bytes(fmap[i*4:i*4+3], 'big')+fmap[i*4+3] for i in range(1024)])
                    compression = 2
                else:
                    compression = fmap[(4096*offset) + 4]
                
                # Prepare data
                chunkData = compress(self.to_bytes(), compression)
                length = len(chunkData) + 1

                # Check if chunk size changed
                oldSectorCount = fmap[header+3]
                newSectorCount = math.ceil((length + 4) / 4096)
                sectorChange = newSectorCount - oldSectorCount
                
                if sectorChange:
                    # Change offsets for following chunks
                    for i in range(1024):
                        oldOffset = int.from_bytes(fmap[i * 4:i * 4 + 3], 'big')
                        
                        if oldOffset > offset:
                            fmap[i * 4:i * 4 + 3] = (oldOffset + sectorChange).to_bytes(3, 'big')
                    
                    # Move following chunks
                    oldStart = 4096 * (offset + oldSectorCount)
                    newStart = oldStart+(4096 * sectorChange)
                    data = fmap[oldStart:]
                    fmap.resize(len(fmap) + (sectorChange * 4096))
                    fmap[newStart:] = data
                
                # Write header
                fmap[header:header + 3] = offset.to_bytes(3, 'big')
                fmap[header + 3] = newSectorCount
                timestamp = int(time.time())
                fmap[header + 4096:header + 4100] = timestamp.to_bytes(4, 'big')
                
                # Write Data
                offset *= 4096
                fmap[offset:offset + 4] = length.to_bytes(4, 'big')
                fmap[offset + 4] = compression
                fmap[offset + 5:offset + length + 4] = chunkData