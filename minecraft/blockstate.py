from minecraft.nbt import *
import json
import os

class BlockState(TAG_Compound):
    """Represents a block with all of its properties.
    
    This does NOT contain coordinates.
    Chunks, and Worlds by extension, are responsible for coordinates.
    """
    ID = NotImplemented
    
    def __init__(self, name, properties = None):

        self.value = { 'Name' : TAG_String(name), 'Properties' : TAG_Compound() }
        
        # Set all properties given to the constructor
        properties = {} if properties is None else properties
        for key, value in properties.items():
            self.set_property(key, value)

        # Set missing properties to their default values
        for key, value in self.validProperties.items():
            if key not in self['Properties']:
                self.set_property(key, value[0])

    def set_property(self, key, value):
        """Edit a property with type and value checking"""
        value = TAG_String(value)
        
        if key not in self.validProperties:
            raise KeyError(f'Invalid property {key} for block {self["Name"]}')
        if value not in self.validProperties[key]:
            raise ValueError(f'Invalid value {value} for property {key} of block {self["Name"]}')
        
        self['Properties'][key] = value

    @property
    def validProperties(self):
        """A dict containing valid properties and their valid values for this block type"""
        
        def load_from_parents(name):
        
            namespace, _, block = name.partition(':')
            folder = os.path.dirname(__file__)
            filePath = os.path.join(folder, 'blockstates', str(namespace), f'{block}.json')
            
            if not os.path.exists(filePath):
                raise FileNotFoundError(f'Unknown block {name}')
            
            with open(filePath) as f:
                data = json.load(f)
        
            try:
                for parent in data['parents']:
                    data['properties'].update(load_from_parents(parent))
            except KeyError:
                pass
            
            return data['properties']
        
        return load_from_parents(self['Name'])