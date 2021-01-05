import minecraft

testChunk = minecraft.Chunk.from_world(chunkX = 0, chunkZ = 0, world = 'debug')
for x in range(16):
    for y in range(256):
        for z in range(16):
            if testChunk.get_block(x,y,z)['Name'] == minecraft.TAG_String('minecraft:stone'):
                print(str(x), str(y), str(z))