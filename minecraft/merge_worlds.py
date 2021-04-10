from .dimension import Dimension
from .mcafile import McaFile
from .world import World
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

def point(x : int = 0, z : int = 0):
    return {'x' : x, 'z' : z}

def rectangle( minimum : point = None, maximum : point = None):
    minimum = minimum or point(0, 0)
    maximum = maximum or point(0, 0)
    return {'min' : minimum, 'max' : maximum}

def dimension_binary_map(dimension : Dimension):
    """Map all chunks from <dimension> to a two dimensional array of booleans"""
    print(f'[{datetime.datetime.now()}] Making binary map')
    x = []
    z = []
    maps = {}
    
    for fileName in os.listdir(dimension.folder):
        if os.path.splitext(fileName)[1] == '.mca':
            f = McaFile(os.path.join(dimension.folder, fileName))
            xRegion, zRegion = f.coords_region
            xChunk, zChunk = f.coords_chunk
            x += [xChunk, xChunk + 31]
            z += [zChunk, zChunk + 31]
            maps[xRegion, zRegion] = f.binary_map()
    
    print(f'[{datetime.datetime.now()}] Done !')
    data = {
        'map' : maps,
        'pos' : rectangle(
            minimum = point(min(x), min(z)), 
            maximum = point(max(x), max(z))
        )
    }
    return data

def generate_offsets(maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric squares around the origin"""
    for radius in range(maxRadius):
        for x in range(-radius, radius + 1):
            if abs(x) == abs(radius):
            # Top and bottom of the square
                for z in range(-radius, radius + 1):    
                    yield point(x, z)
            else:
            # Sides of the square
                yield point(x, -radius)
                yield point(x,  radius)

def fuse(base : World, other : World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    a = dimension_binary_map(base.dimensions['minecraft:overworld'])
    b = dimension_binary_map(other.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for offset in generate_offsets():
        
        # Some random numbers just to test the math, comment out when not needed
        offset = point(53, 7)
        
        b['new'] = rectangle()
        # New coordinates of B after offset
        
        o = {
            'pos'    : rectangle(), # Absolute coords
            'region' : rectangle(), # Region coords
            'chunk'  : rectangle()  # Region-relative chunk coords
        } # Overlap region of A and B
        
        for p in b['pos']:
            for i in b['pos'][p]:
            
                b['new'][p][i] = b['pos'][p][i] + offset[i]
                
                o['pos'][p][i] = min(max(b['new'][p][i], a['pos']['min'][i]), a['pos']['max'][i])
                
                o['region'][p][i], o['chunk'][p][i] = divmod(o['pos'][p][i], McaFile.sideLength)
        
        # Check all chunks inside the overlapping area
        conflict = False
        for coords, region in a['map'].items():
            regionLoc = point(*coords)
            
            for i in regionLoc:
                
                if regionLoc[i] not in range(o['region']['min'][i], o['region']['max'][i] + 1):
                    break
            else:
                #WIP
            
            if (
                regionLoc['x'] in range(overlap['x']['min']['region'], overlap['x']['max']['region'] + 1)
                and
                regionLoc['z'] in range(overlap['z']['min']['region'], overlap['z']['max']['region'] + 1)
            ):
            
                # Set conflict search domain, limited if region is on the edge of the overlap
                search = {
                    axis : {
                        'min' : 0,
                        'max' : McaFile.sideLength - 1
                    } for axis in a['pos']
                }
                
                # Limit search if region is on the edge of the overlap
                for axis in search:
                    for coord in search[axis]:
                        if xRegion == overlap[axis][coord]['region']:
                            search[axis][coord] = overlap[axis][coord]['chunk']
                
                #print(f'Searching {search} in region {xRegion} {zRegion}')
                
                for x, row in enumerate(region[search['x']['min'] : search['x']['max'] + 1]):
                    for z, chunkExists in enumerate(region[x][search['z']['min'] : search['z']['max'] + 1]):
                        if chunkExists:
                            #print(f'Checking chunk {x} {z}')
                        
                            # Calculate real coordinates of x and z
                            realX = x + search['x']['min'] + xRegion * McaFile.sideLength
                            realZ = z + search['z']['min'] + zRegion * McaFile.sideLength
                            
                            # Offset relative to B
                            # (B is positively offset from to A, so A is negatively offset from B)
                            bX = realX - offset['x']
                            bZ = realZ - offset['z']
                            
                            # Convert to region and chunk coordinates
                            bxRegion, bxChunk = divmod(bX, McaFile.sideLength)
                            bzRegion, bzChunk = divmod(bZ, McaFile.sideLength)
                            
                            if (bxRegion, bzRegion) in b['map']:
                                if b['map'][bxRegion, bzRegion][bxChunk][bzChunk] is True:
                                    conflict = True
                        if conflict:
                            break
                    if conflict:
                        break
            if conflict:
                break
        else:
            print(f'[{datetime.datetime.now()}] No conflict with offset {offset}')
            return

'''{'xMin': -256, 'zMin': -320, 'xLen': 512, 'zLen': 864}'''