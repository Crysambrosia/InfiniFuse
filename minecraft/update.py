from minecraft.blockstate import BlockState
from minecraft.chunk import Chunk

def blockStates():
    """Update blockState files based on debug map"""
    def create_property(value):
        newProperty = {}
        if value in ['false', 'true']:
            newProperty['type'] = 'bool'
        elif value.isdigit():
            newProperty['type'] = 'int'
            newProperty['min'] = value
            newProperty['max'] = value
        else:
            newProperty['type'] = 'str'
            newProperty['values'] = [value]
        return newProperty
    
    def update_properties(block : BlockState):
        """Update this block's file so that current properties are valid"""
        valid = block.validProperties
        for key, value in block['Properties'].items():
            if key not in valid:
                create_property(value)
            else:
                if valid[key]['type'] == 'bool':
                    if value not in ['false', 'true']:
                        raise ValueError(f'Found weird property {key} (was bool, can apparently also store {value})')
                elif valid[key]['type'] == 'int':
                    if not value.isdigit():
                        raise ValueError(f'Found weird property{key} (was int, can apparently also store {value})')
                    elif value < valid[key]['min']:
                        valid[key]['min'] = value
                    elif value > valid[key]['max']:
                        valid[key]['max'] = value
                elif valid[key]['type'] == 'str':
                    valid[key]['values'].append(value)
    
    testChunk = Chunk.from_world(chunkX = 0, chunkZ = 0, world = 'debug')
    for x in range(16):
        for z in range(16):
            testBlock = testChunk.get_block(x,70,z)
            

    
