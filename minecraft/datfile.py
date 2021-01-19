from minecraft.compression import compress, decompress
import collections.abc
import minecraft.TAG as TAG
import os
import util

class DatFile(collections.abc.MutableMapping):
    """Interface for .dat files"""

    def __init__( self, 
        value       : TAG.Compound = None, 
        compression : int = 3, 
        filePath    : str = None
    ):
        
        self.value = TAG.Compound() if value is None else value
        """NBT data as a TAG.Compound"""
        
        self.compression = compression
        """Compression type of contained data"""
        
        self._filePath = filePath
        """File path for writing"""

        self.closed = False
        """Whether this file is still open"""

    def close(self, save : bool = False):
        """Close file, save changes if save = True"""
        if (not self.closed) and save:
            self.write()
        self.closed = True
    
    @property
    def filePath(self):
        """Returns a clear error in case of invalid file operations"""
        if self._filePath is None:
            raise ValueError(f'{repr(self)} has no folder !')
        else:
            return self._filePath
    
    @filePath.setter
    def filePath(self, newValue):
        self._filePath = newValue

    @classmethod
    def open(cls, filePath : str):
        """Open from direct file path"""
        
        # Format file name for repr
        filePath = ''.join([char if char != '/' else '\\' for char in filePath])
        
        with open(filePath, mode='rb') as f:
            data = f.read()
        data, compression = decompress(data)
        
        return cls(
            value = TAG.Compound.from_bytes(data), 
            compression = compression, 
            filePath = filePath
        )

    def write(self):
        """Save data changes to file"""
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        else:
            with open(self.filePath, mode='w+b') as f:
                f.write(compress(data = self.to_bytes(), compression = self.compression))

    def __repr__(self):
        try:
            return f'DatFile at {self.filePath}'
        except ValueError:
            return 'DatFile (no file path)'

util.make_wrappers( DatFile, 
    nonCoercedMethods = [
        'keys',
        'to_bytes',
        '__delitem__', 
        '__eq__', 
        '__getitem__', 
        '__iter__',
        '__len__',
        '__setitem__'
    ]
)