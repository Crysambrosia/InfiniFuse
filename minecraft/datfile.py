from .nbt import NBT
import os
import gzip
import zlib

class DatFile():
    """Interface for .dat files"""

    def __init__(self, payload : NBT, file : str):
        
        self.payload = payload
        """NBT data (usually a TAG_Compound)"""
        
        self.file = file
        """File path for writing"""

        self.closed = False
        """Whether this file is still open"""

    def __eq__(self, other):
        """Returns self==value, ignoring file names"""
        if type(other) == openDAT:
            return self.payload == other.payload
        else:
            return False

    def __getitem__(self, key):
        return self.payload[key]

    def __setitem__(self, key, value):
        if type(value) == type( self.payload[key] ):
            self.payload[key] = value
        else:
            raise TypeError('Value must be ' + str(type( self.payload[key] )) + ', not ' + str(type(value)) )

    def __repr__(self):
        return f'DatFile at {self.file}'

    def close(self, save : bool = False):
        """Close file, save changes if save = True"""
        if (not self.closed) and save:
            self.write()
        self.closed = True

    def encode(self):
        """Encode this file's payload"""
        return self.payload.encode()
    
    def keys(self):
        return self.payload.keys()

    @classmethod
    def open(cls, file : str):
        """Open from direct file path"""
        
        # Format file name for repr
        formattedFile = ''
        for character in file:
            if character == '/':
                formattedFile += '\\'
            else:
                formattedFile += character
        file = formattedFile
            
        with open(file, mode='rb') as openFile:
            data = openFile.read()

        return cls(payload = NBT.decode(data), file=file)

    def write(self):
        """Save data changes to file"""
        
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        else:
            with open(self.file, mode='w+b') as NBTFile:
            
                # Write encoded payload to file
                NBTFile.write( self.encode() )
                