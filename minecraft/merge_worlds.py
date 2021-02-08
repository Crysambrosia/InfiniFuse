import os

# Find offset for map
# Offset all chunks
# Change map IDs
# Offset map items
# Offset players
# Combine player stats
# Do something with player inventory ?

def main():

    appdata = os.environ['APPDATA']
    saves = f'{appdata}\\.minecraft\\saves\\'
    
    for world in os.listdir(saves):
        worldFolder = os.path.join(saves, world)
        
