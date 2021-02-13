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
    
    def __init__(self, file : str = None):
    
        self.file = file
        """Path of this .mca file"""
    
    def __getitem__(self, key):
    
        with open(self.file, mode='r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_WRITE) as fmap:
                value = fmap[key]
        
        if isinstance(key, slice) and key.stop - key.start > 1:
            value = int.from_bytes(value, 'big')
        
        return value
    
    def __setitem__(self, key, value : int):
    
        if isinstance(key, slice):
            value = value.to_bytes(key.stop - key.start, 'big')
        
        with open(self.file, mode='r+b') as f:
            with mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_WRITE) as fmap:
                fmap[key] = value
    
    def __repr__(self):
        return f'McaFile {self.file}'
    
    @classmethod
    def from_coords(folder : str, x : int, z : int):
        """Open from a folder, get file name from coords"""
        return cls(file = os.path.join(folder, f'r.{x}.{z}.mca'))
    
    def get_offset(self, key : int):
        """Get offset of chunk <key>"""
        return self[4 * key:4 * key + 3]
    
    def get_sectorCount(self, key : int):
        """Get sector count of chunk <key>"""
        return self[4 * key + 3]
    
    def get_timestamp(self, key : int):
        """Get time stamp of chunk <key>"""
        return self[key * 4 + 4096: key * 4 + 4100]
    
    def set_offset(self, key : int, value : int):
        """Set offset of chunk <key> to value"""
        self[4 * key:4 * key + 3] = value
    
    def set_sectorCount(self, key : int, value : int):
        """Set sector count of chunk <key> to <value>"""
        self[4 * key + 3] = value
    
    def set_timestamp(self, key, value):
        """Set time stamp of chunk <key> to <value>"""
        self[key * 4 + 4096: key * 4 + 4100] = value
    