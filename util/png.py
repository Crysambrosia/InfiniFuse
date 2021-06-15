from .binary import get_bits, set_bits
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
        data : bytearray = None,
        width : int = 1,
        height : int = 1,
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
        self.interlaced = interlaced
        
        if data is not None:
            self.data = data
        else:
            self.data = bytearray(self.lineByteLength * self.height)
    
    def content(self):
        """Return a bytearray of this PNG's content"""
        return self.header() + self.IHDR() + self.IDAT() + self.IEND()
    
    @staticmethod
    def encode_block(name : str, content : bytearray):
        """Return an encoded PNG block <name> containing <content>"""
        block = name.encode('ascii') + content
        return Int4(len(content)) + block + Int4(zlib.crc32(block))
    
    
    def find_line(self, y : int):
        """Return address info of scanline <y>
        
        Mainly used as part of get_line and set_line
        """
        if y not in range(self.height):
            raise ValueError(f'y must be 0 - {self.height - 1}')
        
        lineStart = y * self.lineByteLength
        lineEnd = lineStart + self.lineByteLength
        return lineStart, lineEnd
    
    def find_pixel(self, x : int, y : int):
        """Return address info for pixel at (<x>, <y>)
        
        Mainly used as part of get_pixel and set_pixel
        """
        if x not in range(self.width):
            raise ValueError(f'x must be 0 - {self.width - 1}')
        
        lineStart, _ = self.find_line(y)
        
        startByte, startBit = divmod(x * self.pixelBitLength, 8)
        startByte += lineStart + 1
        endByte = startByte + (self.pixelBitLength // 8) + 1
        endBit = startBit + self.pixelBitLength
        
        return startByte, endByte, startBit, endBit
    
    def get_line(self, y : int):
        """Return data of scanline <y>"""
        lineStart, lineEnd = self.find_line(y)
        return self.data[lineStart : lineEnd]
    
    def get_pixel(self, x : int, y : int):
        """Return data of pixel at (<x>, <y>)"""
        
        startByte, endByte, startBit, endBit = self.find_pixel(x, y)
        
        return get_bits(
            n = int.from_bytes(self.data[startByte:endByte], byteorder = 'little'), 
            start = startBit,
            end   = endBit
        )
    
    @staticmethod
    def header():
        """PNG File header, never changes"""
        return b'\x89' + 'PNG\r\n\x1A\n'.encode('ascii')
    
    @property
    def height(self):
        """Number of lines in the image"""
        return self._height
    
    @height.setter
    def height(self, value):
        if not 0 < value <= self.maxSize:
            raise ValueError(f'Height must be 0 - {self.maxSize}')
        self._height = value
    
    def IDAT(self):
        """Return data block of this image"""
        compressor = zlib.compressobj()
        content = compressor.compress(self.data)
        content += compressor.flush()
        return self.encode_block(name = 'IDAT', content = content)
    
    @staticmethod
    def IEND():
        """Return ending block. Always the same"""
        return PNG.encode_block(name = 'IEND', content = b'')

    def IHDR(self):
        """Return header block of this image, contains basic information"""
        compression = 0 # zlib (no choice here)
        filtertype = 0  # adaptive (each scanline seperately, no choice either)
        
        content =  Int4(self.width) + Int4(self.height)
        content += Int1(self.bitdepth) + Int1(self.colortype)
        content += Int1(compression) + Int1(filtertype) + Int1(self.interlaced)
        
        return self.encode_block(name = 'IHDR', content = content)

    @property
    def lineByteLength(self):
        """Return line length in bytes"""
        lineLength, remainder = divmod(8 + (self.pixelBitLength * self.width), 8)
        
        if remainder != 0:
            # Line breaks always happen on exact byte boundaries
            lineLength += 1
        
        return lineLength

    @property
    def pixelBitLength(self):
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
            # RGBA
            return self.bitdepth * 4

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
        
        self.colortype = colortype
        self.bitdepth  = bitdepth

    def set_line(self, y : int, value : bytearray):
        """Set line at <x> <y> to <value>"""
        lineStart, lineEnd = self.find_line(y)
        
        if len(value) != self.lineByteLength:
            raise ValueError(f'Lines must be exactly {self.lineByteLength} bytes long for this PNG !')
        
        self.data[lineStart:lineEnd] = value

    def set_pixel(self, x : int, y : int, value : int):
        """Set pixel at <x> <y> to <value>
        
        If <value> doesn't fit inside self.pixelBitLength bits, it will overflow !
        """
        startByte, endByte, startBit, endBit = self.find_pixel(x, y)
        
        self.data[startByte:endByte] = set_bits(
            n = int.from_bytes(self.data[startByte:endByte], byteorder = 'little'),
            start = startBit,
            end = endBit,
            value = value & ((2 ** self.pixelBitLength) - 1)
        ).to_bytes(length = endByte - startByte, byteorder = 'little')

    @property
    def width(self):
        """Number of pixels per line of the image"""
        return self._width
    
    @width.setter
    def width(self, value):
        if not 0 < value <= self.maxSize:
            raise ValueError(f'Width must be 0 - {self.maxSize}')
        self._width = value
    
def makePNG(data, height = 0, width = 0):
    """Returnn bytes of a greyscale PNG with <data> as IDAT"""
    
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
        IHDR = Int4(width) + Int4(height) + Int1(bitdepth)
        IHDR += Int1(colortype) + Int1(compression)
        IHDR += Int1(filtertype) + Int1(interlaced)
        block = "IHDR".encode('ascii') + IHDR
        png += Int4(len(IHDR)) + block + Int4(zlib.crc32(block))
    if makeIDAT:
        compressor = zlib.compressobj()
        compressed = compressor.compress(data)
        compressed += compressor.flush() #!!
        block = "IDAT".encode('ascii') + compressed
        png += Int4(len(compressed)) + block + Int4(zlib.crc32(block))
    if makeIEND:
        block = "IEND".encode('ascii')
        png += Int4(0) + block + Int4(zlib.crc32(block))
    return png