import minecraft
import os

# Find offset for map
# Offset all chunks
# Change map IDs
# Offset map items
# Offset players
# Combine player stats
# Do something with player inventory ?

def main():

    base = minecraft.World.from_saves('Test')
    addition = minecraft.World.from_saves('Test2')
    
    offsetX = 0
    offsetZ = 0
    minX, minZ, maxX, maxZ = base.dimensions['minecraft:overworld'].borders()
    
    for radius in range(3_750_000): # Using the 'radius' of a square of course
        for offsetX in range(-radius, radius + 1):
            for offsetZ in range(-radius, radius + 1):
                if abs(offsetX) == radius or abs(offsetZ) == radius:
                    print(f'trying offsets {offsetX} {offsetZ}')
                    for x in range(minX, maxX):
                        for z in range(minZ, maxZ):
                            if (x, z) in addition.dimensions['minecraft:overworld'] and (x + offsetX, z + offsetZ) in base.dimensions['minecraft:overworld']:
                                print(f'Conflict at {x} {z}')
                                break
                        else:
                            continue
                        break
                    else:
                        print(f'No conflict with offsets {offsetX} {offsetZ} !')
                        break
            else:
                continue
            break
        else:
            continue
        break
    else:
        print(f'No possible offset (you probably waited MONTHS to read this, sorry)')
