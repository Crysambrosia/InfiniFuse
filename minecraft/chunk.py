from collections.abc import MutableMapping
from .compression import compress, decompress
from minecraft.nbt import *
from util import make_wrappers, read_bytes
import mmap
import os
import time

class Chunk(MutableMapping):
    """Chunk data model and interface
    
    Chunks are opened and saved directly, abstracting .mca files
    """
    def __init__(self,
        timestamp : int = None,
        value : TAG_Compound = None,
        folder : str = None
    ):

        self.timestamp = int(time.time()) if timestamp is None else timestamp
        """Timestamp of last edit in epoch seconds"""

        self.value = TAG_Compound() if value is None else value
        """NBT data as a TAG_Compound"""

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

    def close(self, save : bool = False):
        """Close file, save changes if save = True"""
        if (not self.closed) and save:
            self.write()
        self.closed = True

    def encode(self):
        """Encode this chunk's payload"""
        return self.payload.encode()

    @property
    def file(self):
        """The file where this chunk will be saved
        
        May not exist yet
        """
        if self.folder is None:
            raise ValueError(f'{repr(self)} has no folder !')
        
        regionX = self['']['Level']['xPos'] // 32
        regionZ = self['']['Level']['zPos'] // 32
        return f'{self.folder}\\r.{regionX}.{regionZ}.mca'

    @classmethod
    def from_world(cls, chunkX : int, chunkZ : int, world : str):
    
        appdata = os.environ['APPDATA']
        folder = (f'{appdata}\\.minecraft\\saves\\{world}\\region')
        
        return cls.open(chunkX, chunkZ, folder)

    @classmethod
    def open(cls, chunkX : int, chunkZ : int, folder : str):
        """Open from folder"""
        
        regionX = chunkX//32
        regionZ = chunkZ//32
        fileName = (f'{folder}\\r.{regionX}.{regionZ}.mca')
        header = (4 * (chunkX + chunkZ*32)) % 1024
        
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
            value = TAG_Compound.from_bytes( decompress(chunkData, compression)[0] ), 
            folder = folder
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
                MCAFile.write(b'\x00' * 8192)
        
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

make_wrappers( Chunk, 
    nonCoercedMethods = [
        'to_bytes', 
        '__delitem__', 
        '__eq__', 
        '__getitem__',
        '__iter__',
        '__len__',
        '__setitem__'
    ]
)
