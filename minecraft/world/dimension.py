from minecraft.chunk import Chunk
from minecraft.mcafile import McaFile
import concurrent.futures
import os
import util

class Dimension(util.Cache):
    """A dimension of a minecraft world"""
    
    __slots__ : ['_cache', 'folder']
    
    sideLength = 60_002_304
    """Maximum side length of a dimension in blocks
    Defined so that range(-sideLength, sideLength) includes every legal block coordinate
    """
    
    def __init__(self, folder : str):
    
        self.folder = folder
        """Folder containing this dimension's .mca files"""
    
        self._cache = {}
        """Cache containing loaded chunks"""
    
    def __contains__(self, key):
        """Returns whether chunk <key> exists in this dimension"""
        if isinstance(key, tuple) and len(key) == 2:
            x, z = key
            return McaFile.chunk_exists(folder = self.folder, x = x, z = z)
    
    def __delitem__(self, key):
        if len(key) == 2:
            x, z = key
            xRegion, xChunk = divmod(x, McaFile.sideLength)
            zRegion, zChunk = divmod(z, McaFile.sideLength)
            del util.Cache.__getitem__(self, key = (xRegion, zRegion))[xChunk, zChunk]
    
    def __getitem__(self, key):
        """Return a chunk from two coords, and a block from three"""
        if len(key) == 2:
            x, z = key
            xRegion, xChunk = divmod(x, McaFile.sideLength)
            zRegion, zChunk = divmod(z, McaFile.sideLength)
            return util.Cache.__getitem__(self, key = (xRegion, zRegion))[xChunk, zChunk]
            
        elif len(key) == 3:
            x, y, z = key
            chunkX, x = divmod(x, 16)
            chunkZ, z = divmod(z, 16)
            
            return self[chunkX, chunkZ][x, y, z]
    
    def __iter__(self):
        """A generator that extracts every existing chunk from this dimension"""
        for f in self.files():
            for chunk in f:
                if chunk is not None:
                    yield chunk
    
    def __len__(self):
        """Number of chunks contained in this dimension"""
        return sum([len(f) for f in self.files()])
    
    def __setitem__(self, key, value):
        
        if len(key) == 2:
            x, z = key
            xRegion, xChunk = divmod(x, McaFile.sideLength)
            zRegion, zChunk = divmod(z, McaFile.sideLength)
            util.Cache.__getitem__(self, key = (xRegion, zRegion))[xChunk, zChunk] = value
            
        elif len(key) == 3:
            x, y, z = key
            xChunk, x = divmod(x, 16)
            zChunk, z = divmod(z, 16)
            self[xChunk, zChunk][x, y, z] = value
    
    def binary_map(self):
        """Return a dict of the binary maps of all contained McaFiles, indexed by region coords"""
        binMap = {}
        for f in self.files():
            binMap[f.coords_region] = f.binary_map()
        return binMap
    
    def convert_key(self, key):
        """Convert <key> to a tuple of ints"""
        key = tuple([int(i) for i in key])
        return key
    
    def convert_value(self, value):
        """Make sure value is a McaFile"""
        if not isinstance(value, McaFile):
            raise TypeError(f'Value must be McaFile, not {value}')
        return value
    
    def files(self):
        """Generate a list of contained .mca files files"""
        if os.path.exists(self.folder):
            for f in os.listdir(self.folder):
                if os.path.splitext(f)[1] == '.mca':
                    yield McaFile.open(os.path.join(self.folder, f))
        else:
            return []
    
    def load_value(self, key):
        """Return McaFile at coords in key"""
        xRegion, zRegion = key
        return McaFile.open(path = os.path.join(self.folder, f'r.{xRegion}.{zRegion}.mca'))
    
    def png_map(self, size : int = 0, shade : int = 127):
        """Return a PNG map of chunk locations
        
        <limit> : The map will be the closest multiple of 32 to this in pixel side length
        <shade> : 0 - 255 shade of grey for existing pixels, defaults to 127
        """
        limit = size // 64
        regionPNGs = {}
        
        for z in range(-limit, limit):
            regionPNGs[z] = {}
            for x in range(-limit, limit):
                f = util.Cache.__getitem__(self, key = (x, z))
                regionPNGs[z][x] = util.PNG.from_iterable(f.binary_map(), shade = shade)
        
        data = bytearray()
        for z in regionPNGs:
            for line in range(McaFile.sideLength):
                data += b'\x00' # No filter
                for x in regionPNGs[z]:
                    data += regionPNGs[z][x].get_line(line)
        
        return util.PNG(
            data = data, 
            height = limit * 64, 
            width = limit * 64,
            bitdepth = 8,
            colortype = 0,
            interlaced = False
        )
    
    def save_all(self):
        """Save all McaFiles from cache"""
        with concurrent.futures.ProcessPoolExecutor() as e:
            # ProcessPool seems to be slightly faster than ThreadPool here
            for _ in e.map(McaFile.write, self._cache.values()):
                pass
        self.discard_all()
    
    def save_value(self, key, value):
        """Write <value> to McaFile at coords in <key>"""
        xRegion, zRegion = key
        value.path = os.path.join(self.folder, f'r.{xRegion}.{zRegion}.mca')
        value.write()