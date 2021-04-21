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

def fuse(base : World, other : World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    offset = find_offsets(a = base, b = other)
    
    netherXchunk, netherZchunk = find_offsets(a = base, b = other)
    netherXblock = netherXchunk * 16
    netherZblock = netherZchunk * 16
    
    overworldXchunk = netherXchunk * 8
    overworldZchunk = netherZchunk * 8
    
    overworldXblock = overworldXchunk * 16
    overworldZchunk = overworldZchunk * 16
    
    
    for chunk in other.dimensions['minecraft:the_nether']:
        chunk['']['Level']['xPos'] += netherXchunk
        chunk['']['Level']['zPos'] += netherZchunk
        
        # Update all entity data that stores position
        for i, entity in enumerate(chunk['']['Level']['Entities']):
            entity['Pos'][0] += netherXblock
            entity['Pos'][2] += netherZblock
            
            for key in entity['Brain']['memories']:
                if key in [
                    'minecraft:home',
                    'minecraft:job_site',
                    'minecraft:meeting_point',
                    'minecraft:potential_job_site'
                ]:
                    memory = entity['Brain']['memories'][key]
                
                    if memory['value']['dimension'] == 'minecraft:the_nether':
                        memory['value']['pos'][0] += netherXblock
                        memory['value']['pos'][2] += netherZblock
                        
                    elif memory['value']['dimension'] == 'minecraft:overworld':
                        memory['value']['pos'][0] += overworldXblock
                        memory['value']['pos'][2] += overworldZblock
                    
                    entity['Brain']['memories'][key] = memory
            
            for key in entity:
            
                if key in [
                    'BeamTarget'
                    'FlowerPos',
                    'HivePos',
                    'Leash',
                    'PatrolTarget',
                    'WanderTarget'
                ]:
                    entity[key]['X'] += netherXblock
                    entity[key]['Z'] += netherZblock
                    
                elif key in [
                    'AX',
                    'APX',
                    'BoundX',
                    'HomePosX',
                    'SleepingX',
                    'TileX',
                    'TravelPosX',
                    'TreasurePosX'
                ]:
                    entity[key] += netherXblock
                    
                elif key in [
                    'AZ',
                    'APZ',
                    'BoundZ',
                    'HomePosZ',
                    'SleepingZ',
                    'TileZ',
                    'TravelPosZ',
                    'TreasurePosZ'
                ]:
                    entity[key] += netherZblock
            
            chunk['']['Level']['Entities'][i] = entity

def dimension_binary_map(dimension : Dimension):
    """Map all chunks from <dimension> to a two dimensional array of booleans"""
    x = []
    z = []
    maps = {}
    
    for fileName in os.listdir(dimension.folder):
        if os.path.splitext(fileName)[1] == '.mca':
            with McaFile(os.path.join(dimension.folder, fileName)) as f:
                chunkX, chunkZ = f.coords_chunk
                x += [chunkX, chunkX + 31]
                z += [chunkZ, chunkZ + 31]
                
                regionX, regionZ = f.coords_region
                maps[regionX, regionZ] = f.binary_map()
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

def find_offsets(a : World, b : World):
    """Find offsets with no conflicts to fuse the Overworld and Nether of <a> and <b>"""
    
    print(f'[{datetime.datetime.now()}] Making binary map of base overworld...')
    aOverworld = dimension_binary_map(a.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Making binary map of base nether...')
    aNether    = dimension_binary_map(a.dimensions['minecraft:the_nether'])
    # Binary maps of <a>'s overworld and nether
    
    print(f'[{datetime.datetime.now()}] Making binary map of other overworld...')
    bOverworld = dimension_binary_map(b.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Making binary map of other nether...')
    bNether    = dimension_binary_map(b.dimensions['minecraft:the_nether'])
    # Binary maps of <b>'s overworld and nether
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for netherOffset in generate_offsets():
        
        # Finding offset for the nether first makes the process faster
        # The nether is usually 8 times smaller than the overworld, and roughly the same shape
        # Thus, there is a very high chance a given nether offset will work for the overworld too
        # And it will be up to 8 times quicker to find !
        
        if not offset_conflicts(a = aNether, b = bNether, offset = netherOffset):
            overworldOffset = tuple([i*8 for i in netherOffset])
            if not offset_conflicts(a = aOverworld, b = bOverworld, offset = overworldOffset):
            
                print(f'[{datetime.datetime.now()}] Found offset : {netherOffset} for the Nether, {overworldOffset} for the overworld !')
                return netherOffset

def offset_conflicts(a, b, offset):
    """Check for conflicts if <b> was fused into <a> at <offset>"""
    
    # These variables are not stored in dicts on purpose !
    # Dict access somehow halves performance
    
    aXmax, aXmin, aZmax, aZmin, aMap = a
    # Data from dimension_binary_map for a
    
    bXmax, bXmin, bZmax, bZmin, bMap = b
    # Data from dimension_binary_map for b
    
    offsetX, offsetZ = offset
    # Offset coordinates
    
    sideLen = McaFile.sideLength
    # Side length of a region file in chunks
    
    defaultSearchMin = 0
    defaultSearchMax = sideLen - 1
    # Default search area limits inside a region file
    
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
        
    return conflict