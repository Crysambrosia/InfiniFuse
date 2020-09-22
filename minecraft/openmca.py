from .chunk import Chunk
from .nbt import NBT
import gzip
import math
import mmap
import os
import time
import zlib

# Interface for .mca files
class openMCA():
    def __init__(self, fileName = '', world='world', regionX=0, regionZ=0):
        
        print(f'Reading region {regionX}, {regionZ} of {world}')
        start = time.perf_counter()
        
        # Format file name
        if fileName != '':
            # Using a file name
            newFileName = ''
            for character in fileName:
                if character == '/':
                    newFileName += '\\'
                else:
                    newFileName += character
            fileName = newFileName
        else:
            # Using world/regionX/regionZ
            fileName = (
                world
                + '\\region\\r.'
                + str(regionX)
                + '.'
                + str(regionZ)
                + '.mca'
            )
        
        # Load file into memory
        try:
            # Try complete file path
            with open(fileName, mode='r+b') as rawMCA:
                MCAFile = mmap.mmap(rawMCA.fileno(), length=0, access=mmap.ACCESS_READ)
        except FileNotFoundError:
            # Try minecraft subdirectory
            fileName = (
                os.environ['APPDATA']
                + '\\.minecraft\\saves\\'
                + fileName
            )
            with open(fileName, mode='r+b') as rawMCA:
                MCAFile = mmap.mmap(rawMCA.fileno(), length=0, access=mmap.ACCESS_READ)
             
        payload = []
            
        # Load existing chunks into their slots
        for i in range(1024):
            # Chunk info is stored in blocks of 4 bytes
            key = i*4
            
            # Get basic info from file header
            offset = 4096 * int.from_bytes( MCAFile[key:key+3], byteorder = 'big' )
            sectorCount = MCAFile[key+3]
            timestamp = int.from_bytes( MCAFile[key+4096:key+4100], byteorder = 'big' )
            
            # Only if chunk exists
            if sectorCount > 0 and offset >= 2:
                
                # Read chunk properties
                length = int.from_bytes(MCAFile[offset:offset+4], byteorder = 'big')
                compression = MCAFile[offset+4]
            
                # If chunk is not empty
                if length > 2:
                
                    # Find chunk data position
                    start = offset + 5
                    end   = offset + 4 + length
                    
                    # Load and decode chunk data
                    chunkPayload = NBT.decode( MCAFile[start:end], compression)
                    payload.append( Chunk(chunkPayload, timestamp) )
            else:
                payload.append( None )
            
        # Close mmap now that it's not needed
        MCAFile.close()
            
        # Wether this file is still writable
        self.closed = False
        
        # Contains chunk data
        self.payload = payload
        
        # Original file name for saving
        self.fileName = fileName
        
        finish = time.perf_counter()
        print(f'Finished reading region {regionX}, {regionZ} of {world} in {finish} seconds')
        
    def __eq__(self, other):
        if type(other) != openMCA:
            return False
        else:
            equal = True
            for chunks1, chunks2 in zip(self.payload, other.payload):
                for chunk1, chunk2 in zip(chunks1, chunks2):
                    if chunk1 != chunk2:
                        equal = False
                        break
                if not equal:
                    break
            return equal
                
        
    # Gets stored Chunk, load if needed
    def __getitem__(self, key):
        if type(key) == tuple and len(key) == 2:
            x = key[0]
            z = key[1]
            return self.payload[ (x + z*32) ]
        elif type(key) == int:
            return self.payload[key]
        else:
            raise IndexError(f'Key must be either index or tuple(x,z), not {type(key)}')
        
    
    # Replace stored Chunk
    def __setItem__(self, key, value):
        if type(value) != Chunk and value is not None:
            raise TypeError('Cannot assign {type(value)} to chunk !')
        else:
            self[key] = value
    
        
    def write(self):
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        else:
            locations = bytearray()
            timestamps = bytearray()
            chunks = []
            # First chunk is 2 sectors after file start
            nextOffset = 2
            # Prepare file data
            for i in range(1024):
                xPos = i%32
                zPos = i//32
                #key = i*4
                
                if self.payload[i] is not None:
                    
                    # Encode and compress chunk payload
                    payload = self[i].encode()
                    
                    length = len(payload)+1
                    
                    # Prepare chunk
                    chunk = bytearray()
                    chunk += length.to_bytes(length=4, byteorder='big')
                    chunk += self[i].payload.compression.to_bytes(length=1, byteorder='big')
                    chunk += payload
                    
                    # Add padding
                    if len(chunk)%4096 != 0:
                        chunk += bytearray( 4096 - ( len(chunk)%4096 ) )
                    
                    # Prepare location
                    offset = nextOffset
                    sectorCount = int(len(chunk)/4096)
                    timestamp = self[i].timestamp
                    
                else:
                    # Prepare empty chunk
                    chunk = bytearray()
                    # Prepare empty location
                    offset = 0
                    sectorCount = 0
                    timestamp = 0
                    
                # Write info to file header
                locations += offset.to_bytes(length=3, byteorder='big')
                locations += sectorCount.to_bytes(length=1, byteorder='big')
                timestamps += timestamp.to_bytes(length=4, byteorder='big')
                
                # Save chunk data
                chunks.append(chunk)
                
                # Increment next offset
                nextOffset += sectorCount
                
            # Write to file
            with open(self.fileName, mode='w+b') as MCAFile:
                MCAFile.write(locations)
                MCAFile.write(timestamps)
                for chunk in chunks:
                    MCAFile.write(chunk)