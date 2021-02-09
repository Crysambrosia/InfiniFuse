from .chunk import Chunk
from .compression import compress, decompress
import minecraft.TAG as TAG
import math
import mmap
import os
import re
import time

class McaFile():
    """Interface for .mca files"""
    
    def __init__(self, folder : str, x : int, z : int):
    
        self._chunkCache = [None for i in range(1024)]
        self.closed = False
        
        self.folder = folder
        self.x = x
        self.z = z
    
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
        
    def close(self, save : bool = False):
        """Close file, save changes if save = True"""
        if (not self.closed) and save:
            self.write()
        self.closed = True
    
    @property
    def file(self):
        """File containing the chunks, derived from region coordinates"""
        return os.path.join(self.folder, f'r.{self.x}.{self.z}.mca')
    
    @staticmethod
    def find_chunk(x : int, z : int):
        """Return ID of chunk at <x> <z> if the coordinates are valid"""
        
        if not 0 <= x <= 31:
            raise ValueError(f'Invalid region-relative chunk x coordinate {x} (Must be 0-31)')
        if not 0 <= z <= 31:
            raise ValueError(f'Invalid region-relative chunk z coordinate {z} (Must be 0-31)')
        
        return 32 * z + x
    
    @classmethod
    def from_world(cls, world : str, x : int, z : int, dimension : str = 'minecraft:overworld'):
        
        if dimension == 'minecraft:overworld':
            dimFolder = ''
        elif dimension == 'minecraft:the_end':
            dimFolder = 'DIM1'
        elif dimension == 'minecraft:the_nether':
            dimFolder = 'DIM-1'
        else:
            raise ValueError(f'Invalid dimension {dimension}')
        
        appdata = os.environ['APPDATA']
        folder = os.path.join(appdata, '.minecraft', 'saves', world, dimFolder, 'region')
        return cls(folder = folder, x = x, z = z)
    
    def get_chunk(self, x : int, z : int):
        """Return chunk at region-relative coordinates <x> <z>"""
        
        chunkID = self.find_chunk(x,z)
        
        if self._chunkCache[chunkID] is None:
            self.load_chunk(chunkID)
        
        return self._chunkCache[chunkID]
    
    def load_all_chunks(self):
        """Load all chunks into self._chunkCache"""
        for chunkID in range(1024):
            try:
                self.load_chunk(chunkID)
            except FileNotFoundError:
                pass

    def load_chunk(self, chunkID : int):
        """Load chunk at <chunkID> into self._chunkCache"""
        
        if self.closed:
            raise ValueError('I/O operation on closed file.')
    
        header = chunkID * 4
            
        with open(self.file, mode = 'r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as fmap:
            
                offset = 4096 * int.from_bytes(fmap[header:header + 3], 'big')
                sectorCount = fmap[header + 3]
                timestamp = int.from_bytes(fmap[header + 4096:header + 4100], 'big')

                if sectorCount > 0 and offset >= 2:
                    length = int.from_bytes(fmap[offset:offset + 4], 'big')
                    compression = fmap[offset + 4]
                    chunkData = fmap[offset + 5:offset + length + 4]
                else:
                    raise FileNotFoundError(f'Chunk doesn\'t exist ({offset},{sectorCount})')
        
        self._chunkCache[chunkID] = Chunk(
            timestamp = timestamp, 
            value = Chunk.decode( decompress(chunkData, compression)[0] )
        )
    
    @classmethod
    def open(cls, filePath):
        """Open from a direct filePath, derive x and z from file name"""
        folder = os.path.dirname(filePath)
        file = os.path.basename(filePath)
        match = re.compile(r'r\.(?P<x>-?\d+)\.(?P<z>-?\d+).mca').match(file)
        if match is None:
            raise ValueError('Invalid file name {file} (must be r.x.z.mca with x and z being coordinates)')
        return cls(folder = folder, x = match['x'], z = match['z'])
    
    def optimize(self):
        """Rewrite all chunks to fresh file, removing all junk data"""
        self.load_all_chunks()
        os.remove(self.file)
        self.save_all_chunks()
    
    def write(self):
        """Same as save_all_chunks, included for interface compatibility"""
        self.save_all_chunks()
    
    def save_all_chunks(self):
        """Save all chunks from self._chunkCache"""
        for chunkID in range(1024):
            self.save_chunk(chunkID)
    
    def save_chunk(self, chunkID : int):
        """Save chunk at <chunkID> to file at self.file"""
        
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        
        chunk = self._chunkCache[chunkID]
        
        if chunk is None:
            return
        
        # Create missing file
        if not os.path.exists(self.file):
            with open(self.file, mode='w+b') as f:
                f.truncate(8192)
        
        timestamp = int(time.time())
        header = chunkID * 4
        
        with open(self.file, mode='r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_WRITE) as fmap:
                
                offset = int.from_bytes( fmap[header:header+3], 'big')
                
                # If this chunk didn't exist in this file, find the smallest free offset to save it
                # and set compression to the newest spec, 2 (zlib)
                if offset == 0:
                    offset = max(2,*[int.from_bytes(fmap[i*4:i*4+3], 'big')+fmap[i*4+3] for i in range(1024)])
                    compression = 2
                else:
                    compression = fmap[(4096*offset) + 4]
                
                # Prepare data
                chunkData = compress(chunk.to_bytes(), compression)
                length = len(chunkData) + 1

                # Check if chunk size changed
                oldSectorCount = fmap[header+3]
                newSectorCount = math.ceil((length + 4) / 4096)
                sectorChange = newSectorCount - oldSectorCount
                
                if sectorChange:
                    # Change offsets for following chunks
                    for i in range(1024):
                        oldOffset = int.from_bytes(fmap[i * 4:i * 4 + 3], 'big')
                        
                        if oldOffset > offset:
                            fmap[i * 4:i * 4 + 3] = (oldOffset + sectorChange).to_bytes(3, 'big')
                    
                    # Move following chunks
                    oldStart = 4096 * (offset + oldSectorCount)
                    newStart = oldStart+(4096 * sectorChange)
                    data = fmap[oldStart:]
                    fmap.resize(len(fmap) + (sectorChange * 4096))
                    fmap[newStart:] = data
                
                # Write header
                fmap[header:header + 3] = offset.to_bytes(3, 'big')
                fmap[header + 3] = newSectorCount
                fmap[header + 4096:header + 4100] = timestamp.to_bytes(4, 'big')
                
                # Write Data
                offset *= 4096
                fmap[offset:offset + 4] = length.to_bytes(4, 'big')
                fmap[offset + 4] = compression
                fmap[offset + 5:offset + length + 4] = chunkData
    
    def set_chunk(self, x : int, z : int, value : Chunk):
        
        try:
            assert isinstance(value, Chunk)
        except AssertionError:
            raise ValueError(f'<value> must be a Chunk, not a {type(value)}')
        
        chunkID = self.find_chunk(x,z)
        self._chunkCache[chunkID] = value
