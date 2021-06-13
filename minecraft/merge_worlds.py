from .mcafile import McaFile
from .world import World
from .world.dimension import Dimension
import concurrent.futures
import itertools
import logging
import minecraft.TAG as TAG
import os
import random
import struct
import time
import util

datefmt = '%Y %b %d %H:%M:%S'

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s | %(message)s',
    level=logging.INFO,
    datefmt=datefmt
)

def find_offsets(destination : World, source : World):
    """Find offsets with no conflicts to fuse the Overworld and Nether of <destination> and <source>"""
    
    logging.info('Mapping destination overworld...')
    destinationOverworld = map_and_boundaries(destination.dimensions['minecraft:overworld'])
    
    logging.info('Mapping destination nether...')
    destinationNether = map_and_boundaries(destination.dimensions['minecraft:the_nether'])
    
    logging.info('Mapping source overworld...')
    graftOverworld = map_and_boundaries(source.dimensions['minecraft:overworld'])
    
    logging.info('Mapping source nether...')
    graftNether = map_and_boundaries(source.dimensions['minecraft:the_nether'])
    
    logging.info(f'Trying offsets...')
    for netherOffset in generate_offsets():
        
        # Finding offset for the nether first makes the process faster
        # The nether is usually 8 times smaller than the overworld, and roughly the same shape
        # Thus, there is a very high chance a given nether offset will work for the overworld too
        # And it will be up to 8 times quicker to find !
        
        if not offset_conflicts(
            destination = destinationNether, 
            source = graftNether, 
            offset = netherOffset
        ):
            overworldOffset = tuple([i*8 for i in netherOffset])
            if not offset_conflicts(
                destination = destinationOverworld, 
                source = graftOverworld, 
                offset = overworldOffset
            ):
            
                logging.info(f'Found {netherOffset} Nether, {overworldOffset} Overworld.')
                return netherOffset

def fuse(destination : str, source : str, offset : tuple = None):
    """Fuse <source> into <destination>. Takes a REALLY long time !
    Offset for <source> will be found automatically if <offset> is None
    
    <destination>  : Name in .minecraft/saves of the map into which to fuse <source>
    <source> : Name in .minecraft/saves of the map to fuse into <destination>
    <offset>: Tuple of two ints (xNether, zNether) representing the NETHER chunk offset of <source>. The overworld will be moved 8x as far to keep the portals connected
    """
    
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
            mapDimension = source.maps[mapId]['']['data']['dimension']
            
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
        """Move chunk from source to destination"""
        
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
                            coords.unsigned = util.set_bits(coords.unsigned, 0, 32, x)
                            coords.unsigned = util.set_bits(coords.unsigned, 32, 64, z)
                            
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
    
        destination.dimensions[dimensionName][chunk.coords_chunk] = chunk
    
    cacheSize = 2048
    # Number of chunks to be moved before clearing caches
    
    destination = World.from_saves(destination)
    source = World.from_saves(source)
    
    if offset is None:
        xChunkNether, zChunkNether = find_offsets(destination, source)
    else:
        xChunkNether, zChunkNether = offset
    
    xBlockNether = xChunkNether * 16
    zBlockNether = zChunkNether * 16
    
    xChunkOverworld = xChunkNether * 8
    zChunkOverworld = zChunkNether * 8
    
    xBlockOverworld = xChunkOverworld * 16
    zBlockOverworld = zChunkOverworld * 16
    
    
    mapIdOffset = len(destination.maps)
    
    logging.info(f'Transferring {len(source.maps):,} Maps...')
    for m in source.maps:
        
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
        
        destination.maps.append(m)
    
    logging.info(f'Transferring {len(source.players):,} Players...')
    for uuid, player in source.players.items():
    
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
        
        destination.players[uuid] = player
    
    
    worldChunkTotal = sum([len(dimension) for dimension in source.dimensions.values()])
    logging.info(f'Counted {worldChunkTotal:,} chunks to be transferred')
    
    cacheSize = 2048
    progress = 0
    startTime = time.perf_counter()
    
    for dimensionName, dimension in source.dimensions.items():
    
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
        
        dimensionChunkTotal = len(dimension)
        logging.info(f'Transferring {dimensionChunkTotal:,} chunks from {dimensionName}...')
        
        for i, chunk in enumerate(dimension):
        
            move_chunk(chunk)
            
            if (i + 1) % cacheSize == 0:
            
                destination.dimensions[dimensionName].save_all()
                
                progress += cacheSize
                elapsedTime = time.perf_counter() - startTime
                remainingTime = (elapsedTime / progress) * (worldChunkTotal - progress)
                completionTime = time.strftime(datefmt, time.localtime(time.time() + remainingTime))
                
                completion = progress / worldChunkTotal
                completionStr = f'{progress:8,}/{worldChunkTotal:8,}'
                
                logging.info(f'{completionStr} - {completion:6.2%} - ETC : {completionTime}')
            
            if i + 1 == dimensionChunkTotal:
                progress += (i + 1) % cacheSize
                destination.dimensions[dimensionName].save_all()
                logging.info(f'Finished transferring {dimensionChunkTotal:,} chunks from {dimensionName} !')
    
    logging.info(f'Transfer done !')

