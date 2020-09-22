from .nbt import NBT
import os
import gzip
import zlib

# Interface for .dat files
class openDAT():

    def __init__(self, fileName = 'world\\level.dat'):
    
        # Format file name
        newFileName = ''
        for character in fileName:
            if character == '/':
                newFileName += '\\'
            else:
                newFileName += character
        fileName = newFileName
        
        # Load file into memory
        try:
            # Try complete file path
            with open(fileName, mode='r+b') as NBTFile:
                rawNBT = NBTFile.read()
        except FileNotFoundError:
            # Try minecraft subdirectory
            fileName = (
                os.environ['APPDATA']
                + '\\.minecraft\\saves\\'
                + fileName
            )
            with open(fileName, mode='r+b') as NBTFile:
                rawNBT = NBTFile.read()

        # Decode the file
        payload = NBT.decode(rawNBT)
        
        # Wether this file is still writable
        self.closed = False
        # File path for writing to
        self.name = fileName
        # File NBT payload
        self.payload = payload
       
    def __eq__(self, other):
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
        return self.name + ':\n' + repr(self.payload)
        
    # Closes file and discards unsaved edits
    def close(self, save=False):
        if (not self.closed) and save:
            self.write()
        self.closed = True
       
    # Returns encoded payload
    def encode(self):
        return self.payload.encode()
    
    def keys(self):
        return self.payload.keys()
        
    # Save changes to file
    def write(self):
        if self.closed:
            raise ValueError('I/O operation on closed file.')
        else:
            with open(self.name, mode='w+b') as NBTFile:
            
                # Write encoded payload to file
                NBTFile.write( self.encode() )
