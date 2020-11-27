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
                self.set_property(key, value['default'])

    def set_property(self, key, value):
        """Edit a property with type and value checking"""
        value = TAG_String(value)
        
        if key not in self.validProperties:
            raise KeyError(f'Invalid property {key} for block {self["Name"]}')
        else:
            valid = self.validProperties[key]
        
        if valid['type'] == 'bool':
            if value not in ['false', 'true']:
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self["Name"]}
                    (expected \'true\' or \'false\')
                    '''
                )

        elif valid['type'] == 'int':
            if value not in range(valid['min'], valid['max']):
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self["Name"]} 
                    (expected number between {valid['min']} and {valid['max']})
                    '''
                )

        elif valid['type'] == 'str':
            if value not in valid['values']:
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self["Name"]} 
                    (expected one of {valid['values']})
                    '''
                )
        
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

            for parent in data['parents']:
                data['properties'].update(load_from_parents(parent))
            
            return data['properties']
        
        return load_from_parents(self['Name'])