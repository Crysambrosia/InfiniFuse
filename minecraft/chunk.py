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
    __slots__ = ['closed', 'folder', 'timestamp', '_blocks', '_value']
    ID = None
    
    def __init__(self,
        timestamp : int = None,
        value : dict = None,
        folder : str = None
    ):

        self.timestamp = int(time.time()) if timestamp is None else timestamp
        """Timestamp of last edit in epoch seconds"""

        self.value = {} if value is None else value
        """NBT data as a TAG.Compound"""

        self.folder = folder
        """Folder containing the .mca files for writing"""

        self.closed = False
        """Whether this chunk is still open"""

    def __repr__(self):
        """Shows chunk coordinates and formatted timestamp"""
        xPos = str( self['']['Level']['xPos'] )
        zPos = str( self['']['Level']['zPos'] )
        timestamp = time.asctime( time.localtime(self.timestamp) )
        return (f'Chunk at {xPos},{zPos} (Last edited {timestamp})')

    def __delitem__(self, key):
        """Delete a block if <key> is a 3-tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            try:
                self.set_block(x = key[0], y= key[1], z = key[2], newBlock = BlockState.create_valid())
                return
            except ValueError:
                pass
        super().__delitem__(key)

    def __getitem__(self, key):
        """Return a block if <key> is a 3-tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            try:
                return self.get_block(x = key[0], y = key[1], z = key[2])
            except ValueError:
                pass
        return super().__getitem__(key)
    
    def __setitem__(self, key, value):
        """Set block if <key> is a 3-tuple, otherwise default to super"""
        if isinstance(key, tuple) and len(key) == 3:
            try:
                self.set_block(x = key[0], y = key[1], z = key[2], newBlock = value )
                return
            except ValueError:
                pass
        super().__setitem__(key, value)

    def close(self, save : bool = False):
        """Close file, save changes if save = True"""
        if (not self.closed) and save:
            self.write()
        self.closed = True

    @property
    def file(self):
        """The file where this chunk will be saved
        
        May not exist yet
        """
        if self.folder is None:
            raise ValueError(f'No folder.')
        
        regionX = self['']['Level']['xPos'] // 32
        regionZ = self['']['Level']['zPos'] // 32
        return f'{self.folder}\\r.{regionX}.{regionZ}.mca'
    
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

    def find_section(self, x, y, z):
        """Return indexes of section and block at <x> <y> <z>"""
        
        # Raise an exception if <x> <y> <z> are not valid chunk-relative coordinates
        if not 0<=x<=15:
            raise ValueError(f'Invalid chunk-relative x coordinate {x} (must be 0-15)')
        elif not 0<=y<=255:
            raise ValueError(f'Invalid chunk-relative y coordinate {y} (must be 0-255)')
        elif not 0<=z<=15:
            raise ValueError(f'Invalid chunk-relative z coordinate {z} (must be 0-15)')
        
        # Find section containing coordinates
        sectionY, y = divmod(y, 16)
        for section in self['']['Level']['Sections']:
            if section['Y'] == sectionY:
                break
        else:
            raise KeyError(f'Section {sectionY} doesn\'t exist')
        
        blockID = y*16*16 + z*16 + x
        
        return section, blockID

    @classmethod
    def from_world(cls, chunkX : int, chunkZ : int, world : str):
    
        appdata = os.environ['APPDATA']
        folder = (f'{appdata}\\.minecraft\\saves\\{world}\\region')
        return cls.open(chunkX, chunkZ, folder)

    def get_block(self, x : int, y : int , z : int):
        """Return BlockState at chunk-relative coordinates"""
        
        section, blockID = self.find_section(x, y, z)
        unit, start, end = self.find_block(section, blockID)
        
        paletteID = util.get_bits(
            n = section['BlockStates'][unit], 
            start = start,
            end = end
        )
        
        return BlockState(section['Palette'][paletteID])

    @classmethod
    def open(cls, chunkX : int, chunkZ : int, folder : str):
        """Open from folder"""
        
        regionX, chunkX = divmod(chunkX,32)
        regionZ, chunkZ = divmod(chunkZ,32)
        fileName = (f'{folder}\\r.{regionX}.{regionZ}.mca')
        header = 4 * (chunkX + chunkZ*32)
        
        with open(fileName, mode='r+b') as MCAFile:
            with mmap.mmap(MCAFile.fileno(), length=0, access=mmap.ACCESS_READ) as MCA:
    
                offset = 4096 * int.from_bytes( MCA[header:header+3], 'big')
                sectorCount = MCA[header+3]
                timestamp = int.from_bytes( MCA[header+4096:header+4100], 'big')

                if sectorCount > 0 and offset >= 2:
                    length = int.from_bytes(MCA[offset:offset+4], 'big')
                    compression = MCA[offset+4]
                    chunkData = MCA[offset+5 : offset+length+4]
                else:
                    raise FileNotFoundError(f'Chunk doesn\'t exist ({offset},{sectorCount})')

        return cls(
            timestamp = timestamp, 
            value = cls.decode( decompress(chunkData, compression)[0] ), 
            folder = folder
        )

    def set_block(self, x : int, y : int, z : int, newBlock : BlockState):
        """Set the block at x y z to <block>, after checking that <newBlock> is a valid BlockState"""
        
        newBlock = BlockState.create_valid(newBlock)
        section, blockID = self.find_section(x, y, z)
        
        if newBlock not in section['Palette']:
        
            paletteIsFull = max(4, len(section['Palette']).bit_length()) % 2 > 0
            
            if paletteIsFull:
                
                # Copy BlockStates
                blocks = []
                for i in range(4096):
                    unit, start, end = self.find_block(section, i)
                    blocks.append(util.get_bits(section['BlockStates'][unit], start, end))
                
                # Empty the blockStates
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
    
    def write(self):
        """Save chunk changes to file.
        
        Will resize file if chunk changed size.
        Will create missing file.
        """
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        
        self.timestamp = int(time.time())
        
        # Create missing file
        if not os.path.exists(self.file):
            with open(self.file, mode='w+b') as MCAFile:
                MCAFile.truncate(8192)
        
        with open(self.file, mode='r+b') as MCAFile:
            with mmap.mmap(MCAFile.fileno(), length=0, access=mmap.ACCESS_WRITE) as MCA:
            
                # Read header
                header = (4 * (self['']['Level']['xPos'] + self['']['Level']['zPos'] * 32)) % 1024
                offset = int.from_bytes( MCA[header:header+3], 'big')
                
                # If this chunk didn't exist in this file, find the smallest free offset to save it
                # and set compression to the newest spec, 2 (zlib)
                if offset == 0:
                    offset = max(2,*[int.from_bytes(MCA[i*4:i*4+3], 'big')+MCA[i*4+3] for i in range(1024)])
                    compression = 2
                else:
                    compression = MCA[(4096*offset) + 4]
                
                # Prepare data
                chunkData = compress(self.to_bytes(), compression)
                length = len(chunkData) + 1

                # Check if chunk size changed
                oldSectorCount = MCA[header+3]
                newSectorCount = 1+( length//4096 )
                sectorChange = newSectorCount - oldSectorCount
                
                if sectorChange:
                    # Change offsets for following chunks
                    for i in range(1024):
                        oldOffset = int.from_bytes(MCA[i*4 : i*4+3], 'big')
                        
                        if oldOffset > offset:
                            MCA[i*4 : i*4+3] = (oldOffset + sectorChange).to_bytes(3, 'big')
                    
                    # Move following chunks
                    oldStart = 4096 * (offset + oldSectorCount)
                    newStart = oldStart+(4096 * sectorChange)
                    data = MCA[oldStart:]
                    MCA.resize(len(MCA) + (sectorChange * 4096))
                    MCA[newStart:] = data
                
                # Write header
                MCA[header:header+3] = offset.to_bytes(3, 'big')
                MCA[header+3] = newSectorCount
                MCA[header+4096:header+4100] = self.timestamp.to_bytes(4, 'big')
                
                # Write Data
                offset *= 4096
                MCA[offset:offset+4] = length.to_bytes(4, 'big')
                MCA[offset+4] = compression
                MCA[offset+5 : offset + length + 4] = chunkData