import json
import minecraft.TAG as TAG
import os

class BlockState(TAG.Compound):
    """Represents a block with all of its properties.
    
    This does NOT contain coordinates.
    Chunks, and Worlds by extension, are responsible for coordinates.
    """
    ID = None
    
    def __init__(self, value : dict = None):
    
        value = {} if value is None else value
        
        if 'Name' not in value:
            value['Name'] = TAG.String('minecraft:air')
        
        self.value = value

    @classmethod
    def create_validated(cls, name : str, properties : dict = None):
        """Create a blockstate, validating all given properties and setting others to default"""
    
        newBlockState = cls({ 'Name' : TAG.String(name), 'Properties' : TAG.Compound() })
        properties = {} if properties is None else properties 
        
        # Set properties given to the constructor
        for key, value in properties.items():
            newBlockState.set_property(key, value)
        
        # Set missing properties to default
        for key in newBlockState.validProperties:
            if key not in properties:
                newBlockState.set_property(key)
        
        return newBlockState

    def set_property(self, key, value = ''):
        """Edit a property with type and value checking"""
        
        if key not in self.validProperties:
            raise KeyError(f'Invalid property {key} for block {self["Name"]}')
        
        valid = self.validProperties[key]
        value = TAG.String(value)
        
        if valid['type'] == 'bool':
            if value == '':
                value = 'false'
            elif value not in ['false', 'true']:
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self['Name']}
                    (expected 'true' or 'false')
                    '''
                )

        elif valid['type'] == 'int':
            if value == '':
                value = valid['min']
            elif value not in range(valid['min'], valid['max']):
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self['Name']} 
                    (expected number between {valid['min']} and {valid['max']})
                    '''
                )

        elif valid['type'] == 'str':
            if value == '':
                value = valid['values'][0]
            elif value not in valid['values']:
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self['Name']} 
                    (expected {'or'.join(valid['values'])}
                    '''
                )
        
        if 'Properties' not in self:
            self['Properties'] = TAG.Compound()
        
        self['Properties'][key] = value

    @property
    def filePath(self):
        """File defining this block's properties"""
        namespace, _, block = self['Name'].partition(':')
        folder = os.path.dirname(__file__)
        return os.path.join(folder, 'blockstates', str(namespace), f'{block}.json')

    @property
    def validProperties(self):
        """A dict containing valid properties and values for this block type"""
        if not os.path.exists(self.filePath):
            raise FileNotFoundError(f'Unknown block {self["Name"]}')
        
        with open(self.filePath, mode = 'r') as f:
            return json.load(f)