import gzip
import mmap
import os
import struct
import time
import zlib

from .chunk import Chunk
from .nbt import *
from .old_datfile import DatFile