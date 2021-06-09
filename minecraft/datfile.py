from minecraft.compression import compress, decompress
import minecraft.TAG as TAG
import os

class DatFile(TAG.MutableMapping):
    """Interface for .dat files
    
    For use as a context manager
    """
    
    __slots__ = ['_value', 'compression', 'path']

    def __init__(self, path : str, compression : int = None):
        self.compression = compression
        self.path = path

    def __enter__(self):
        """Load data from path if it exists, and return self"""
    
        if os.path.exists(self.path):
        
            with open(self.path, mode = 'rb') as f:
                data, compression = decompress(f.read())
            self.value = super().decode(data)
            
        else:
        
            compression = 1
            self.value = {}
        
        self.compression = self.compression or compression
        
        return self

    def __exit__(self, exc_type = None, exc_value = None, traceback = None):
        """Save value to disk"""
        with open(self.path, mode = 'wb') as f:
            f.write(compress(data = self.to_bytes(), compression = self.compression))

    def __repr__(self):
        return f'DatFile at {self.path}'