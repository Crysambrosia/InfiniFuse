from .chunk import Chunk
from .compression import compress, decompress
import collections.abc
import math
import mmap
import os
import time
import util

class McaFile(collections.abc.Sequence, util.Cache):
    """Interface for .mca files
    
    For use as a context manager !
    """
    __slots__ = ['_file', '_mmap', 'path']
    sectorLength = 4096
    sideLength = 32
    
    def __init__(self, path):
        
        self._cache = {}
        """Cache containing loaded chunks"""
        
        self._file = None
        """File Object of file at self.path (after __enter__)"""
        
        self._mmap = None
        """mmap.map of file at self.path (after __enter__)"""
        
        self.path = path
        """Path of file for IO"""
    
    def __contains__(self, key):
        """Whether chunk <key> contains any data"""
        return self.get_header(key) is not None
    
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
    
    def __getitem__(self, key):
        return util.Cache.__getitem__(self, key)
    
    def __len__(self):
        return self.sideLength ** 2
    
    def __repr__(self):
        return f'McaFile at {self.path}'
    
    def binary_map(self):
        """Return a table of booleans, representing whether a chunk exists or not"""
        length = self.sideLength
        return [[self.chunk_key(x, z) in self for z in range(length)] for x in range(length)]
   
    @classmethod
    def chunk_exists(cls, folder : str, x : int, z : int):
    
        path, key = cls.find_chunk(folder, x, z)
        
        if not os.path.exists(path):
            return False
        else:
            return key in cls(path)
    
    @classmethod
    def chunk_key(cls, xChunk, zChunk):
        """Return key of chunk based on its region-relative coordinates"""
        return cls.sideLength * zChunk + xChunk
    
    @classmethod
    def find_chunk(cls, folder : str, x : int, z : int):
        """Return containing file and key of chunk at <x> <z>"""
        
        xRegion, xChunk = divmod(x, cls.sideLength)
        zRegion, zChunk = divmod(z, cls.sideLength)
        
        path = os.path.join(folder, f'r.{xRegion}.{zRegion}.mca')
        key = cls.chunk_key(xChunk = xChunk, zChunk = zChunk)
        
        return path, key
    
    def get_header(self, key):
        """Return header info of chunk <key> or None if it does not exist"""
        
        key = self.convert_key(key)
        if not os.path.exists(self.path):
            return None
        
        offset = int.from_bytes(self.mmap[key*4 : key*4 + 3], byteorder = 'big')
        sectorCount = self.mmap[key*4 + 3]
        timestamp = int.from_bytes(
            self.mmap[key*4 + self.sectorLength : key*4 + self.sectorLength + 4],
            byteorder = 'big'
        )
        
        if offset < 2 or sectorCount <= 0:
            return None
        else:
            return {'offset' : offset, 'sectorCount' : sectorCount, 'timestamp' : timestamp}
    
    @classmethod
    def read_chunk(cls, folder : str, x : int, z : int):
    
        path, key = cls.find_chunk(folder, x, z)
        return cls(path)[key]
    
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
    
    def read(self, key):
        """Return data for chunk <key>"""
        header = self.get_header(key)
        
        if header is None:
            return None
        
        offset = header['offset'] * self.sectorLength
        length = int.from_bytes(self.mmap[offset : offset + 4], 'big')
        compression = self.mmap[offset + 4]
        data = self.mmap[offset + 5 : offset + length + 4]
        
        return Chunk.from_bytes(decompress(data, compression)[0])
    
    @property
    def mmap(self):
        if self._mmap is None:
            self.__enter__()
        return self._mmap
    
    def set_header(self, 
        key : int, 
        offset : int = None, 
        sectorCount : int = None,
        timestamp : int = None
    ):
        """Set <offset>, <sectorCount> and <timestamp> of chunk <key>"""
        self.convert_key(key)
        
        if offset is not None:
            self.mmap[key*4 : key*4 + 3] = offset.to_bytes(length = 3, byteorder = 'big')
        
        if sectorCount is not None:
            self.mmap[key*4 + 3] = sectorCount
        
        if timestamp is not None:
            timestamp = timestamp.to_bytes(length = 4, byteorder = 'big')
            self.mmap[key*4 + self.sectorLength : key*4 + self.sectorLength + 4] = timestamp

    def convert_key(self, key):
    
        if not isinstance(key, int):
        
            try:
                xChunk, zChunk = key
                key = self.sideLength * zChunk + xChunk
            except:
                raise TypeError(f'Indices must be int or sequence of 2 coords, not {type(key)}')
        
        if key > len(self):
            raise keyError(f'Key must be 0-{len(self)}, not {key}')
        
        return key
   
    def convert_value(self, value):
        if not isinstance(value, Chunk):
            raise TypeError(f'Value must be a Chunk, not {value}')
        return value
   
    def write(self, key, value):
        """Save <value> as data for entry <key>"""
        
        value = self.convert_value(value)
        value.save_all()
        
        # Get header info
        header = self.get_header(key)
        
        if header is None:
            # If this chunk didn't exist in this file, find smallest free offset to save it
            
            offsets = [0]
            for i in range(len(self)):
                header = self.get_header(i)
                if header is not None:
                    offsets.append(header['offset'] + header['sectorCount'])
            
            offset = max(2, *offsets)
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
            key, 
            offset = offset, 
            sectorCount = newSectorCount,
            timestamp = int(time.time())
        )
        
        # Write Data
        offset *= self.sectorLength
        
        self.mmap[offset : offset + 4] = length.to_bytes(4, 'big')
        self.mmap[offset + 4] = compression
        self.mmap[offset + 5 : offset + length + 4] = data
    
    @classmethod
    def write_chunk(cls, folder : str, value, protected = False):
        """Save <value> to the appropriate McaFile for chunk <x> <z> in <folder>
        If <protected> is True, raise an exception if there is already a chunk there
        """
        
        x, z = value.coords_chunk
        path, key = cls.find_chunk(folder = folder, x = x, z = z)
        
        file = cls(path)
        
        if protected and key in file:
            raise IOError(f'Cannot overwrite chunk at {x}, {z} in protected mode')
        
        file[key] = value