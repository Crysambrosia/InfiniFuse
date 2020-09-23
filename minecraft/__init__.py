import gzip
import mmap
import os
import struct
import time
import zlib

from .chunk import Chunk, openChunk
from .nbt import NBT
from .opendat import openDAT
from .openmca import openMCA

#TEST CODE
#test = NBT.decode(b'\x0a\x00\x00\x01\x00\x01\x41\x01\x01\x00\x01\x42\x02\x00')
#level = openDat('world/level.dat')