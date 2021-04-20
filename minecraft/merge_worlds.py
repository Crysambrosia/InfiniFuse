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
  
def dimension_binary_map(dimension : Dimension):
    """Map all chunks from <dimension> to a two dimensional array of booleans"""
    print(f'[{datetime.datetime.now()}] Making binary map')
    x = []
    z = []
    maps = {}
    
    for fileName in os.listdir(dimension.folder):
        if os.path.splitext(fileName)[1] == '.mca':
            f = McaFile(os.path.join(dimension.folder, fileName))
            
            chunkX, chunkZ = f.coords_chunk
            x += [chunkX, chunkX + 31]
            z += [chunkZ, chunkZ + 31]
            
            regionX, regionZ = f.coords_region
            maps[regionX, regionZ] = f.binary_map()
    
    print(f'[{datetime.datetime.now()}] Done !')
    return max(x), min(x), max(z), min(z), maps
    
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

def fuse(base : World, other : World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    iterations = 0
    
    aXmax, aXmin, aZmax, aZmin, aMap = dimension_binary_map(base.dimensions['minecraft:overworld'])
    # Binary map of <base>'s overworld
    
    bXmax, bXmin, bZmax, bZmin, bMap = dimension_binary_map(other.dimensions['minecraft:overworld'])
    # Binary map of <other>'s overworld
    
    sideLen = McaFile.sideLength
    # Side length of a region file in chunks
    
    defaultSearchMin = 0
    defaultSearchMax = sideLen - 1
    # Default search area limits inside a region file
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for offset in generate_offsets(370):
        # Some random numbers just to test the math, comment out when not needed
        #offset = (53, 7)
        
        # These variables are not stored in dicts on purpose !
        # Dict access somehow halves performance
        
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
        
        # Check all chunks inside the overlapping area
        conflict = False
        for coords in aMap:
            regionX, regionZ = coords
            if ( 
                    regionX in range(overlapXminRegion, overlapXmaxRegion)
                and regionZ in range(overlapZminRegion, overlapZmaxRegion)
            ):
                # If region is on the edge of the overlap, search only relevant chunks
                searchXmax = overlapXmaxChunk if regionX == overlapXmaxRegion else defaultSearchMax
                searchXmin = overlapXminChunk if regionX == overlapXminRegion else defaultSearchMin
                searchZmax = overlapZmaxChunk if regionZ == overlapZmaxRegion else defaultSearchMax
                searchZmin = overlapZminChunk if regionZ == overlapZminRegion else defaultSearchMin
                
                for x, row in enumerate(aMap[coords][searchXmin : searchXmax + 1]):
                    for z, chunkExists in enumerate(row[searchZmin : searchZmax + 1]):
                        iterations += 1
                        if chunkExists:
                            
                            # Convert from search-relative to b-relative
                            realX = x + searchXmin + regionX*sideLen - offsetX
                            realZ = z + searchZmin + regionZ*sideLen - offsetZ
                            
                            # Convert to region and chunk
                            realXregion, realXchunk = divmod(realX, sideLen)
                            realZregion, realZchunk = divmod(realZ, sideLen)
                            
                            if (realXregion, realZregion) in bMap:
                                conflict = bMap[realXregion, realZregion][realXchunk][realZchunk]
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