from minecraft.compression import compress, decompress
import minecraft.TAG as TAG

class DatFile(TAG.Compound):
    """Interface for .dat files"""
    
    __slots__ = ['_path', '_value', 'compression']
    ID = None

    def __init__( self, 
        compression : int = None,
        path : str = None,
        value : dict = None
    ):
        
        self.value = {} if value is None else value
        """NBT data"""
        
        self.compression = compression or 3
        """Compression type of contained data"""
        
        self.path = path
        """File path for writing"""
    
    def __enter__(self):
        """For context managers, no initialization steps required"""
        return self
    
    def __exit__(self, exc_type = None, exc_value = None, traceback = None):
        """For context managers. Saves changes to disk"""
        self.write()
    
    def __repr__(self):
        try:
            return f'DatFile at {self.path}'
        except ValueError:
            return 'DatFile (no file path)'
    
    @property
    def path(self):
        """Raises a clear exception in case of invalid file operations"""
        if self._path is None:
            raise ValueError(f'DatFile has no file path.')
        
        return self._path
    
    @path.setter
    def path(self, value):
        self._path = value

    @classmethod
    def open(cls, path : str):
        """Open from direct file path"""
        
        f = cls(path = path)
        f.read()
        return f

    def read(self):
        """Load data from disk"""
        with open(self.path, mode = 'rb') as f:
            data, compression = decompress(f.read())
        
        self.value = super().decode(data)
        self.compression = compression

    def write(self):
        """Save data changes to file"""
        with open(self.path, mode='w+b') as f:
            f.write(compress(data = self.to_bytes(), compression = self.compression))