from .mcafile import McaFile
from .world import World
from .world.dimension import Dimension
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
    
    # These make more sense as their own functions,
    # but also access to way too many variables defined here
    # to be separable from this function.
    # They don't even make sense to use on their own regardless
    
    def update_entity(entity):
        """Update an entity's data.
        
        Separated into its own function for recursive calls
        """
        entity['Pos'][0] += xBlock
        entity['Pos'][2] += zBlock
        
        for idx, _ in enumerate(entity['UUID']):
            entity['UUID'][idx] = TAG.Int(random.randint(-2_147_483_648, 2_147_483_647))
        
        for key in entity:
        
            if key == 'Passengers':
                for passengerIdx, passenger in enumerate(entity['Passengers']):
                    entity['Passengers'][passengerIdx] = update_entity(passenger)
               
            elif key == 'TileEntityData':
                entity['TileEntityData'] = update_tile_entity(entity['TileEntityData'])
               
            elif key == 'Brain':
                for memKey in entity['Brain']['memories']:
                    if memKey in [
                        'minecraft:home',
                        'minecraft:job_site',
                        'minecraft:meeting_point',
                        'minecraft:potential_job_site'
                    ]:
                        memory = entity['Brain']['memories'][memKey]
                        
                        if memory['value']['dimension'] == 'minecraft:overworld':
                            memory['value']['pos'][0] += xBlockOverworld
                            memory['value']['pos'][2] += zBlockOverworld
                            
                        elif memory['value']['dimension'] == 'minecraft:the_nether':
                            memory['value']['pos'][0] += xBlockNether
                            memory['value']['pos'][2] += zBlockNether
                        
                        entity['Brain']['memories'][memKey] = memory
                
            elif key == 'Item':
                if 'id' in entity['Item']:
                    if entity['Item']['id'] == 'minecraft:filled_map':
                        entity['Item'] = update_map_item(entity['Item'])
                
            elif key in [
                'ArmorItems',
                'HandItems', 
                'Inventory',
                'Items'
            ]:
                for itemIdx, item in enumerate(entity[key]):
                    if 'id' in item:
                        if item['id'] == 'minecraft:filled_map':
                            entity[key][itemIdx] = update_map_item(item)
            
            elif key in [
                'BeamTarget'
                'FlowerPos',
                'HivePos',
                'Leash',
                'PatrolTarget',
                'WanderTarget'
            ]:
                entity[key]['X'] += xBlock
                entity[key]['Z'] += zBlock
                
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
                entity[key] += xBlock
                
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
                entity[key] += zBlock
        
        return entity
    
    def update_map_item(item):
        """Updates a map item's contained positional data"""
        if 'Decorations' in item['tag']:
        
            mapId = item['tag']['map']
            mapDimension = b.maps[mapId]['']['data']['dimension']
            
            if isinstance(mapDimension, TAG.Byte):
                if mapDimension == 0:
                    mapDimension = 'minecraft:overworld'
                elif mapDimension == -1:
                    mapDimension = 'minecraft:the_nether'
                elif mapDimension == 1:
                    mapDimension = 'minecraft:the_end'
            
            for decorationIdx, decoration in enumerate(item['tag']['Decorations']):
            
                if mapDimension == 'minecraft:overworld':
                    decoration['x'] += xBlockOverworld
                    decoration['z'] += zBlockOverworld
                    
                elif mapDimension == 'minecraft:the_nether':
                    decoration['x'] += xBlockNether
                    decoration['z'] += zBlockNether
                
                item['tag']['Decorations'][decorationIdx] = decoration
        
        item['tag']['map'] += mapIdOffset
        return item
    
    def update_tile_entity(tile):
        
        for key in tile:
        
            if key == 'x':
                tile['x'] += xBlock
                
            elif key == 'z':
                tile['z'] += zBlock
                
            elif key == 'Items':
                for itemIdx, item in enumerate(tile['Items']):
                    if 'id' in item:
                        if item['id'] == 'minecraft:filled_map':
                            tile['Items'][itemIdx] = update_map_item(item)
                
            elif key in ['ExitPortal', 'FlowerPos']:
                tile[key]['X'] += xBlock
                tile[key]['Z'] += zBlock
        
        return tile
    
    def move_chunk(chunk):
        """Move chunk from b to a"""
        chunk['']['Level']['xPos'] += xChunk
        chunk['']['Level']['zPos'] += zChunk
        
        if 'Entities' in chunk['']['Level']:
            for i, entity in enumerate(chunk['']['Level']['Entities']):
                chunk['']['Level']['Entities'][i] = update_entity(entity)
       
        if 'TileEntities' in chunk['']['Level']:
            for i, tile in enumerate(chunk['']['Level']['TileEntities']):
                chunk['']['Level']['TileEntities'][i] = update_tile_entity(tile)
        
        if 'TileTicks' in chunk['']['Level']:
            for i, tick in enumerate(chunk['']['Level']['TileTicks']):
                tick['x'] += xBlock
                tick['z'] += zBlock
            
                chunk['']['Level']['TileTicks'][i] = tick
        
        if 'LiquidTicks' in chunk['']['Level']:
            for i, tick in enumerate(chunk['']['Level']['LiquidTicks']):
                tick['x'] += xBlock
                tick['z'] += zBlock
            
                chunk['']['Level']['LiquidTicks'][i] = tick
        
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
                            x += xChunk
                            z += zChunk
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
                        
                        start['BB'][0] += xBlock
                        start['BB'][2] += zBlock
                        start['BB'][3] += xBlock
                        start['BB'][5] += zBlock
                        
                        start['ChunkX'] += xChunk
                        start['ChunkZ'] += zChunk
                        
                        if 'Children' in start:
                            for i, child in enumerate(start['Children']):
                                child['BB'][0] += xBlock
                                child['BB'][2] += zBlock
                                child['BB'][3] += xBlock
                                child['BB'][5] += zBlock
                                
                                for key in child:
                                    if key == 'Entrances':
                                        for iEntrance, entrance in enumerate(child['Entrances']):
                                            entrance[0] += xBlock
                                            entrance[2] += zBlock
                                            entrance[3] += xBlock
                                            entrance[5] += zBlock
                                            child['Entrances'][iEntrance] = entrance
                                        
                                    elif key == 'junctions':
                                        for iJunction, junction in enumerate(child['junctions']):
                                            junction['source_x'] += xBlock
                                            junction['source_z'] += zBlock
                                            child['junctions'][iJunction] = junction
                                        
                                    elif key in ['PosX', 'TPX']:
                                        child[key] += xBlock
                                        
                                    elif key in ['PosZ', 'TPZ']:
                                        child[key] += zBlock
                                
                                start['Children'][i] = child
                        
                        if 'Processed' in start:
                            for i, process in enumerate(start['Processed']):
                                process['X'] += xChunk
                                process['Z'] += zChunk
                                start['Processed'][i] = process
                        
                        chunk['']['Level']['Structures']['Starts'][startKey] = start
    
        a.dimensions[dimensionName][chunk.coords_chunk] = chunk
    
    cacheSize = 2048
    # Number of chunks to be moved before clearing caches
    
    a = World.from_saves(base)
    b = World.from_saves(other)
    
    xChunkNether, zChunkNether = find_offsets(a, b)
    
    xBlockNether = xChunkNether * 16
    zBlockNether = zChunkNether * 16
    
    xChunkOverworld = xChunkNether * 8
    zChunkOverworld = zChunkNether * 8
    
    xBlockOverworld = xChunkOverworld * 16
    zBlockOverworld = zChunkOverworld * 16
    
    cacheSize = 2048
    
    mapIdOffset = len(a.maps)
    
    print(f'[{datetime.datetime.now()}] Transferring {len(b.maps)} Maps...')
    for m in b.maps:
        
        mapDimension = m['']['data']['dimension']
        
        if isinstance(mapDimension, TAG.Byte):
            if mapDimension == 0:
                mapDimension = 'minecraft:overworld'
                
            elif mapDimension == -1:
                mapDimension = 'minecraft:the_nether'
                
            elif mapDimension == 1:
                mapDimension = 'minecraft:the_end'
                
            else:
                mapDimension = 'unknown'
        
        if mapDimension == 'minecraft:overworld':
            xBlock = xBlockOverworld
            zBlock = zBlockOverworld
        elif mapDimension == 'minecraft:the_nether':
            xBlock = xBlockNether
            zBlock = zBlockNether
        else:
            continue
            # Other dimensions are not transferred, so we don't bother with their maps
        
        m['']['data']['xCenter'] += xBlock
        m['']['data']['zCenter'] += zBlock

        if 'banners' in m['']['data']:
            for i, banner in enumerate(m['']['data']['banners']):
                banner['Pos']['X'] += xBlock
                banner['Pos']['Z'] += zBlock
                m['']['data']['banners'][i] = banner
        
        if 'frames' in m['']['data']:
            for i, frame in enumerate(m['']['data']['frames']):
                frame['Pos']['X'] += xBlock
                frame['Pos']['Z'] += zBlock
                m['']['data']['frames'][i] = frame
        
        a.maps.append(m)
    
    print(f'[{datetime.datetime.now()}] Transferring {len(b.players)} Players...')
    for uuid, player in b.players.items():
    
        dimension = player['playerdata']['']['Dimension']
        
        if dimension == -1 or dimension == 'minecraft:the_nether':
            xBlock = xBlockNether
            zBlock = zBlockNether
        if dimension == 0  or dimension == 'minecraft:overworld':
            xBlock = xBlockOverworld
            zBlock = zBlockOverworld
        else:
            # Other dimensions are not transferred, so players inside of them are discarded
            continue
        
        player['playerdata']['']['Pos'][0] += xBlock
        player['playerdata']['']['Pos'][2] += zBlock
        
        if 'SpawnX' in player['playerdata'][''] and 'SpawnZ' in player['playerdata']['']:
            if (
                'SpawnDimension' in player['playerdata']['']
                and player['playerdata']['']['SpawnDimension'] == 'minecraft:the_nether'
            ):
                xBlock = xBlockNether
                zBlock = zBlockNether
            else:
                xBlock = xBlockOverworld
                zBlock = zBlockOverworld
        
            player['playerdata']['']['SpawnX'] += xBlock
            player['playerdata']['']['SpawnZ'] += zBlock
        
        a.players[uuid] = player
    
    for dimensionName, dimension in b.dimensions.items():
    
        if dimensionName == 'minecraft:overworld':
            xBlock = xBlockOverworld
            zBlock = zBlockOverworld
            xChunk = xChunkOverworld
            zChunk = zChunkOverworld
        elif dimensionName == 'minecraft:the_nether':
            xBlock = xBlockNether
            zBlock = zBlockNether
            xChunk = xChunkNether
            zChunk = zChunkNether
        else:
            # Transferring other dimensions is not supported
            continue
        
        chunkTotal = len(dimension)
        print(f'[{datetime.datetime.now()}] Transferring {chunkTotal} chunks from {dimensionName}...')
        
        for i, chunk in enumerate(dimension):
            
            move_chunk(chunk)
            
            if i % cacheSize == 0 and i > 0:
                a.dimensions[dimensionName].save_all()
                print(f'[{datetime.datetime.now()}] Processed {i}/{chunkTotal} chunks...')
        
        a.dimensions[dimensionName].save_all()
        print(f'[{datetime.datetime.now()}] Finished transferring {i} chunks for {dimensionName} !')
    
    print(f'[{datetime.datetime.now()}] Transfer done !')

