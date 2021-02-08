import json
import minecraft.TAG as TAG
import os

class BlockState(TAG.Compound):
    """Represents a block with all of its properties.
    
    This does NOT contain coordinates.
    Chunks, and Worlds by extension, are responsible for coordinates.
    """
    __slots__ = ['_value']
    ID = None
    
    def __init__(self, value : dict = None):
        """Create a blockstate, checking given properties for correctness"""
        
        value = {} if value is None else value
        self.value = value
    
    @classmethod
    def create_valid(cls, value : dict = None):
        """Create a BlockState if <value> is a valid representation of one"""
        value = {} if value is None else value
        
        if 'Name' not in value:
            value['Name'] = TAG.String('minecraft:air')
        
        block = cls(value)
        
        for key in block.validProperties:
            if 'Properties' not in block or key not in block['Properties']:
                block.reset_property(key)
        
        block.validate()
        return block
 
    def check_property(self, key, value = None):
        """Check if property <key> exists, and if <value> is valid for it if provided"""
        
        if key not in self.validProperties:
            raise KeyError(f'Invalid property {key} for block {self["Name"]}')
        
        if value is not None:
            valid = self.validProperties[key]
            
            if valid['type'] == 'bool' and value not in ['false', 'true']:
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self['Name']}
                    (expected 'true' or 'false')
                    '''
                )

            elif valid['type'] == 'int' and int(value) not in range(int(valid['min']), int(valid['max'])):
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self['Name']} 
                    (expected number between {valid['min']} and {valid['max']})
                    '''
                )

            elif valid['type'] == 'str' and value not in valid['values']:
                raise ValueError(
                    f'''Invalid value {value} for property {key} of block {self['Name']} 
                    (expected {'or'.join(valid['values'])}
                    '''
                )

    @property
    def filePath(self):
        """File defining this block's properties"""
        namespace, _, block = self['Name'].partition(':')
        folder = os.path.dirname(__file__)
        return os.path.join(folder, 'blockstates', str(namespace), f'{block}.json')

    def reset(self):
        """Resets all properties"""
        for key in self.validProperties:
            self.reset_property(key)

    def reset_property(self, key):
    
        self.check_property(key)
        valid = self.validProperties[key]
        
        if valid['type'] == 'bool':
            value = 'false'
        elif valid['type'] == 'int':
            value = valid['min']
        elif valid['type'] == 'str':
            value = valid['values'][0]
        
        self.set_property(key, value)

    def set_property(self, key, value):
        """Edit a property with type and value checking"""
        
        self.check_property(key, value)
        
        if 'Properties' not in self:
            self['Properties'] = TAG.Compound()
        
        self['Properties'][key] = TAG.String(value)

    def validate(self):
        """Raise an error if the state of properties is invalid"""
        if 'Properties' in self:
            for key, value in self['Properties'].items():
                self.check_property(key, value)
        for key in self.validProperties:
            if key not in self['Properties']:
                raise KeyError(f'Property {key} is not set')

    @property
    def validProperties(self):
        """A dict containing valid properties and values for this block type"""
        if not os.path.exists(self.filePath):
            raise FileNotFoundError(f'Unknown block {self["Name"]}')
        
        with open(self.filePath, mode = 'r') as f:
            return json.load(f)