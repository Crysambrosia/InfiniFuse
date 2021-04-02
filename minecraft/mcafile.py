from .compression import compress, decompress
import minecraft.TAG as TAG
import math
import mmap
import os
import re
import time

class McaFile():
    """Interface for .mca files"""
    
    sectorLength = 4096
    
    def __init__(self, path):
        self.closed = True
        self.path = path
    
    def __enter__(self):
        self.closed = False
        self.file = open(self.path)
        self.file.__enter__()
        self.mmap = mmap.mmap(fileno = self.file.fileno, length = 0, access = mmap.ACCESS_READ)
        self.mmap.__enter__()  
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True
        self.file.__exit__(exc_type, exc_value, traceback)
        self.mmap.__exit__(exc_type, exc_value, traceback)
    
    def __getitem__(self, key):
    
        if self.closed:
            raise IOError(f'{repr(self)} is closed !')
        
        return self.mmap[key]
    
    def __setitem__(self, key, value):
    
        if self.closed:
            raise IOError(f'{repr(self)} is closed !')
        
        self.mmap[key] = value
    
    def __repr__(self):
        return f'McaFile at {self.path}'
    
    def get_data(self, key):
        """Get data of chunk <key>"""
        
        offset = self.get_offset(key) * self.sectorLength
        sectorCount = self.get_sectorCount(key)
        
        if sectorCount < 0 or offset <= 2 * self.sectorLength:
            raise FileNotFoundError(f'Chunk doesn\'t exist ({offset},{sectorCount})')
        
        length = int.from_bytes(self[offset : offset + 4], 'big')
        compression = self[offset + 4]
        data = self[offset + 5 : offset + length + 4]
        
        return decompress(data, compression)[0]
    
    def get_offset(self, key):
        """Return offset of chunk <key> in sectors"""
        return int.from_bytes(self[key : key + 3], byteorder = 'big')
    
    def get_sectorCount(self, key):
        """Return number of sectors used by chunk <key>"""
        return self[key+3]
    
    def set_offset(self, key, value):
        """Set offset for chunk <key> to <value>"""
        self[key : key + 3] = value.to_bytes(length = 3, byteorder = 'big')
    
    def set_sectorCount(self, key, value):
        """Set sectorCount for chunk <key> to <value>"""
        self[key + 3] = value
    
    def set_timestamp(self, key, value):
        """Set timestamp for chunk <key> to <value>"""
        value = value.to_bytes(length = 4, byteorder = 'big')
        self[key + self.sectorLength : key + self.sectorLength + 4] = value
    
    def set_data(self, key, chunk):
        """Save this chunk in <folder>, commit all cache changes"""
        
        offset = self.get_offset(key)
        
        # If this chunk didn't exist in this file, find the smallest free offset to save it
        # and set compression to the newest spec, 2 (zlib)
        if offset == 0:
            offset = max(2, *[self.get_offset(i) + self.get_sectorCount(i) for i in range(1024)])
        
        # Prepare data
        compression = 2
        data = compress(chunk.to_bytes(), compression)
        length = len(data) + 1

        # Check if chunk size changed
        oldSectorCount = self.get_sectorCount(key)
        newSectorCount = math.ceil((length + 4) / self.sectorLength)
        sectorChange = newSectorCount - oldSectorCount
        
        if sectorChange:
            # Change offsets for following chunks
            for i in range(1024):
                oldOffset = self.get_offset(i)
                
                if oldOffset > offset:
                    self.set_offset(i, oldOffset + sectorChange)
            
            # Move following chunks
            oldStart = self.sectorLength * (offset + oldSectorCount)
            newStart = oldStart + (self.sectorLength * sectorChange)
            oldData = self[oldStart:]
            self.mmap.resize(len(self.mmap) + (sectorChange * self.sectorLength))
            self[newStart:] = oldData
        
        # Write header
        self.set_offset(key, offset)
        self.set_sectorCount(key, newSectorCount)
        self.set_timestamp(key, int(time.time()))
        
        # Write Data
        self[offset : offset + 4] = length.to_bytes(4, 'big')
        self[offset + 4] = compression
        self[offset + 5 : offset + length + 4] = data
    
    @classmethod
    def write_chunk(cls, folder, chunk):
        """Save <chunk> to the appropriate McaFile in <folder>"""
        regionX, chunkX = divmod(chunk['']['Level']['xPos'], 32)
        regionZ, chunkZ = divmod(chunk['']['Level']['zPos'], 32)
        
        key = 32*chunkZ + chunkX
        
        path = os.path.join(folder, f'r.{regionX}.{regionZ}.mca')
        with cls(path) as f:
            f.set_data(key, chunk)