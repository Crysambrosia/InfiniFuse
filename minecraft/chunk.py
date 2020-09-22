from .nbt import NBT
import time
               
# Chunk data model and interface
class Chunk():
    def __init__(self,
        payload = NBT(ID=10,payload={}), 
        timestamp = int(time.mktime(time.localtime()))
    ):
        # Chunk NBT data
        self.payload = payload
        # Last edit timestamp
        self.timestamp = timestamp
        
    def __eq__(self, other):
        if type(other) == Chunk:
            return self.payload == other.payload
        else:
            return False
        
    def __getitem__(self, key):
        return self.payload[key]
        
    def __setitem__(self, key, value):
        # Set value
        self.payload[key] = value
        # Set timestamp to time of edit
        self.timestamp = int(time.mktime(time.localtime()))
        
    def __repr__(self):
        xPos = str( self.payload['Level']['xPos'].payload )
        zPos = str( self.payload['Level']['zPos'].payload )
        timestamp = time.asctime( time.localtime(self.timestamp) )
        return (
            'Chunk at ' 
            + xPos 
            + ', ' 
            + zPos 
            + ' (Last edited ' 
            + timestamp 
            + ')'
        )
        
    def encode(self):
        return self.payload.encode()
        
    def keys(self):
        return self.payload.keys()