def fusion_map(
    destination : str, 
    source : str, 
    dimension : str = 'minecraft:overworld', 
    offset : tuple = None,
    size : int = 1024
):
    """Create a PNG idea of how two maps are going to be fused, each pixel being a chunk.
    Any overlap will be white, blank pixels are black, and occupied chunks are grey
    
    <source> is the map to be moved into <destination>
    <destination> is the map receiving <source>
    <dimension> is the string ID of a dimension, either minecraft:the_nether or minecraft:overworld
    <offset> is the pasting offset, an optimal offset will be found if unspecified
    <size> the image will be the closest multiple of 32 pixels to this number in both dimensions
    """
    destination = World.from_saves(destination)
    source = World.from_saves(source)
    
    if offset is None:
        xOffset, zOffset = find_offsets(destination, source)
    else:
        xOffset, zOffset = offset
    
    if dimension == 'minecraft:overworld':
        xOffset *= 8
        zOffset *= 8
    
    aMap, *_ = map_and_boundaries(destination.dimensions[dimension])
    bMap, *_ = map_and_boundaries(source.dimensions[dimension])
    
    if len(source.dimensions[dimension]) > len(destination.dimensions[dimension]):
        # Invert maps and offsets if source is bigger than destination
        aMap, bMap = bMap, aMap
        xOffset *= -1
        zOffset *= -1
    
    sideLen = McaFile.sideLength
    
    logging.info(f'Combining maps...')
    
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
    
    # Clamp borders at size if necessary
    limit = int(size / 64)
    maxX  = min( limit, max(x))   
    minX  = max(-limit, min(x))
    maxZ  = min( limit, max(z))
    minZ  = max(-limit, min(z))
    
    logging.info(f'Preparing PNG data...')
    data = b""
    for zRegion in range(minZ, maxZ + 1):
        for zChunk in range(sideLen):
            data += b"\0" # no filter for this scanline
            for xRegion in range(minX, maxX + 1):
                if (xRegion, zRegion) in fuseMap:
                    for xChunk in range(sideLen):
                        data += (fuseMap[xRegion, zRegion][xChunk][zChunk] * 127).to_bytes(1, 'big')
                else:
                    # Write a black strip if this region doesn't exist
                    data += b'\x00' * sideLen
    
    height = (maxZ - minZ + 1) * sideLen
    width  = (maxX - minX + 1) * sideLen
    
    logging.info(f'Writing PNG...')
    with open(r'C:\Users\ambro\Documents\fuseMap.png', mode = 'wb') as f:
        f.write(util.makePNG(data = data, height = height, width = width))
    
    logging.info(f'Done !')

def generate_offsets(minRadius : int = 0, maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric circles around the origin
    Uses Bresenham's Circle Drawing Algorithm
    """
    def yield_points(x, y):
        
            yield x, y
            yield x, -y
            yield -x, -y
            yield -x, y
            
            if x != y:
                yield y, x
                yield y, -x
                yield -y, -x
                yield -y, x
    
    def yield_circle(radius, previousCircle):
        x = 0
        y = radius
        d = 3 - (2 * radius)
        while x < y:
        
            for point in yield_points(x, y):
                if point not in previousCircle:
                    yield point
            
            if d < 0:
                d += (4 * x) + 6
            else:
                d += (4 * (x-y)) + 10
                for point in itertools.chain(yield_points(x + 1, y), yield_points(x, y - 1)):
                    if point not in previousCircle:
                        yield point
                y -= 1
            
            x += 1
    
    previousCircle = [(0,0)]
    for radius in range(minRadius, maxRadius):
    
        circle = set()
        for point in yield_circle(radius, previousCircle):
            if point not in circle:
                yield point
                circle.add(point)
        
        previousCircle = circle

def map_and_boundaries(dimension : Dimension):
    """Return binary map and boundaries of <dimension>"""
    
    binaryMap = dimension.binary_map()
    if binaryMap == {}:
        return None
    
    x = []
    z = []
    for xRegion, zRegion in binaryMap:
        x.append(xRegion)
        z.append(zRegion)
    
    xMax = (max(x) + 1) * McaFile.sideLength
    xMin = min(x) * McaFile.sideLength
    zMax = (max(z) + 1) * McaFile.sideLength
    zMin = min(z) * McaFile.sideLength
    
    return binaryMap, xMax, xMin, zMax, zMin

def offset_conflicts(destination, source, offset):
    """Check for conflicts if <source> was fused into <destination> at <offset>"""
    
    # These variables are not stored in dicts on purpose !
    # Dict access somehow halves performance
    
    if destination is None or source is None:
        return False
    
    aMap, aXmax, aXmin, aZmax, aZmin = destination
    # Data from map_and_boundaries for destination
    
    bMap, bXmax, bXmin, bZmax, bZmin = source
    # Data from map_and_boundaries for source
    
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
    
    for i in [newXmax, newXmin, newZmax, newZmin]:
        if i * 16 not in range(-Dimension.sideLength, Dimension.sideLength):
            return True
    # Cannot paste source outside of world border
    
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