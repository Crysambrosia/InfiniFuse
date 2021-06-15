import logging
import zlib
import struct

def Int1(n):
    return struct.pack("!B", n & (2**8-1))
    
def Int4(n):
    return struct.pack("!I", n & (2**32-1))

class PNG():
    """A Portable Network Graphics file interface
    WIP : Do not use as-is ! This is not functional yet
    """
    
    maxSize = 2 ** 31
    """The maximum size of a png in one dimension"""
    
    def __init__( self, 
        width : int = 0,
        height : int = 0,
        bitdepth : int = 8,
        colortype : int = 0,
        interlaced : bool = False
    ):
        """Create a PNG object
    
        <width>     : number of pixels per line of the image
        <height>    : number of lines in the image
        <bitdepth>  : (see set_colortype)
        <colortype> : (see set_colortype)
        <interlaced>: True if the image is interlaced, defaults to False
        """
    
        self.width = width
        self.height = height
        self.set_colortype(colortype = colortype, bitdepth = bitdepth)
        self.compression = compression
        self.filtertype = filtertype
        self.interlaced = interlaced
    
    def get_scanline(self, y : int):
        """Return data of scanline <y>"""
        
    
    @classmethod
    @property
    def header(cls):
        """PNG File header, never changes"""
        return b'\x89' + 'PNG\r\n\x1A\n'.encode('ascii')
    
    @property
    def height(self):
        """Number of lines in the image"""
        return self._height
    
    @height.setter
    def height(self, value):
        if not 0 < value < self.maxSize:
            raise ValueError(f'Height must be 0 - {self.maxSize}')
        self._height = value
    
    @property
    def pixelSize(self):
        """Number of bits per pixel of this file"""
        if self.colortype in [0, 3]:
            # Grayscale / Palette
            return self.bitdepth
        elif self.colortype == 4:
            # Grayscale + Alpha
            return self.bitdepth * 2
        elif self.colortype == 2:
            # RGB
            return self.bitdepth * 3
        elif self.colortype == 6:
            #RGBA
            return self.bitdepth * 4
    
    @property
    def width(self):
        """Number of pixels per line of the image"""
        return self._width
    
    @width.setter
    def width(self, value):
        if not 0 < value < self.maxSize:
            raise ValueError(f'Width must be 0 - {self.maxSize}')
        self._width = value
    
    def IHDR(self):
        """Return header block of this image, contains basic information"""
        compression = 0 # zlib (no choice here)
        filtertype = 0  # adaptive (each scanline seperately, no choice either)
        
        IHDR =  Int4(self.width) + Int4(self.height)
        IHDR += Int1(self.bitdepth) + Int1(self.colortype)
        IHDR += Int1(compression) + Int1(filtertype) + Int1(interlaced)
        
        block = "IHDR".encode('ascii') + IHDR
        return Int4(len(IHDR)) + block + Int4(zlib.crc32(block))
    
    def set_colortype(self, colortype : int = 0, bitdepth : int = None):
        """Change color Type for this PNG image. Can corrupt image content !
        Valid values are :
        | Color |                      | Allowed        |
        | Type  | Explanation          | Bit Depths     |
        |-------|----------------------|----------------|
        |   0   | Grayscale            | 1, 2, 4, 8, 16 |
        |   2   | RGB                  | 8, 16          |
        |   3   | Palette (see .PLTE)  | 1, 2, 4, 8     |
        |   4   | Grayscale with Alpha | 8, 16          |
        |   6   | RGB with Alpha       | 8, 16          |
        """
        
        valid = {
            0 : [1, 2, 4, 8, 16],
            2 : [8, 16],
            3 : [1, 2, 4, 8],
            4 : [8, 16],
            6 : [8, 16]
        }
        
        if colortype not in valid:
            values = ", ".join([str(i) for i in valid])
            raise ValueError(f'colortype must be one of {values}')
        
        if bitdepth is None:
            bitdepth = valid[colortype][0]
        elif bitdepth not in valid[colortype]:
            values = ", ".join([str(i) for i in valid[colortype]])
            raise ValueError(f'bitdepth for colortype {colortype} must be one of {values}')
        
        self._colortype = colortype
        self._bitdepth  = bitdepth
    
    

def makePNG(data, height = 0, width = 0):
    """Returnn bytes of a greyscale PNG with <data> as IDAT"""

    def I1(value):
        return struct.pack("!B", value & (2**8-1))
    def I4(value):
        return struct.pack("!I", value & (2**32-1))
    
    # generate these chunks depending on image type
    makeIHDR = True
    makeIDAT = True
    makeIEND = True
    png = b"\x89" + "PNG\r\n\x1A\n".encode('ascii')
    if makeIHDR:
        colortype = 0 # true gray image (no palette)
        bitdepth = 8 # with one byte per pixel (0..255)
        compression = 0 # zlib (no choice here)
        filtertype = 0 # adaptive (each scanline seperately)
        interlaced = 0 # no
        IHDR = I4(width) + I4(height) + I1(bitdepth)
        IHDR += I1(colortype) + I1(compression)
        IHDR += I1(filtertype) + I1(interlaced)
        block = "IHDR".encode('ascii') + IHDR
        png += I4(len(IHDR)) + block + I4(zlib.crc32(block))
    if makeIDAT:
        compressor = zlib.compressobj()
        compressed = compressor.compress(data)
        compressed += compressor.flush() #!!
        block = "IDAT".encode('ascii') + compressed
        png += I4(len(compressed)) + block + I4(zlib.crc32(block))
    if makeIEND:
        block = "IEND".encode('ascii')
        png += I4(0) + block + I4(zlib.crc32(block))
    return png