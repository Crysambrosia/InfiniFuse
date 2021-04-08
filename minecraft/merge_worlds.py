import datetime
import minecraft
import os

# Find offset for map
# Offset all chunks
# Change map IDs
# Offset map items
# Offset players
# Combine player stats
# Do something with player inventory ?

def dimension_binary_map(dimension : minecraft.Dimension):
    """Map all chunks from <dimension> to a two dimensional array of booleans"""
    minX = 0
    maxX = 0
    minZ = 0
    maxZ = 0
    
    for fileName in os.listdir(dimension.folder):
        if os.path.splitext(fileName)[1] == '.mca':
            f = minecraft.McaFile(os.path.join(dimension.folder, fileName))
            x, z = f.coords_chunk
            minX = min(minX, x)
            minZ = min(minZ, z)
            # Add 32 and not 31 since range(31) stops at 30 and 31 needs to be included
            maxX = max(maxX, x + 32)
            maxZ = max(maxZ, z + 32)
    
    width  = (abs(minX) + abs(maxX))
    height = (abs(minZ) + abs(maxZ))
    
    binMap = [[minecraft.McaFile.chunk_exists(dimension.folder, minX + x, minZ + z) for x in range(width)] for z in range(height)]
    return {'map' : binMap, 'x' : minX, 'z' : minZ, 'zlen' : width, 'xlen' : height}

def generate_offsets(maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric squares around the origin"""
    
    x = 0
    z = 0
    
    for radius in range(maxRadius):
        for z in range(-radius, radius + 1):
            if abs(z) == abs(radius):
            # Top and bottom of the square
                for x in range(-radius, radius + 1):    
                    yield x, z
            else:
            # Sides of the square
                yield x, -radius
                yield x, radius

def main(base : minecraft.World, addition : minecraft.World):
    
    print(f'[{datetime.datetime.now()}] Making base binary map...')
    basemap = dimension_binary_map(base.dimensions['minecraft:overworld'])
    print(f'[{datetime.datetime.now()}] Making add binary map...')
    addmap = dimension_binary_map(addition.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for offsetX, offsetZ in generate_offsets():
        conflict = False
        for z, row in enumerate(addmap['map']):
            for x, chunkExists in enumerate(row):
            
                if chunkExists:
                    # X and Z start out relative to addmap.
                    # Adding them with addmap's origin coordinates makes them absolute
                    # Conversely, substracting basemap's origin makes them relative to basemap.
                    newRelX = x + offsetX + addmap['x'] - basemap['x']
                    newRelZ = z + offsetZ + addmap['z'] - basemap['z']
                    
                    if newRelX in range(basemap['xlen']) and newRelZ in range(basemap['zlen']):
                        conflict = basemap['map'][newRelZ][newRelX]
                        if conflict:
                            break
            
            if conflict:
                break
            
        else:
            print(f'[{datetime.datetime.now()}] No conflict with offsets {offsetX} {offsetZ}\n')
            break