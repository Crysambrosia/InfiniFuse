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
    xMin = 0
    xMax = 0
    zMin = 0
    zMax = 0
    
    for fileName in os.listdir(dimension.folder):
        if os.path.splitext(fileName)[1] == '.mca':
            f = minecraft.McaFile(os.path.join(dimension.folder, fileName))
            x, z = f.coords_chunk
            xMin = min(xMin, x)
            zMin = min(zMin, z)
            # Add 32 and not 31 since range(31) stops at 30 and 31 needs to be included
            xMax = max(xMax, x + 32)
            zMax = max(zMax, z + 32)
    
    xLen = (abs(xMin) + abs(xMax))
    zLen = (abs(zMin) + abs(zMax))
    
    binMap = [[minecraft.McaFile.chunk_exists(dimension.folder, xMin + x, zMin + z) for x in range(xLen)] for z in range(zLen)]
    return {'map' : binMap, 'xMin' : xMin, 'zMin' : zMin, 'xLen' : xLen, 'zLen' : zLen}
    #return {'xMin' : xMin, 'zMin' : zMin, 'xLen' : xLen, 'zLen' : zLen}

def generate_offsets(maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric squares around the origin"""
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

def fuse(base : minecraft.World, other : minecraft.World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    print(f'[{datetime.datetime.now()}] Making binary map of base world...')
    aMap = dimension_binary_map(base.dimensions['minecraft:overworld'])
    print(f'[{datetime.datetime.now()}] Making binary map of other world...')
    bMap = dimension_binary_map(other.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for xOffset, zOffset in generate_offsets():
    
        # Calculate coordinates of offset bMap relative to aMap
        xMinB = xOffset + bMap['xMin'] - aMap['xMin']
        zMinB = zOffset + bMap['zMin'] - aMap['zMin']
        xMaxB = xMinB + bMap['xLen']
        zMaxB = zMinB + bMap['zLen']
        
        # Calculate possible overlap from bMap's coordinates
        xMinOverlap = min(max(0, xMinB), aMap['xLen'])
        xMaxOverlap = min(max(0, xMaxB), aMap['xLen'])
        zMinOverlap = min(max(0, zMinB), aMap['zLen'])
        zMaxOverlap = min(max(0, zMaxB), aMap['zLen'])
        
        # Check all chunks inside the overlapping area
        conflict = False
        for z, row in enumerate(aMap['map'][zMinOverlap : zMaxOverlap]):
            for x, chunkExists in enumerate(row[xMinOverlap : xMaxOverlap]):
            
                if chunkExists:
                    # Coords start relative to overlap, relative to aMap
                    # Adding both overlap and aMap's origin coordinates makes the coords absolute
                    # And substracting bMap's offset origin makes them relative to offset bMap !
                    bX = x + xMinOverlap + aMap['xMin'] - (bMap['xMin'] + xOffset)
                    bZ = z + zMinOverlap + aMap['zMin'] - (bMap['zMin'] + zOffset)
                   
                    try:
                        conflict = bMap['map'][bZ][bX]
                    except IndexError as e:
                        bxMinOverlap = xMinOverlap + aMap['xMin'] - bMap['xMin']
                        bzMinOverlap = zMinOverlap + aMap['zMin'] - bMap['zMin']
                        bxMaxOverlap = xMaxOverlap + aMap['xMin'] - bMap['xMin']
                        bzMaxOverlap = zMaxOverlap + aMap['zMin'] - bMap['zMin']
                        print(f'Offsets were {xOffset} {zOffset}')
                        print(f'A relative overlap : {xMinOverlap} {zMinOverlap} to {xMaxOverlap} {zMaxOverlap}')
                        print(f'B relative overlap : {bxMinOverlap} {bzMinOverlap} to {bxMaxOverlap} {bzMaxOverlap}')
                        print(f'Was trying to check {bX, bZ}')
                        print(f'bMap dimensions are {bMap["xMin"]} {bMap["xLen"]} ; {bMap["zMin"]} {bMap["zLen"]}')
                        raise e
                    
                    if conflict:
                        break
            
            if conflict:
                break
            
        else:
            print(f'[{datetime.datetime.now()}] No conflict with offsets {xOffset} {zOffset}')
            break
    else:
        print(f'[{datetime.datetime.now()}] Fusing these maps is impossible, sorry')

'''{'xMin': -256, 'zMin': -320, 'xLen': 512, 'zLen': 864}'''