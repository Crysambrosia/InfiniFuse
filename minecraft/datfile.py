from minecraft.compression import compress, decompress
import collections.abc
import minecraft.TAG as TAG
import os
import util

class DatFile(TAG.Compound):
    """Interface for .dat files"""

    ID = None

    def __init__( self, 
        value       : dict = None, 
        compression : int = 3, 
        filePath    : str = None
    ):
        
        self.value = {} if value is None else value
        """NBT data"""
        
        self.compression = compression
        """Compression type of contained data"""
        
        self._filePath = filePath
        if self._filePath is not None:
            # Format filePath for repr to use only \\
            self._filePath = ''.join([char if char != '/' else '\\' for char in filePath])
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
            raise ValueError(f'No file path.')
        else:
            return self._filePath
    
    @filePath.setter
    def filePath(self, newValue):
        self._filePath = newValue

    @classmethod
    def open(cls, filePath : str):
        """Open from direct file path"""
        
        with open(filePath, mode='rb') as f:
            data, compression = decompress(f.read())
        
        return cls(
            value = super().decode(data), 
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