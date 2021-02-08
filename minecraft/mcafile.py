from .chunk import Chunk
from .compression import compress, decompress
import minecraft.TAG as TAG
import mmap
import os

class McaFile():
    """Interface for .mca files"""
    
    def __init__(self, fileName : str):
        self.fileName = fileName
        self._chunkCache = [None for i in range(1024)]
    
    def __getitem__(self, key):
    
        try:
            assert isinstance(key, tuple)
            assert len(key) == 2
        except AssertionError:
            raise KeyError(f'Key must be x and z coordinate of chunk, not {key}')
        
        return self.get_chunk(x = key[0], z = key[1])
    
    def __setitem__(self, key, value):
    
        try:
            assert isinstance(key, tuple)
            assert len(key) == 2
        except AssertionError:
            raise KeyError(f'Key must be x and z coordinate of chunk, not {key}')
        
        self.set_chunk(x = key[0], z = key[1], value = value)
    
    @staticmethod
    def find_chunk(x : int, z : int):
    
        if not 0 <= x <= 31:
            raise ValueError(f'Invalid region-relative chunk x coordinate {x} (Must be 0-31)')
        if not 0 <= z <= 31:
            raise ValueError(f'Invalid region-relative chunk z coordinate {z} (Must be 0-31)')
        
        return 32 * z + x
    
    def get_chunk(self, x : int, z : int):
    
        chunkID = self.find_chunk(x,z)
    
        if self._chunkCache[chunkID] is None:
            self._chunkCache[chunkID] = self.load_chunk(chunkID)
        
        return self._chunkCache[chunkID]
    
    def load_chunk(self, chunkID : int):
        """Return chunk at <chunkID> in file at self.fileName"""
        
        header = chunkID * 4
        
        with open(self.fileName, mode = 'r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as fmap:
            
                offset = 4096 * int.from_bytes( fmap[header:header+3], 'big')
                sectorCount = fmap[header+3]
                timestamp = int.from_bytes( fmap[header+4096:header+4100], 'big')

                if sectorCount > 0 and offset >= 2:
                    length = int.from_bytes(fmap[offset:offset+4], 'big')
                    compression = fmap[offset+4]
                    chunkData = fmap[offset+5 : offset+length+4]
                else:
                    raise FileNotFoundError(f'Chunk doesn\'t exist ({offset},{sectorCount})')
                    
        return Chunk(
            timestamp = timestamp, 
            value = Chunk.decode( decompress(chunkData, compression)[0] )
        )
    
    def save_chunk(self, chunkID : int):
    
        if not os.path.exists(self.fileName):
            with open(self.file, mode='w+b') as f:
                f.truncate(8192)
    
    def set_chunk(self, x : int, z : int, value : Chunk):
        
        try:
            assert isinstance(value, Chunk)
        except AssertionError:
            raise ValueError(f'<value> must be a Chunk, not a {type(value)}')
        
        chunkID = self.find_chunk(x,z)
        self._chunkCache[chunkID] = value
