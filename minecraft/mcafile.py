from .chunk import Chunk
from .compression import compress, decompress
import collections.abc
import math
import mmap
import os
import time

class McaFile(collections.abc.Sequence):
    """Interface for .mca files
    
    For use as a context manager !
    """
    
    sectorLength = 4096
    sideLength = 32
    
    def __init__(self, path):
    
        self.closed = True
        self.path = path
    
    def __enter__(self):
        """Will actually create the file if it does not exist"""
        
        if not os.path.exists(self.path):
            with open(self.path, mode = 'wb') as f:
                f.truncate(self.sectorLength*2)
    
        self.closed = False
        self.file = open(self.path, mode = 'r+b')
        self.file.__enter__()
        self.mmap = mmap.mmap(fileno = self.file.fileno(), length = 0, access = mmap.ACCESS_WRITE)
        self.mmap.__enter__()  
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True
        self.file.__exit__(exc_type, exc_value, traceback)
        self.mmap.__exit__(exc_type, exc_value, traceback)
    
    def __delitem__(self, key):
        """Delete chunk <key>, will be generated again next time the game runs"""
        with self as f:
            f[key] = b''
    
    def __getitem__(self, key):
        """Get data of chunk <key>"""
    
        if self.closed:
            raise IOError(f'{repr(self)} is closed')
    
        if key > len(self) - 1:
            raise IndexError(f'Key must be 0-{len(self)-1}, not {key}')
        
        offset = self.get_offset(key) * self.sectorLength
        sectorCount = self.get_sectorCount(key)
        
        if sectorCount <= 0 or offset < 2 * self.sectorLength:
            return None
        
        length = int.from_bytes(self.mmap[offset : offset + 4], 'big')
        compression = self.mmap[offset + 4]
        data = self.mmap[offset + 5 : offset + length + 4]
        
        return Chunk.from_bytes(decompress(data, compression)[0])
    
    def __len__(self):
        return self.sideLength ** 2
    
    def __setitem__(self, key, value):
        """Save this chunk <key> to file at self.path, commit all cache changes"""
    
        if self.closed:
            raise IOError(f'{repr(self)} is closed')
    
        if key > len(self):
            raise ValueError(f'Key must be 0-{len(self)}, not {key}')

        offset = self.get_offset(key)
        
        # If this chunk didn't exist in this file, find the smallest free offset to save it
        # and set compression to the newest spec, 2 (zlib)
        if offset == 0:
            offset = max(2, *[self.get_offset(i) + self.get_sectorCount(i) for i in range(len(self))])
        
        # Prepare data
        compression = 2
        data = compress(value.to_bytes(), compression)
        length = len(data) + 1

        # Check if chunk size changed
        oldSectorCount = self.get_sectorCount(key)
        newSectorCount = math.ceil((length + 4) / self.sectorLength)
        sectorChange = newSectorCount - oldSectorCount
        
        if sectorChange:
            # Change offsets for following chunks
            for i in range(len(self)):
                oldOffset = self.get_offset(i)
                
                if oldOffset > offset:
                    self.set_offset(i, oldOffset + sectorChange)
            
            # Move following chunks
            oldStart = offset + oldSectorCount
            newStart = oldStart + sectorChange
            oldData = self.mmap[oldStart * self.sectorLength :]
            self.mmap.resize(len(self.mmap) + sectorChange * self.sectorLength)
            self.mmap[newStart * self.sectorLength :] = oldData
        
        # Write header
        self.set_offset(key, offset)
        self.set_sectorCount(key, newSectorCount)
        self.set_timestamp(key, int(time.time()))
        
        # Write Data
        offset *= self.sectorLength
        
        self.mmap[offset : offset + 4] = length.to_bytes(4, 'big')
        self.mmap[offset + 4] = compression
        self.mmap[offset + 5 : offset + length + 4] = data
    
    def __repr__(self):
        return f'McaFile at {self.path}'
    
    @staticmethod
    def find_chunk(folder, x : int, z : int):
        """Return path of containing file and index of chunk at <x> <z>"""
        
        regionX, chunkX = divmod(x, McaFile.sideLength)
        regionZ, chunkZ = divmod(z, McaFile.sideLength)
        
        path = os.path.join(folder, f'r.{regionX}.{regionZ}.mca')
        key = McaFile.sideLength*chunkZ + chunkX
        
        return path, key
    
    def get_all_data(self):
        """Return all chunks stored in this file
        
        Warning : Might overload RAM
        """
        chunks = {}
        for key in range(1024):
            try:
                self.get_data(key = key)
            except:
                pass
    
    def get_offset(self, key):
        """Return offset of chunk <key> in sectors"""
        return int.from_bytes(self.mmap[key*4 : key*4 + 3], byteorder = 'big')
    
    def get_sectorCount(self, key):
        """Return number of sectors used by chunk <key>"""
        return self.mmap[key*4 + 3]
    
    @classmethod
    def read_chunk(cls, folder : str, x : int, z : int):
    
        path, key = cls.find_chunk(folder, x, z)
        
        if os.path.exists(path):
            with cls(path) as f:
                return f[key]
        else:
            return None
    
    @property
    def coords(self):
        """Coords of origin block of this file"""
        return tuple(i * 16 for i in self.coords_chunk)
    
    @property
    def coords_chunk(self):
        """Chunk grid coords of origin chunk of this file (16x16 blocks)"""
        return tuple(i * self.sideLength for i in self.coords_region)
    
    @property
    def coords_region(self):
        """Region grid coords of this file (512*512 blocks, 32x32 chunks)"""
        _, regionX, regionZ, _ = os.path.basename(self.path).split('.')
        return (int(regionX), int(regionZ))
    
    def set_offset(self, key, value):
        """Set offset for chunk <key> to <value>"""
        self.mmap[key*4 : key*4 + 3] = value.to_bytes(length = 3, byteorder = 'big')
    
    def set_sectorCount(self, key, value):
        """Set sectorCount for chunk <key> to <value>"""
        self.mmap[key*4 + 3] = value
    
    def set_timestamp(self, key, value):
        """Set timestamp for chunk <key> to <value>"""
        value = value.to_bytes(length = 4, byteorder = 'big')
        self.mmap[key*4 + self.sectorLength : key*4 + self.sectorLength + 4] = value
    
    @classmethod
    def write_chunk(cls, folder : str, value):
        """Save <value> to the appropriate McaFile for chunk <x> <z> in <folder>"""
        
        x, z = value.coords_chunk
        path, key = cls.find_chunk(folder = folder, x = x, z = z)
        
        with cls(path) as f:
            f[key] = value