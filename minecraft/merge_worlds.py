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
    
    data = {
        'map' : maps,
        'pos' : {
            'x' : {'max' : max(x), 'min' : min(x) },
            'z' : {'max' : max(z), 'min' : min(z) }
        }
    }
    
    print(f'[{datetime.datetime.now()}] Done !')
    return data

def generate_offsets(maxRadius : int = 3_750_000):
    """Generate x and z coordinates in concentric squares around the origin"""
    for radius in range(maxRadius):
        for z in range(-radius, radius + 1):
            if abs(z) == abs(radius):
            # Top and bottom of the square
                for x in range(-radius, radius + 1):    
                    yield {'x' : x, 'z' : z}
            else:
            # Sides of the square
                yield {'x' : x, 'z' : -radius}
                yield {'x' : x, 'z' : radius}

def fuse(base : World, other : World):
    """Fuse two maps into one. Takes a REALLY long time ! (Could be days)"""
    
    a = dimension_binary_map(base.dimensions['minecraft:overworld'])
    b = dimension_binary_map(other.dimensions['minecraft:overworld'])
    
    print(f'[{datetime.datetime.now()}] Trying offsets...')
    for offset in generate_offsets():
        
        # Some random numbers just to test the math, comment out when not needed
        offset = { 'x' : 53, 'z' : 7 }
        
        # Calculate new coordinates of b
        print(f'A : \n{a["pos"]}')
        print(f'B : \n{b["pos"]}')
        print(f'Offset : \n{offset}')
        b['new'] = {
            axis : {
                coord : b['pos'][axis][coord] + offset[axis] for coord in b['pos'][axis]
            } for axis in b['pos']
        } # Tested
        print(f'Bnew : \n{b["new"]}')
        
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
        } # Tested
        print(f'Overlap : \n{overlap}')
        
        # Convert to region and chunk coordinates 
        for axis in overlap:
            for coord in overlap[axis]:
                region, chunk = divmod(overlap[axis][coord]['abs'], McaFile.sideLength)
                overlap[axis][coord]['region'] = region
                overlap[axis][coord]['chunk']  = chunk
        # Tested
        print(f'Converted Overlap : \n{overlap}\n')
        
        # Check all chunks inside the overlapping area
        conflict = False
        for xReg in range(overlap['x']['min']['region'], overlap['x']['max']['region'] + 1):
            for zReg in range(overlap['z']['min']['region'], overlap['z']['max']['region'] + 1):
                if (xReg, zReg) in a['map']:
                    
                    # Set conflict search domain
                    search = {
                        axis : {
                            'min' : 0,
                            'max' : McaFile.sideLength - 1
                        } for axis in a['pos']
                    }
                    
                    # Limit search if region is on the edge of the overlap
                    for coord in search['x']:
                        if xReg == overlap['x'][coord]['region']:
                            search['x'][coord] = overlap['x'][coord]['chunk']
                
                    for coord in search['z']:
                        if zReg == overlap['z'][coord]['region']:
                            search['z'][coord] = overlap['z'][coord]['chunk']
                    
                    print(f'I want to search {search} in region {xReg} {zReg}')
                    
        return
        '''
        conflict = False
        for x in range(overlap['x']['min']['abs'], overlap['x']['max']['abs'] + 1):
            for z in range(overlap['z']['min']['abs'], overlap['z']['max']['abs'] + 1):
            
                axRegion, axChunk = divmod(x, McaFile.sideLength)
                azRegion, azChunk = divmod(x, McaFile.sideLength)\
                
                if (axRegion, azRegion) in a['map'] and a['map'][axRegion,azRegion][axChunk][azChunk] == True:
                    bxRegion, bxChunk = divmod(x + offset['x'], McaFile.sideLength)
                    bzRegion, bzChunk = divmod(z + offset['z'], McaFile.sideLength)
                    
                    if (bxRegion, bzRegion) in b['map'] and b['map'][bxRegion,bzRegion][bxChunk][bzChunk] == True:
                        conflict = True
                        break
            if conflict:
                break
        else:
            print(f'[{datetime.datetime.now()}] No conflict for {offset}')
            break
        '''
        '''
        # Check all chunks inside the overlapping area
        conflict = False
        for zReg in range(overlap['z']['min']['region'], overlap['z']['max']['region'] + 1):
            for xReg in range(overlap['x']['min']['region'], overlap['x']['max']['region'] + 1):
                if (xReg, zReg) in a['map']:
                    
                    # Set conflict search domain
                    search = {
                        axis : {
                            'min' : 0,
                            'max' : McaFile.sideLength - 1
                        } for axis in a['pos']
                    }
                    
                    # Limit search if region is on the edge of the overlap
                    for coord in search['x']:
                        if xReg == overlap['x'][coord]['region']:
                            search['x'][coord] = overlap['x'][coord]['chunk']
                
                    for coord in search['z']:
                        if zReg == overlap['z'][coord]['region']:
                            search['z'][coord] = overlap['z'][coord]['chunk']
                    
                    region = a['map'][xReg, zReg]
                    for z, row in enumerate(region[search['z']['min'] : search['z']['max'] + 1]):
                        for x, chunkExists in enumerate(region[search['x']['min'] : search['x']['max'] + 1]):
                            if chunkExists:
                                # Coords start relative to search, relative to region
                                # Make them relative to the offset
                                bAbsX = x + search['x']['min'] + xReg * McaFile.sideLength - offset['x']
                                bAbsZ = z + search['z']['min'] + zReg * McaFile.sideLength - offset['z']
                                
                                # Convert to chunk and region coords inside b['new']
                                bChunkX, bRegX = divmod(bAbsX, McaFile.sideLength)
                                bChunkZ, bRegZ = divmod(bAbsZ, McaFile.sideLength)
                                
                                if (bRegX, bRegZ) in b['map'] and b['map'][bRegX, bRegZ][bChunkX][bChunkZ] == True:
                                    conflict = True
                                    break
                            if conflict:
                                break
                        if conflict:
                            break
                if conflict:
                    break
            if conflict:
                break
        else:
            print(f'No conflict for offset {offset}')
            return'''
        '''
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
        print(f'[{datetime.datetime.now()}] Fusing these maps is impossible, sorry')'''

'''{'xMin': -256, 'zMin': -320, 'xLen': 512, 'zLen': 864}'''