def fusion_map(base : str, other : str, dimension = 'minecraft:overworld'):
    """Create a PNG idea of how two maps are going to be fused"""
    a = World.from_saves(base)
    b = World.from_saves(other)
    
    xOffset, zOffset = find_offsets(a, b)
    if dimension == 'minecraft:overworld':
        xOffset *= 8
        zOffset *= 8
    
    aMap, *_ = map_and_boundaries(a.dimensions[dimension])
    bMap, *_ = map_and_boundaries(b.dimensions[dimension])
    
    sideLen = McaFile.sideLength
    
    fuseMap = aMap
    for coords, region in bMap.items():
        xRegion, zRegion = coords
        for x, row in enumerate(region):
            for z, chunk in enumerate(row):
                realXregion, realXchunk = divmod(x + xOffset + xRegion*sideLen, sideLen)
                realZregion, realZchunk = divmod(z + zOffset + zRegion*sideLen, sideLen)
                
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

def offset_conflicts(a, b, offset):
    """Check for conflicts if <b> was fused into <a> at <offset>"""
    
    # These variables are not stored in dicts on purpose !
    # Dict access somehow halves performance
    
    aMap, aXmax, aXmin, aZmax, aZmin = a
    # Data from map_and_boundaries for a
    
    bMap, bXmax, bXmin, bZmax, bZmin = b
    # Data from map_and_boundaries for b
    
    xOffset, zOffset = offset
    # Offset coordinates
    
    sideLen = McaFile.sideLength
    # Side length of a region file in chunks
    
    defaultSearchMin = 0
    defaultSearchMax = sideLen - 1
    # Default search area limits inside a region file
    
    newXmax = bXmax + xOffset
    newXmin = bXmin + xOffset
    newZmax = bZmax + zOffset
    newZmin = bZmin + zOffset
    
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
    
        xRegion, zRegion = coords
        
        if ( 
                xRegion in range(overlapXminRegion, overlapXmaxRegion + 1)
            and zRegion in range(overlapZminRegion, overlapZmaxRegion + 1)
        ):
            # If region is on the edge of the overlap, search only relevant chunks
            searchXmax = overlapXmaxChunk if xRegion == overlapXmaxRegion else defaultSearchMax
            searchXmin = overlapXminChunk if xRegion == overlapXminRegion else defaultSearchMin
            searchZmax = overlapZmaxChunk if zRegion == overlapZmaxRegion else defaultSearchMax
            searchZmin = overlapZminChunk if zRegion == overlapZminRegion else defaultSearchMin
            
            for x, row in enumerate(aMap[coords][searchXmin : searchXmax + 1]):
                for z, chunkExists in enumerate(row[searchZmin : searchZmax + 1]):
                
                    if chunkExists:
                        
                        # Convert from search-relative to b-relative
                        realX = x + searchXmin + xRegion*sideLen - xOffset
                        realZ = z + searchZmin + zRegion*sideLen - zOffset
                        
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