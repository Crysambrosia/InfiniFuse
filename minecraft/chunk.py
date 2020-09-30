from .nbt import NBT
import mmap
import os
import time
               
class Chunk():
    """Chunk data model and interface
    
    Chunks can be opened and saved directly, abstracting .mca files
    """
    def __init__(self,
        timestamp : int,
        payload : NBT,
        folder : str = None
    ):

        self.timestamp = timestamp
        """Timestamp of last edit in epoch seconds"""

        self.payload = payload
        """NBT data (usually a TAG_Compound)"""

        self.folder = folder
        """Folder containing the .mca files, for writing"""

        self.closed = False
        """Whether this chunk is still open"""
        
    def __eq__(self, other):
        if type(other) == Chunk:
            return self.payload == other.payload
        else:
            return False
        
    def __getitem__(self, key):
        return self.payload[key]
        
    def __setitem__(self, key, value):
        self.payload[key] = value
        
    def __repr__(self):
        """Shows chunk coordinates and formatted timestamp"""
        xPos = str( self['Level']['xPos'].payload )
        zPos = str( self['Level']['zPos'].payload )
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
        if self.folder is None:
            raise ValueError(f'{repr(self)} has no folder !')
        regionX = self['Level']['xPos'].payload // 32
        regionZ = self['Level']['zPos'].payload // 32
        return f'{self.folder}\\r.{regionX}.{regionZ}.mca'
       
    @classmethod
    def from_world(cls, chunkX : int, chunkZ : int, world : str):
    
        appdata = os.environ['APPDATA']
        folder = (f'{appdata}\\.minecraft\\saves\\{world}\\region')
        
        return cls.read(chunkX, chunkZ, folder)
         
    def keys(self):
        return self.payload.keys()
        
    @classmethod
    def read(cls, chunkX : int, chunkZ : int, folder : str):
        """Open from folder"""
            
        regionX = chunkX//32
        regionZ = chunkZ//32
        fileName = (f'{folder}\\r.{regionX}.{regionZ}.mca')
        
        # Find chunk header location
        header = (4 * (chunkX + chunkZ*32)) % 1024
            
        with open(fileName, mode='r+b') as MCAFile:
            with mmap.mmap(MCAFile.fileno(), length=0, access=mmap.ACCESS_READ) as MCA:
                
                # Read header
                offset = 4096 * int.from_bytes( MCA[header:header+3], 'big')
                sectorCount = MCA[header+3]
                timestamp = int.from_bytes( MCA[header+4096:header+4100], 'big')
                
                # If chunk exists
                if sectorCount > 0 and offset >= 2:
                    
                    # Read chunk data properties
                    length = int.from_bytes(MCA[offset:offset+4], 'big')
                    compression = MCA[offset+4]
                    # Read chunk data
                    payload = NBT.decode( MCA[offset+5 : offset+length+4], compression)
                else:
                    raise FileNotFoundError(f'Chunk doesn\'t exist ({offset},{sectorCount})')
                    
        return cls(timestamp, payload, folder)
            
    def write(self):
        """Save chunk changes to file.
        
        Will resize file if chunk changed size.
        Will create missing file.
        """
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        
        # Change timestamp to now
        self.timestamp = int(time.time())
        
        # Create .mca file if it does not exist
        if not os.path.exists(self.file):
            with open(self.file, mode='w+b') as MCAFile:
                for i in range(8192):
                    MCAFile.write(b'\x00')
                
        # Find chunk header location
        header = (4 * (self['Level']['xPos'].payload + self['Level']['zPos'].payload*32)) % 1024
        
        # Prepare Data
        payload = self.encode()
        length = len(payload)+1
        compression = self.payload.compression
        
        with open(self.file, mode='r+b') as MCAFile:
            with mmap.mmap(MCAFile.fileno(), length=0, access=mmap.ACCESS_WRITE) as MCA:
                
                offset = int.from_bytes( MCA[header:header+3], 'big')
                if offset == 0:
                    offset = max(2,*[int.from_bytes(MCA[i*4:i*4+3], 'big')+MCA[i*4+3] for i in range(1024)])
                
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
                    oldStart = 4096 * (offset+oldSectorCount)
                    data = MCA[oldStart:]
                    
                    MCA.resize(len(MCA) + (sectorChange * 4096))
                    
                    newStart = oldStart+(4096 * sectorChange)
                    MCA[newStart:] = data
                    
                # Write header
                MCA[header:header+3] = offset.to_bytes(3, 'big')
                MCA[header+3] = newSectorCount
                MCA[header+4096:header+4100] = self.timestamp.to_bytes(4, 'big')
                
                # Write Data
                offset *= 4096
                MCA[offset:offset+4] = length.to_bytes(4, 'big')
                MCA[offset+4] = compression
                MCA[offset+5 : offset + length + 4] = payload
                    