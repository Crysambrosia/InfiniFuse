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
    __slots__ = ['_file', '_mmap', 'path']
    sectorLength = 4096
    sideLength = 32
    
    def __init__(self, path):
        
        self._file = None
        """File Object of file at self.path (after __enter__)"""
        
        self._mmap = None
        """mmap.map of file at self.path (after __enter__)"""
        
        self.path = path
        """Path of file for IO"""
    
    def __contains__(self, index):
        """Whether chunk <index> contains any data"""
        return self.get_header(index) is not None
    
    def __del__(self):
        self.__exit__()
    
    def __enter__(self):
        """Will actually create the file if it does not exist"""
        
        if not os.path.exists(self.path):
            with open(self.path, mode = 'wb') as f:
                f.truncate(self.sectorLength*2)
        
        self._file = open(self.path, mode = 'r+b')
        self._file.__enter__()
        self._mmap = mmap.mmap(fileno = self._file.fileno(), length = 0, access = mmap.ACCESS_WRITE)
        self._mmap.__enter__()
        return self
    
    def __exit__(self, exc_type = None, exc_value = None, traceback = None):
        if self._file is not None:
            self._file.__exit__(exc_type, exc_value, traceback)
        if self._mmap is not None:
            self._mmap.__exit__(exc_type, exc_value, traceback)
    
    def __delitem__(self, index):
        """Delete chunk <index>, will be generated again next time the game runs"""
        self[index] = b''
    
    def __getitem__(self, index):
        """Get data of chunk <index>"""
        
        header = self.get_header(index)
        
        if header is None:
            return None
        
        offset = header['offset'] * self.sectorLength
        length = int.from_bytes(self.mmap[offset : offset + 4], 'big')
        compression = self.mmap[offset + 4]
        data = self.mmap[offset + 5 : offset + length + 4]
        
        return Chunk.from_bytes(decompress(data, compression)[0])
    
    def __len__(self):
        return self.sideLength ** 2
    
    def __setitem__(self, index, value):
        """Save this chunk <index> to file at self.path, commit all cache changes"""
        
        # Get header info
        header = self.get_header(index)
        
        if header is None:
            # If this chunk didn't exist in this file, find smallest free offset to save it
            offset = max(2, *[sum(self.get_header(i)) for i in range(len(self))])
            oldSectorCount = 0
        else:
            offset = header['offset']
            oldSectorCount = header['sectorCount']
        
        # Prepare data
        compression = 2
        data = compress(value.to_bytes(), compression)
        length = len(data) + 1

        # Check if chunk size changed
        newSectorCount = math.ceil((length + 4) / self.sectorLength)
        sectorChange = newSectorCount - oldSectorCount
        
        if sectorChange:
            # Change offsets for following chunks
            for i in range(len(self)):
            
                header = self.get_header(i)
                
                if header is not None and header['offset'] > offset:
                    header['offset'] += sectorChange
                    self.set_header(i, **header)
            
            # Move following chunks
            oldStart = offset + oldSectorCount
            newStart = oldStart + sectorChange
            oldData = self.mmap[oldStart * self.sectorLength :]
            self.mmap.resize(len(self.mmap) + sectorChange * self.sectorLength)
            self.mmap[newStart * self.sectorLength :] = oldData
        
        # Write header
        self.set_header(
            index, 
            offset = offset, 
            sectorCount = newSectorCount,
            timestamp = int(time.time())
        )
        
        # Write Data
        offset *= self.sectorLength
        
        self.mmap[offset : offset + 4] = length.to_bytes(4, 'big')
        self.mmap[offset + 4] = compression
        self.mmap[offset + 5 : offset + length + 4] = data
    
    def __repr__(self):
        return f'McaFile at {self.path}'
    
    def binary_map(self):
        """Return a table of booleans, representing whether a chunk exists or not"""
        length = self.sideLength
        return [[self.chunk_index(x, z) in self for x in range(length)] for z in range(length)]
    
    def check_index(self, index):
        """Raise an exception if <index> is invalid for this file"""
        if not isinstance(index, int):
            raise TypeError(f'Indices must be int, not {type(index)}')
        elif index > len(self):
            raise IndexError(f'Index must be 0-{len(self)}, not {index}')
   
    @classmethod
    def chunk_exists(cls, folder : str, x : int, z : int):
    
        path, index = cls.find_chunk(folder, x, z)
        
        if not os.path.exists(path):
            return False
        else:
            return index in cls(path)
    
    @classmethod
    def chunk_index(cls, xChunk, zChunk):
        """Return index of chunk based on its region-relative coordinates"""
        return cls.sideLength * zChunk + xChunk
    
    @classmethod
    def find_chunk(cls, folder : str, x : int, z : int):
        """Return containing file and index of chunk at <x> <z>"""
        
        xRegion, xChunk = divmod(x, cls.sideLength)
        zRegion, zChunk = divmod(z, cls.sideLength)
        
        path = os.path.join(folder, f'r.{xRegion}.{zRegion}.mca')
        index = cls.chunk_index(xChunk = xChunk, zChunk = zChunk)
        
        return path, index
    
    def get_header(self, index):
        """Return header info of chunk <index> or None if it does not exist"""
        
        self.check_index(index)
        if not os.path.exists(self.path):
            return None
        
        offset = int.from_bytes(self.mmap[index*4 : index*4 + 3], byteorder = 'big')
        sectorCount = self.mmap[index*4 + 3]
        timestamp = int.from_bytes(
            self.mmap[index*4 + self.sectorLength : index*4 + self.sectorLength + 4],
            byteorder = 'big'
        )
        
        if offset < 2 or sectorCount <= 0:
            return None
        else:
            return {'offset' : offset, 'sectorCount' : sectorCount, 'timestamp' : timestamp}
    
    @classmethod
    def read_chunk(cls, folder : str, x : int, z : int):
    
        path, index = cls.find_chunk(folder, x, z)
        return cls(path)[index]
    
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
    
    @property
    def mmap(self):
        if self._mmap is None:
            self.__enter__()
        return self._mmap
    
    def set_header(self, 
        index : int, 
        offset : int = None, 
        sectorCount : int = None,
        timestamp : int = None
    ):
        """Set <offset>, <sectorCount> and <timestamp> of chunk <index>"""
        self.check_index(index)
        
        if offset is not None:
            self.mmap[index*4 : index*4 + 3] = offset.to_bytes(length = 3, byteorder = 'big')
        
        if sectorCount is not None:
            self.mmap[index*4 + 3] = sectorCount
        
        if timestamp is not None:
            timestamp = timestamp.to_bytes(length = 4, byteorder = 'big')
            self.mmap[index*4 + self.sectorLength : index*4 + self.sectorLength + 4] = timestamp
    
    @classmethod
    def write_chunk(cls, folder : str, value):
        """Save <value> to the appropriate McaFile for chunk <x> <z> in <folder>"""
        
        x, z = value.coords_chunk
        path, index = cls.find_chunk(folder = folder, x = x, z = z)
        cls(path)[index] = value
