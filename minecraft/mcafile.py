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
    
    def __init__(self, x : int, z : int, folder : str = None):
    
        self._cache = {}
        """Contains dynamically loaded chunks"""
        
        self.closed = False
        """Whether this file is still open"""
        
        self.folder = folder
        """Folder containing this .mca file"""
        
        self.x = x
        """X coordinate of this region"""
        
        self.z = z
        """Z coordinate of this region"""
    
    def __delitem__(self, key):
        """Remove chunk at given coordinates in <key> from cache"""
        if not isinstance(key, tuple):
            raise KeyError(f'Key must be x and z coordinates of chunk, not {key}')
        
        cacheID = self.cache_index(*key)
        
        del self._cache[cacheID]
    
    def __getitem__(self, key):
        """Return chunk at given coordinates in <key>"""
        if not isinstance(key, tuple):
            raise KeyError(f'Key must be x and z coordinates of chunk, not {key}')
        
        cacheID = self.cache_index(*key)
        
        if cacheID not in self._cache:
            self.load_chunk(cacheID)
        
        return self._cache[cacheID]
    
    def __repr__(self):
        try:
            return f'McaFile at {self.file}'
        except ValueError:
            return 'McaFile (No Folder)'
    
    def __setitem__(self, key, value):
        """Set chunk at given coordinates in <key> to <value>"""
        if not isinstance(key, tuple):
            raise KeyError(f'Key must be x and z coordinates of chunk, not {key}')
        if not isinstance(value, Chunk):
            raise ValueError(f'<value> must be a Chunk, not a {type(value)}')
        
        cacheID = self.cache_index(*key)
        self._cache[cacheID] = value
    
    @staticmethod
    def cache_index(x : int, z : int):
        """Return cache index of chunk at coordinates <x> <z> if they are valid."""
        
        x = int(x)
        z = int(z)
        
        if not 0 <= x <= 31:
            raise ValueError(f'Invalid region-relative chunk x coordinate {x} (Must be 0-31)')
        if not 0 <= z <= 31:
            raise ValueError(f'Invalid region-relative chunk z coordinate {z} (Must be 0-31)')
        
        return 32 * z + x
    
    def close(self, save : bool = False):
        """Close file, save changes if save = True"""
        if save and not self.closed:
            self.save()
        self.closed = True
    
    @property
    def file(self):
        """File containing the chunks, derived from region coordinates"""
        if self.folder is None:
            raise ValueError('No folder.')
        return os.path.join(self.folder, f'r.{self.x}.{self.z}.mca')
    
    def load_all_chunks(self):
        """Load all chunks into self._cache"""
        for cacheID in range(1024):
            if cacheID not in self._cache:
                try:
                    self.load_chunk(cacheID)
                except FileNotFoundError:
                    pass

    def load_chunk(self, cacheID : int):
        """Load chunk at <cacheID> into self._cache"""
        
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        
        if not 0 <= cacheID <= 1023:
            raise IndexError(f'Invalid cacheID {cacheID} (must be 0-1023)')
    
        header = cacheID * 4
        
        with open(self.file, mode = 'r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ) as fmap:
            
                offset = 4096 * int.from_bytes(fmap[header:header + 3], 'big')
                sectorCount = fmap[header + 3]

                if sectorCount > 0 and offset >= 2:
                    length = int.from_bytes(fmap[offset:offset + 4], 'big')
                    compression = fmap[offset + 4]
                    chunkData = fmap[offset + 5:offset + length + 4]
                else:
                    raise FileNotFoundError(f'Chunk doesn\'t exist ({offset},{sectorCount})')
        
        self._cache[cacheID] = Chunk.from_bytes(decompress(chunkData, compression)[0])
    
    @classmethod
    def open(cls, filePath):
        """Open from a direct filePath, derive x and z from file name"""
        folder = os.path.dirname(filePath)
        file = os.path.basename(filePath)
        match = re.compile(r'r\.(?P<x>-?\d+)\.(?P<z>-?\d+).mca').match(file)
        if match is None:
            raise ValueError(f'Invalid file name {file} (must be r.x.z.mca with x and z being coordinates)')
        return cls(folder = folder, x = match['x'], z = match['z'])
    
    def optimize(self):
        """Rewrite all chunks to fresh file, removing all junk data"""
        self.load_all_chunks()
        os.remove(self.file)
        self.save_all_chunks()
    
    def save(self):
        """Save all chunks from self._cache"""
        for i in self._cache:
            self.save_chunk(i)
    
    def save_chunk(self, cacheID : int):
        """Save chunk at <cacheID> to file at self.file"""
        
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        
        if not 0 <= cacheID <= 1023:
            raise IndexError(f'Invalid cache index {cacheID} (must be 0-1023)')
        
        if cacheID not in self._cache:
            return
        
        self._cache[cacheID].save()
        chunk = self._cache[cacheID]
        
        # Create missing file
        if not os.path.exists(self.file):
            with open(self.file, mode='w+b') as f:
                f.truncate(8192)
        
        header = cacheID * 4
        
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
                timestamp = int(time.time())
                fmap[header + 4096:header + 4100] = timestamp.to_bytes(4, 'big')
                
                # Write Data
                offset *= 4096
                fmap[offset:offset + 4] = length.to_bytes(4, 'big')
                fmap[offset + 4] = compression
                fmap[offset + 5:offset + length + 4] = chunkData
            
        del self._cache[cacheID]