from minecraft.blockstate import BlockState
from minecraft.chunk import Chunk
import json

def blockStates():
    """Update blockState files based on debug map"""
    
    def create_property(value):
        """Create a property dict fitting the given value"""
        prop = {}
        if value in ['false', 'true']:
            prop['type'] = 'bool'
        elif value.isdigit():
            prop['type'] = 'int'
            prop['min'] = value
            prop['max'] = value
        else:
            prop['type'] = 'str'
            prop['values'] = [value]
        return prop
    
    def convert_property(prop : dict):
        """Convert a property to str type
        Used when a property appears to store multiple data types
        """
        if prop['type'] == 'bool':
            values = ['false', 'true']
        elif prop['type'] == 'int':
            values = [i for i in range(prop['min'], prop['max'])]
        else:
            raise TypeError('Can only convert bool and int properties to str')
        
        return {'type':'str', 'values':values}
    
    def update_property(prop: dict, value):
        if prop['type'] == 'bool':
            if value not in ['false', 'true']:
                prop = convert_property(prop)
            
        elif prop['type'] == 'int':
            if not value.isdigit():
                prop = convert_property(prop)
            elif value < prop['min']:
                prop['min'] = value
            elif value > prop['max']:
                prop['max'] = value
    
        if prop['type'] == 'str':
            if value not in prop['values']:
                prop['values'].append(value)
        
        return prop
    
    def update_block(block : BlockState):
        """Update this block's file so that current properties are valid"""
        try:
            valid = block.validProperties
        except FileNotFoundError:
            valid = {}
        
        try:
            for key, value in block['Properties'].items():
                value = str(value)
                if key in valid:
                    valid[key] = update_property(valid[key], value)
                else:
                    valid[key] = create_property(value)
        except KeyError:
            pass
        
        with open(block.filePath, mode='w') as f:
            json.dump(valid, f, indent = 4)
    
    chunkX = 0
    chunkZ = 0
    emptyChunks = 0
    while True:
    
        testChunk = Chunk.from_world(chunkX, chunkZ, world = 'debug')
        emptyBlocks = 0
        print(f'Reading {testChunk}')
        
        for x in range(1,16,2):
            for z in range(1,16,2):
            
                testBlock = testChunk.get_block(x,70,z)
                
                if testBlock['Name'] == 'minecraft:air':
                    emptyBlocks += 1
                
                update_block(testBlock)
        
        if emptyBlocks >= 64:
        
            emptyChunks += 1
            
            if emptyChunks > 1:
                break
            else:
                chunkX = 0
                chunkZ += 1
            
        else:
            chunkX += 1
            emptyChunks = 0
    