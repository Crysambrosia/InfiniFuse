from .dimension import Dimension
from .mcafile import McaFile
from .world import World
import concurrent.futures
import datetime
import itertools
import minecraft.TAG as TAG
import os
import random
import struct
import util

# Find offset for map
# Offset all chunks
# Change map IDs
# Offset map items
# Offset players
# Combine player stats
# Do something with player inventory ?

def map_and_boundaries(dimension : Dimension):
    """Return binary map and boundaries of <dimension>"""
    x = []
    z = []
    
    binMap = dimension.binary_map()
    for xRegion, zRegion in binMap:
        x.append(xRegion)
        z.append(zRegion)
    
    xMax = (max(x) + 1) * McaFile.sideLength
    xMin = min(z) * McaFile.sideLength
    zMax = (max(z) + 1) * McaFile.sideLength
    zMin = min(z) * McaFile.sideLength
    
    return binMap, xMax, xMin, zMax, zMin

def find_offsets(a : World, b : World):
    """Find offsets with no conflicts to fuse the Overworld and Nether of <a> and <b>"""
    
    print(f'[{datetime.datetime.now()}] Making binary map of base overworld...')
    aOverworld = map_and_boundaries(a.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Making binary map of base nether...')
    aNether    = map_and_boundaries(a.dimensions['minecraft:the_nether'])
    # Binary maps of <a>'s overworld and nether
    
    print(f'[{datetime.datetime.now()}] Making binary map of other overworld...')
    bOverworld = map_and_boundaries(b.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Making binary map of other nether...')
    bNether    = map_and_boundaries(b.dimensions['minecraft:the_nether'])
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

def fuse(base : str, other : str):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    a = World.from_saves(base)
    b = World.from_saves(other)
    
    netherX, netherZ = find_offsets(a, b)
    
    overworldX = netherX * 8
    overworldZ = netherZ * 8
    
    cacheSize = 2048
    
    print(f'[{datetime.datetime.now()}] Transferring the nether...')
    move_dimension(
        a = a.dimensions['minecraft:the_nether'],
        b = b.dimensions['minecraft:the_nether'],
        offsetX = netherX,
        offsetZ = netherZ
    )
    print(f'[{datetime.datetime.now()}] Transferring the overworld...')
    move_dimension(
        a = a.dimensions['minecraft:overworld'],
        b = b.dimensions['minecraft:overworld'],
        offsetX = overworldX,
        offsetZ = overworldZ
    )
    
    print(f'[{datetime.datetime.now()}] Transfer done !')

def fusion_map(base : str, other : str, dimension = 'minecraft:overworld'):
    """Create a PNG idea of how two maps are going to be fused"""
    a = World.from_saves(base)
    b = World.from_saves(other)
    
    offsetX, offsetZ = find_offsets(a, b)
    if dimension == 'minecraft:overworld':
        offsetX *= 8
        offsetZ *= 8
    
    aMap, *_ = map_and_boundaries(a.dimensions[dimension])
    bMap, *_ = map_and_boundaries(b.dimensions[dimension])
    
    sideLen = McaFile.sideLength
    
    fuseMap = aMap
    for coords, region in bMap.items():
        regionX, regionZ = coords
        for x, row in enumerate(region):
            for z, chunk in enumerate(row):
                realXregion, realXchunk = divmod(x + offsetX + regionX*sideLen, sideLen)
                realZregion, realZchunk = divmod(z + offsetZ + regionZ*sideLen, sideLen)
                
                if (realXregion, realZregion) not in fuseMap:
                    fuseMap[realXregion, realZregion] = [[0 for x in range(sideLen)] for z in range(sideLen)]
                
                if chunk:
                    fuseMap[realXregion, realZregion][realXchunk][realZchunk] += 1
    
    x = []
    z = []
    for xRegion, zRegion in fuseMap:
        x.append(xRegion)
        z.append(zRegion)
    
    print(f'[{datetime.datetime.now()}] Preparing PNG data...')
    data = b""
    for zRegion in range(min(z), max(z) + 1):
        for zChunk in range(sideLen):
            data += b"\0" # no filter for this scanline
            for xRegion in range(min(x), max(x) + 1):
                if (xRegion, zRegion) in fuseMap:
                    for xChunk in range(sideLen):
                        data += (fuseMap[xRegion, zRegion][xChunk][zChunk] * 127).to_bytes(1, 'big')
                else:
                    # Write a black strip if this region doesn't exist
                    data += b'\x00' * sideLen
    
    height = (max(z) - min(z) + 1) * sideLen
    width  = (max(x) - min(x) + 1) * sideLen
    
    print(f'[{datetime.datetime.now()}] Writing PNG...')
    with open(r'C:\Users\ambro\Documents\fuseMap.png', mode = 'wb') as f:
        f.write(util.makePNG(data = data, height = height, width = width))
    
    print(f'[{datetime.datetime.now()}] Done !')
  
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

def move_chunk(chunk, offsetXchunk : int, offsetZchunk : int):
    """Offset a chunk by <offsetX> <offsetZ> chunks on the grid
    """
    
    offsetXblock = offsetXchunk * 16
    offsetZblock = offsetZchunk * 16
    
    chunk['']['Level']['xPos'] += offsetXchunk
    chunk['']['Level']['zPos'] += offsetZchunk
    
    # Update all entity data that stores position
    if 'Entities' in chunk['']['Level']:
        for i, entity in enumerate(chunk['']['Level']['Entities']):
            entity['Pos'][0] += offsetXblock
            entity['Pos'][2] += offsetZblock
            
            for idx, _ in enumerate(entity['UUID']):
                entity['UUID'][idx] = TAG.Int(random.randint(-2_147_483_648, 2_147_483_647))
            
            for key in entity:
            
                if key == 'Brain':
                    for memKey in entity['Brain']['memories']:
                        if memKey in [
                            'minecraft:home',
                            'minecraft:job_site',
                            'minecraft:meeting_point',
                            'minecraft:potential_job_site'
                        ]:
                            memory = entity['Brain']['memories'][memKey]
                        
                            # This doesn't take into account memory['value']['dimension']
                            # Since villagers become disconnected when changing dimensions,
                            # either this tag is not present when the villager is in another dimension
                            # or it will be deleted by the game next time the villager is updated
                            memory['value']['pos'][0] += offsetXblock
                            memory['value']['pos'][2] += offsetZblock
                            
                            entity['Brain']['memories'][memKey] = memory
                    
            
                if key in [
                    'BeamTarget'
                    'FlowerPos',
                    'HivePos',
                    'Leash',
                    'PatrolTarget',
                    'WanderTarget'
                ]:
                    entity[key]['X'] += offsetXblock
                    entity[key]['Z'] += offsetZblock
                    
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
                    entity[key] += offsetXblock
                    
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
                    entity[key] += offsetZblock
            
            chunk['']['Level']['Entities'][i] = entity
   
    # Update tile entities
    # This does NOT update map IDs yet !
    if 'TileEntities' in chunk['']['Level']:
        for i, entity in enumerate(chunk['']['Level']['TileEntities']):
            entity['x'] += offsetXblock
            entity['z'] += offsetZblock
            
            for key in entity:
                if key in ['ExitPortal', 'FlowerPos']:
                    entity[key]['X'] += offsetXblock
                    entity[key]['Z'] += offsetZblock
            
            chunk['']['Level']['TileEntities'][i] = entity
    
    # Update TileTicks
    if 'TileTicks' in chunk['']['Level']:
        for i, tick in enumerate(chunk['']['Level']['TileTicks']):
            tick['x'] += offsetXblock
            tick['z'] += offsetZblock
        
            chunk['']['Level']['TileTicks'][i] = tick
    
    # Update LiquidTicks
    if 'LiquidTicks' in chunk['']['Level']:
        for i, tick in enumerate(chunk['']['Level']['LiquidTicks']):
            tick['x'] += offsetXblock
            tick['z'] += offsetZblock
        
            chunk['']['Level']['LiquidTicks'][i] = tick
    
    # Update Structures
    if 'Structures' in chunk['']['Level']:
    
        # Update References
        if 'References' in chunk['']['Level']['Structures']:
            for key, reference in chunk['']['Level']['Structures']['References'].items():
                if reference != []:
                    for i, coords in enumerate(reference):
                        x = TAG.Int()
                        z = TAG.Int()
                        
                        x.unsigned = util.get_bits(coords,  0, 32)
                        z.unsigned = util.get_bits(coords, 32, 64)
                        x += offsetXchunk
                        z += offsetZchunk
                        try:
                            coords.unsigned = util.set_bits(coords.unsigned, 0, 32, x)
                            coords.unsigned = util.set_bits(coords.unsigned, 32, 64, z)
                        except struct.error as e:
                            print(x, z, coords)
                            raise e
                        
                        reference[i] = coords
                    
                    chunk['']['Level']['Structures']['References'][key] = reference
        
        # Update Starts
        if 'Starts' in chunk['']['Level']['Structures']:
            for startKey, start in chunk['']['Level']['Structures']['Starts'].items():
                if start['id'] != 'INVALID':
                    
                    start['BB'][0] += offsetXblock
                    start['BB'][2] += offsetZblock
                    start['BB'][3] += offsetXblock
                    start['BB'][5] += offsetZblock
                    
                    start['ChunkX'] += offsetXchunk
                    start['ChunkZ'] += offsetZchunk
                    
                    if 'Children' in start:
                        for i, child in enumerate(start['Children']):
                            child['BB'][0] += offsetXblock
                            child['BB'][2] += offsetZblock
                            child['BB'][3] += offsetXblock
                            child['BB'][5] += offsetZblock
                            
                            for key in child:
                                if key == 'Entrances':
                                    for iEntrance, entrance in enumerate(child['Entrances']):
                                        entrance[0] += offsetXblock
                                        entrance[2] += offsetZblock
                                        entrance[3] += offsetXblock
                                        entrance[5] += offsetZblock
                                        child['Entrances'][iEntrance] = entrance
                                    
                                elif key == 'junctions':
                                    for iJunction, junction in enumerate(child['junctions']):
                                        junction['source_x'] += offsetXblock
                                        junction['source_z'] += offsetZblock
                                        child['junctions'][iJunction] = junction
                                    
                                elif key in ['PosX', 'TPX']:
                                    child[key] += offsetXblock
                                    
                                elif key in ['PosZ', 'TPZ']:
                                    child[key] += offsetZblock
                            
                            start['Children'][i] = child
                    
                    if 'Processed' in start:
                        for i, process in enumerate(start['Processed']):
                            process['X'] += offsetXchunk
                            process['Z'] += offsetZchunk
                            start['Processed'][i] = process
                    
                    chunk['']['Level']['Structures']['Starts'][startKey] = start
    
    return chunk

def move_dimension(a : Dimension, b : Dimension, offsetX : int, offsetZ : int):
    """Move all chunks from <b> into <a> at <offsetX> <offsetZ>"""
    cacheSize = 2048
    
    for i, chunk in enumerate(b):
    
        chunk = move_chunk(chunk, offsetX, offsetZ)
        a[chunk.coords_chunk] = chunk
        
        if i % cacheSize == 0 and i != 0:
            print(f'[{datetime.datetime.now()}] Saving {cacheSize} chunks...')
            a.save_all()
            print(f'[{datetime.datetime.now()}] Saved.')
    
    a.save_all()

def offset_conflicts(a, b, offset):
    """Check for conflicts if <b> was fused into <a> at <offset>"""
    
    # These variables are not stored in dicts on purpose !
    # Dict access somehow halves performance
    
    aMap, aXmax, aXmin, aZmax, aZmin = a
    # Data from map_and_boundaries for a
    
    bMap, bXmax, bXmin, bZmax, bZmin = b
    # Data from map_and_boundaries for b
    
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
                regionX in range(overlapXminRegion, overlapXmaxRegion + 1)
            and regionZ in range(overlapZminRegion, overlapZmaxRegion + 1)
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