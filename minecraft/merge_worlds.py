from .dimension import Dimension
from .mcafile import McaFile
from .world import World
import datetime
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
    
def old_dimension_binary_map(dimension : Dimension):
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
    
    data = {
        'map' : maps,
        'pos' : {
            'x' : {'max' : max(x), 'min' : min(x) },
            'z' : {'max' : max(z), 'min' : min(z) }
        }
    }
    
    print(f'[{datetime.datetime.now()}] Done !')
    return data
  
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
    return max(x), min(x), max(z), min(z), maps

def old_generate_offsets(maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric squares around the origin"""
    for radius in range(maxRadius):
        for x in range(-radius, radius + 1):
            if abs(x) == abs(radius):
            # Top and bottom of the square
                for z in range(-radius, radius + 1):    
                    yield {'x' : x, 'z' : z}
            else:
            # Sides of the square
                yield {'x' : x, 'z' : -radius}
                yield {'x' : x, 'z' :  radius}
    
def generate_offsets(maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric squares around the origin"""
    for radius in range(maxRadius):
        for x in range(-radius, radius + 1):
            if abs(x) == abs(radius):
            # Top and bottom of the square
                for z in range(-radius, radius + 1):    
                    yield x, z
            else:
            # Sides of the square
                yield x, -radius
                yield x,  radius

def old_fuse(base : World, other : World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    iterations = 0
    a = old_dimension_binary_map(base.dimensions['minecraft:overworld'])
    b = old_dimension_binary_map(other.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for offset in old_generate_offsets(370):
        
        # Some random numbers just to test the math, comment out when not needed
        #offset = { 'x' : 53, 'z' : 7 }
        
        # Calculate new coordinates of b
        b['new'] = {
            axis : {
                coord : b['pos'][axis][coord] + offset[axis] for coord in b['pos'][axis]
            } for axis in b['pos']
        }
        
        # Calculate absolute chunk coordinates of overlap
        overlap = {
            axis : {
                coord : {
                    'abs' : min(
                        max(a['pos'][axis]['min'], b['new'][axis][coord]), 
                        a['pos'][axis]['max']
                    )
                } for coord in a['pos'][axis]
            } for axis in a['pos']
        }
        
        # Convert to region and chunk coordinates 
        for axis in overlap:
            for coord in overlap[axis]:
                region, chunk = divmod(overlap[axis][coord]['abs'], McaFile.sideLength)
                overlap[axis][coord]['region'] = region
                overlap[axis][coord]['chunk']  = chunk
        
        # Check all chunks inside the overlapping area
        conflict = False
        for coords, region in a['map'].items():
            xRegion, zRegion = coords
            if (
                xRegion in range(overlap['x']['min']['region'], overlap['x']['max']['region'] + 1)
                and
                zRegion in range(overlap['z']['min']['region'], overlap['z']['max']['region'] + 1)
            ):
                # Set conflict search domain
                search = {
                    axis : {
                        'min' : 0,
                        'max' : McaFile.sideLength - 1
                    } for axis in a['pos']
                }
                
                # Limit search if region is on the edge of the overlap
                for coord in search['x']:
                    if xRegion == overlap['x'][coord]['region']:
                        search['x'][coord] = overlap['x'][coord]['chunk']
            
                for coord in search['z']:
                    if zRegion == overlap['z'][coord]['region']:
                        search['z'][coord] = overlap['z'][coord]['chunk']
                
                #print(f'Searching {search} in region {xRegion} {zRegion}')
                
                for x, row in enumerate(region[search['x']['min'] : search['x']['max'] + 1]):
                    for z, chunkExists in enumerate(region[x][search['z']['min'] : search['z']['max'] + 1]):
                        iterations += 1
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
            print(f'[{datetime.datetime.now()}] Done in {iterations} iterations')
            return

def fuse(base : World, other : World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    iterations = 0
    
    aXmax, aXmin, aZmax, aZmin, aMap = dimension_binary_map(base.dimensions['minecraft:overworld'])
    # Binary map of <base>'s overworld
    
    bXmax, bXmin, bZmax, bZmin, bMap = dimension_binary_map(other.dimensions['minecraft:overworld'])
    # Binary map of <other>'s overworld
    
    sidelen = McaFile.sideLength
    # Side length of a region file in chunks
    
    
    # Initialize all coords at once, outside of the loop
    # These variables are not stored in dicts on purpose !
    # Dict access somehow halves performance
    
    defaultSearchMin = 0
    defaultSearchMax = sideLen-1
    # Default search area limits inside a region file


    # New limit coords of B after offset
    newXmax = 0
    newXmin = 0
    newZmax = 0
    newZmin = 0
    
    # Absolute position of overlap
    overlapXmax = 0
    overlapXmin = 0
    overlapZmax = 0
    overlapZmin = 0
    
    # Region coords of overlap
    overlapXmaxRegion = 0
    overlapXminRegion = 0
    overlapZmaxRegion = 0
    overlapZminRegion = 0
    
    # Region-relative chunk coords of overlap
    overlapXmaxChunk = 0
    overlapXminChunk = 0
    overlapZmaxChunk = 0
    overlapZminChunk = 0
    
    # Search area inside region file
    searchXmax = 0
    searchXmin = 0
    searchZmax = 0
    searchZmin = 0
    
    # Chunk coords of region currently checked for overl
    regionX = 0
    regionZ = 0
    
    # Coordinates of chunk currently checked for overlap
    chunkX = 0
    chunkZ = 0
    chunkXchunk = 0
    chunkZchunk = 0
    chunkXregion = 0
    chunkZregion = 0
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for offset in generate_offsets(370):
        # Some random numbers just to test the math, comment out when not needed
        #offset = (53, 7)
        offsetX, offsetZ = offset
        
        newXmax = bXmax + offsetX
        newXmin = bXmin + offsetX
        newZmax = bZmax + offsetZ
        newZmin = bZmin + offsetZ
        
        overlapXmax = min(max(newXmax, aXmin), aXmax)
        overlapXmin = min(max(newXmin, aXmin), aXmax)
        overlapZmax = min(max(newZmax, aZmin), aZmax)
        overlapZmin = min(max(newZmin, aZmin), aZmax)
        
        overlapXmaxRegion, overlapXmaxChunk = divmod(overlapXmax, sideLen)
        overlapXminRegion, overlapXminChunk = divmod(overlapXmin, sideLen)
        overlapZmaxRegion, overlapZmaxChunk = divmod(overlapZmax, sideLen)
        overlapZminRegion, overlapZminChunk = divmod(overlapZmin, sideLen)
        
        for p in b['pos']:
            for i in b['pos'][p]:
            
                # Offset new coordinates of b
                b['new'][p][i] = b['pos'][p][i] + offset[i]
                
                # Find absolute position of overlap
                o['pos'][p][i] = min(max(b['new'][p][i], a['pos']['min'][i]), a['pos']['max'][i])
                
                # Convert overlap position to region and chunk
                o['reg'][p][i], o['cnk'][p][i] = divmod(o['pos'][p][i], sidelen)
        
        # Check all chunks inside the overlapping area
        conflict = False
        for coords, region in a['map'].items():
            regionPos['x'], regionPos['z'] = coords
            if ( 
                    regionPos['x'] in range(o['reg']['min']['x'], o['reg']['max']['x'] + 1)
                and regionPos['z'] in range(o['reg']['min']['z'], o['reg']['max']['z'] + 1)
            ):
                # If region is on the edge of the overlap, search only relevant chunks
                for p in search:
                    for i in search[p]:
                        if regionPos[i] == o['reg'][p][i]:
                            search[p][i] = o['cnk'][p][i]
                        else:
                            search[p][i] = defaultSearch[p]
                
                for x, row in enumerate(region[search['min']['x'] : search['max']['x'] + 1]):
                    for z, chunkExists in enumerate(region[x][search['min']['z'] : search['max']['z'] + 1]):
                        iterations += 1
                        if chunkExists:
                            
                            chunk['pos']['x'] = x
                            chunk['pos']['z'] = z
                            
                            for i in chunk['pos']:
                                # This seems to be the issue
                                # Try unwrapping this as much as possible and see if there's a difference 
                                
                                # Convert from search-relative to a-relative
                                chunk['pos'][i] += search['min'][i] + regionPos[i] * sidelen
                                
                                # Convert from a-relative to b-relative
                                chunk['pos'][i] -= offset[i]
                                
                                # Convert to region and chunk
                                chunk['reg'][i], chunk['cnk'][i] = divmod(chunk['pos'][i], sidelen)
                            
                            regionIdx = (chunk['reg']['x'], chunk['reg']['z'])
                            if regionIdx in b['map']:
                                conflict = b['map'][regionIdx][chunk['cnk']['x']][chunk['cnk']['z']]
                        if conflict:
                            break
                    if conflict:
                        break
                
            if conflict:
                break
        else:
            print(f'[{datetime.datetime.now()}] No conflict with offset {offset}')
            print(f'[{datetime.datetime.now()}] Done in {iterations} iterations')
            break

'''{'xMin': -256, 'zMin': -320, 'xLen': 512, 'zLen': 864}'''