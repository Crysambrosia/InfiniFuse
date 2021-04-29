from .chunk import Chunk
from .compression import compress, decompress
import collections.abc
import concurrent.futures
import math
import os
import time
import util

class McaFile(collections.abc.Sequence, util.Cache):
    """Interface for .mca files"""
    
    __slots__ = ['_cache', 'path', 'value']
    sectorLength = 4096
    sideLength = 32
    
    def __init__(self, path : str = None, value : bytearray = None):
        
        self._cache = {}
        """Cache containing loaded chunks"""
        
        self.path = path
        """Path of file for IO"""
        
        self.value = value or bytearray(self.sectorLength*2)
        """Content of represented file as a bytearray"""
    
    def __contains__(self, key):
        """Whether chunk <key> contains any data"""
        return self.get_header(key) is not None
    
    def __del__(self):
        self.__exit__()
    
    def __enter__(self):
        """Return self"""
        return self
    
    def __exit__(self, exc_type = None, exc_value = None, traceback = None):
        """Save all changes"""
        self.write()
    
    def __getitem__(self, key):
        return util.Cache.__getitem__(self, key)
    
    def __iter__(self):
        with concurrent.futures.ProcessPoolExecutor() as e:
            for chunk in e.map(self.load_value, range(len(self))):
                yield chunk
    
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
        
        offset = int.from_bytes(self.value[key*4 : key*4 + 3], byteorder = 'big')
        sectorCount = self.value[key*4 + 3]
        timestamp = int.from_bytes(
            self.value[key*4 + self.sectorLength : key*4 + self.sectorLength + 4],
            byteorder = 'big'
        )
        
        if offset < 2 or sectorCount <= 0:
            return None
        else:
            return {'offset' : offset, 'sectorCount' : sectorCount, 'timestamp' : timestamp}
    
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
    
    def load_value(self, key):
        """Return data for chunk <key>"""
        header = self.get_header(key)
        
        if header is None:
            return None
        
        offset = header['offset'] * self.sectorLength
        length = int.from_bytes(self.value[offset : offset + 4], 'big')
        compression = self.value[offset + 4]
        data = self.value[offset + 5 : offset + length + 4]
        
        return Chunk.from_bytes(decompress(data, compression)[0])
    
    def set_header(self, 
        key : int, 
        offset : int = None, 
        sectorCount : int = None,
        timestamp : int = None
    ):
        """Set <offset>, <sectorCount> and <timestamp> of chunk <key>"""
        self.convert_key(key)
        
        if offset is not None:
            self.value[key*4 : key*4 + 3] = offset.to_bytes(length = 3, byteorder = 'big')
        
        if sectorCount is not None:
            self.value[key*4 + 3] = sectorCount
        
        if timestamp is not None:
            timestamp = timestamp.to_bytes(length = 4, byteorder = 'big')
            self.value[key*4 + self.sectorLength : key*4 + self.sectorLength + 4] = timestamp

    def convert_key(self, key):
    
        if not isinstance(key, int):
        
            try:
                xChunk, zChunk = key
                key = self.sideLength * zChunk + xChunk
            except:
                raise TypeError(f'Indices must be int or sequence of 2 coords, not {type(key)}')
        
        if key > len(self):
            raise IndexError(f'Key must be 0-{len(self)}, not {key}')
        
        return key
   
    def convert_value(self, value):
        if not isinstance(value, Chunk):
            raise TypeError(f'Value must be a Chunk, not {value}')
        return value
    
    @classmethod
    def open(cls, path):
        """Open from <path>"""
        with open(path, mode = 'rb') as f:
            return cls(path = path, value = f.read())
    
    def save(self, key):
        """Save changes from cache to value, and from value to disk"""
        util.Cache.save(self, key)
        self.write()
    
    def save_all(self):
        util.Cache.save_all(self)
        self.write()
   
    def save_value(self, key, value):
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
            oldStart = (offset + oldSectorCount) * self.sectorLength
            self.value = self.value[:oldStart] + bytearray(sectorChange*self.sectorLength) + self.value[oldStart:]
            
        
        # Write header
        self.set_header(
            key, 
            offset = offset, 
            sectorCount = newSectorCount,
            timestamp = int(time.time())
        )
        
        # Write Data
        offset *= self.sectorLength
        
        self.value[offset : offset + 4] = length.to_bytes(4, 'big')
        self.value[offset + 4] = compression
        self.value[offset + 5 : offset + length + 4] = data
    
    def write(self):
        with open(self.path, mode = 'wb') as f:
            f.write(self.value)