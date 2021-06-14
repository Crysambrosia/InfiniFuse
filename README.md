# InfiniFuse
Minecraft World Editor

InfiniFuse is a python package that can fuse two minecraft worlds together !

# Quick Start Up Guide :
- Install somewhere python can import it
- Grab the .minecraft/saves subfolder names of two worlds you want to fuse
- Type this in python :
```
>>> import InfiniFuse.minecraft
>>> InfiniFuse.minecraft.fuse(source = 'worldName', destination = 'otherWorldName')
```

This will move every chunk, map, and player from <source> to <destination> !
For now, it only moves the overworld and the nether

# Features :
- Fuse two worlds together !
- Offsets one of the maps if they overlap
- All Nether portals stay connected
- All Maps stay valid
- All Players move with the terrain

Also features completely custom NBT support.

For contributors, I suggest you get started in ```minecraft/merge_worlds.py```
Then you can look into the stuff you don't understand as you find it !
