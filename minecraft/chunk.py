from .nbt import NBT
import mmap
import os
import time
               
# Chunk data model and interface
class Chunk():
    def __init__(self,
        timestamp,
        payload,
        folder
    ):
        # Timestamp
        self.timestamp = timestamp
        # Chunk NBT data
        self.payload = payload
        
        # Folder containing chunk
        self.folder = folder
        
        # Whether this chunk is still writeable
        self.closed = False
        
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
        xPos = str( self['Level']['xPos'].payload )
        zPos = str( self['Level']['zPos'].payload )
        timestamp = time.asctime( time.localtime(self.timestamp) )
        return (f'Chunk {xPos},{zPos} (Last edited {timestamp})')
        
    def close(self, save=False):
        if (not self.closed) and save:
            self.write()
        self.closed = True
        
    def encode(self):
        return self.payload.encode()
        
    def keys(self):
        return self.payload.keys()
        
    def write(self):
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        else:
        
            # Change timestamp to now
            self.timestamp = int(time.mktime(time.localtime()))
            
            # Prepare Data
            payload = self.encode()
            length = len(payload)+1
            compression = self.payload.compression
            
            # Reconstruct file name
            chunkX = self['Level']['xPos'].payload
            chunkZ = self['Level']['zPos'].payload
            regionX = chunkX // 32
            regionZ = chunkZ // 32
            fileName = (f'{self.folder}\\r.{regionX}.{regionZ}.mca')
            
            # Find chunk header location
            header = 4*(chunkX + chunkZ*32)
            
            with open(fileName, mode='r+b') as MCAFile:
                with mmap.mmap(MCAFile.fileno(), length=0, access=mmap.ACCESS_WRITE) as MCA:
                    
                    offset = int.from_bytes( MCA[header:header+3], 'big')
                    oldSectorCount = MCA[header+3]
                    newSectorCount = 1+( length//4096 )
                    
                    # Move following chunks if size changed
                    if newSectorCount != oldSectorCount:
                        
                        sectorChange = newSectorCount - oldSectorCount
                        # Change offsets for following chunks
                        for i in range(0, 4096, 4):
                        
                            oldOffset = int.from_bytes(MCA[i:i+3], 'big')
                            
                            if oldOffset > offset:
                                newOffset = oldOffset + sectorChange
                                MCA[i:i+3] = newOffset.to_bytes(3, 'big')
                                print(f'Changed offset of {i//4} from {oldOffset} to {newOffset}')
                        
                        # Prepare data move
                        oldStart = 4096 * (offset+newSectorCount)
                        newStart = oldStart+( 4096*sectorChange )
                        dataLength = len(MCA) - oldStart
                        data = MCA[oldStart:oldStart+dataLength]
                        
                        # Resize file
                        MCA.resize( len(MCA)+( sectorChange*4096 ) )
                        
                        # Move data
                        MCA[newStart:newStart+dataLength] = data
                        
                    # Write sector count
                    MCA[header+3] = newSectorCount
                    # Write timestamp
                    MCA[header+4096:header+4100] = self.timestamp.to_bytes(4, 'big')
                    # Convert offset to 4KiB
                    offset *= 4096
                    # Write Data
                    MCA[offset:offset+4] = length.to_bytes(4, 'big')
                    MCA[offset+4] = compression
                    MCA[offset+5 : offset + length + 4] = payload
                    
def openChunk(
    chunkX = 0,
    chunkZ = 0,
    folder = None,
    world = None
):
    # Format file name
    if world is not None:
        # Using world/chunkX/chunkZ
        appdata = os.environ['APPDATA']
        folder = (f'{appdata}\\.minecraft\\saves\\{world}\\region')
        
    elif folder is not None:
        
        # Using complete file name
        formattedFolder = ''
        # Format to using \\
        for character in folder:
            if character == '/':
                formattedFolder += '\\'
            else:
                formattedFolder += character
        folder = formattedFolder
        
    else:
        raise ValueError('Either folder or world is required')
        
    regionX = chunkX//32
    regionZ = chunkZ//32
    fileName = (f'{folder}\\r.{regionX}.{regionZ}.mca')
    
    # Find chunk header location
    header = 4*(chunkX + chunkZ*32)
        
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
                # Reac chunk data
                payload = NBT.decode( MCA[offset+5 : offset+length+4], compression)
            else:
                raise FileNotFoundError('Chunk doesn\'t exist')
    return Chunk(timestamp, payload, folder)