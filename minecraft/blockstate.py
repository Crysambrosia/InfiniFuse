from minecraft.nbt import *
import json
import os

class BlockState(TAG_Compound):
    """Represents a block with all of its properties.
    
    This does NOT contain coordinates.
    Chunks, and Worlds by extension, are responsible for coordinates.
    """
    def __init__(self, Name, Properties = None):
    
        Properties = {} if Properties is None else Properties
        Properties = TAG_Compound({key:TAG_String(value) for (key, value) in Properties.items()})
    
        self.value = {
            'Name' : TAG_String(Name), 
            'Properties' : TAG_Compound({key : TAG_String(value) for (key, value) in Properties.items()})
        }
    
        if not os.path.exists(self.file):
            raise FileNotFoundError(f'Unknown block {Name}')
    
        with open(self.file) as f:
            validProperties = json.load(f)
    
        for i in self['Properties']:
            if i not in validProperties:
                raise AttributeError(f'Invalid property {i} for block {self["Name"]}')
    
        for i in validProperties:
            if i in self['Properties']:
                if self['Properties'][i] not in validProperties[i]:
                    raise ValueError(f'Invalid value {self["Properties"][i]} for property {i}')
            else:
                self['Properties'][i] = TAG_String(validProperties[i][0])

    @property
    def file(self):
        """The file where the valid properties for this block are stored"""
        namespace, _, block = self['Name'].partition(':')
        return os.path.join(os.path.dirname(__file__), 'blockstates', str(namespace), f'{block}.json')
    
    def __setitem__(self, key, value):
        if key not in self:
            raise AttributeError(f'Invalid property {key} for block {self["Name"]}')