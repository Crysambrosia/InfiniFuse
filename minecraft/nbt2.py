from abc import ABC, abstractmethod
from collections.abc import MutableMapping, MutableSequence, Sequence
import functools
import gzip
import math
import struct
import zlib

class TAG_Abstract():
    """Abstract Base Class of all tag types"""
    
    def __getattr__(self, name):
        try:
            return getattr(self.value, name)
        except AttributeError:
            raise AttributeError(f'{self.__class__} object has no attribute {name}')

class TAG_AbstractValue(TAG_Abstract):
    """Abstract Base Class for all simple value tag types"""
    
    ID = NotImplemented
    """TAG_ID of this Tag"""
    
    @property
    def value(self):
        return self.decode(self._value)

    @value.setter
    def value(self, newValue):
        self._value = self.encode( self.valueType(newValue) )

    @staticmethod
    @abstractmethod
    def valueType(n):
        pass

    def __init__(self, value = 0):
        self.value = value

    def __add__(self, other):
        return self.__class__(self.value + other)

    def __eq__(self, other):
        return self.value == other

    def __ge__(self, other):
        return self.value >= other

    def __gt__(self, other):
        return self.value > other

    def __le__(self, other):
        return self.value <= other

    def __lt__(self, other):
        return self.value < other

    def __mod__(self, other):
        return self.__class__(self.value % other)

    def __rmod__(self, other):
        return other % self.value

    def __mul__(self, other):
        return self.__class__(self.value * other)

    def __rmul__(self, other):
        return other * self.value

class TAG_AbstractNumber(TAG_AbstractValue):
    """Abstract Base Class for numerical tag types

    Assignments to .value are automatically boundary checked"""

    fmt = NotImplemented
    """Format string for encoding and decoding"""
    
    snbt = NotImplemented
    """SNBT value identifier"""


    @classmethod
    def decode(cls, value):
        """Convert bytes -> value for this TAG_ID"""
        return struct.unpack(cls.fmt, value)[0]
    
    @classmethod
    def encode(cls, value):
        """Convert value for this TAG_ID -> bytes"""
        return struct.pack(cls.fmt, value)
    
    def __abs__(self):
        return self.__class__( abs(self.value) )

    def __radd__(self, other):
        return other + self.value

    def __ceil__(self):
        return self.__class__( math.ceil(self.value) )
    
    def __divmod__(self, other):
        return(self // other, self % other)

    def __rdivmod__(self, other):
        return(other // self, other % self)

    def __floor__(self):
        return self.__class__( math.floor(self.value) )

    def __floordiv__(self, other):
        return self.__class__(self.value // other)

    def __rfloordiv__(self, other):
        return other // self.value

    def __len__(self):
        """Return byte length of encoded value"""
        return len(self._value)

    def __neg__(self):
        return self.__class__(-self.value)

    def __pos__(self):
        return self.__class__(+self.value)

    def __pow__(self, other):
        return self.__class__(self.value ** other)

    def __rpow__(self, other):
        return other ** self.value

    def __repr__(self):
        """Return SNBT formatted tag"""
        return f'{self.value}{self.snbt}'

    def __round__(self, ndigits=None):
        return self.__class__( round(self.value, ndigits) )

    def __sub__(self, other):
        return self.__class__(self.value - other)

    def __rsub__(self, other):
        return other - self.value

    def __truediv__(self, other):
        return self.__class__(self.value / other)

    def __rtruediv__(self, other):
        return other / self.value

    def __trunc__(self):
        return self.__class__( math.trunc(self.value) )
    
class TAG_AbstractInteger(TAG_AbstractNumber):
    """Abstract Base Class for integer tag types"""

    def __and__(self, other):
        return self.__class__(self.value & other)

    def __rand__(self, other):
        return other & self.value

    def __index__(self):
        return self.value.__index__()

    def __invert__(self):
        return self.__class__(~self.value)

    def __lshift__(self, other):
        return self.__class__(self.value << other)

    def __rlshift__(self, other):
        return other << self.value

    def __or__(self, other):
        return self.__class__(self.value | other)

    def __ror__(self, other):
        return other | self.value

    def __rshift__(self, other):
        return self.__class__(self.value >> other)

    def __rrshift__(self, other):
        return other >> self.value

    def __xor__(self, other):
        return self.__class__(self.value ^ other)

    def __rxor__(self, other):
        return other ^ self.value

class TAG_Byte(TAG_AbstractInteger):
    
    ID = 1
    fmt = 'B'
    snbt = 'b'
    valueType = int

class TAG_Short(TAG_AbstractInteger):
    
    ID = 2
    fmt = '>h'
    snbt = 's'
    valueType = int
  
class TAG_Int(TAG_AbstractInteger):
    
    ID = 3
    fmt = '>i'
    snbt = ''
    valueType = int

class TAG_Long(TAG_AbstractInteger):
    
    ID = 4
    fmt = '>q'
    snbt = 'L'
    valueType = int
 
class TAG_Float(TAG_AbstractNumber):

    ID = 5
    fmt = '>f'
    snbt = 'f'
    valueType = float

class TAG_Double(TAG_AbstractNumber):
    
    ID = 6
    fmt = '>d'
    snbt = 'd'
    valueType = float

class TAG_AbstractSequence(TAG_Abstract, Sequence):
    """Abstract Base Class for sequence tag types"""

    def __getitem__(self, key):
        return self.value[key]

    def __len__(self):
        return len(self.value)

class TAG_String(TAG_AbstractValue, TAG_AbstractSequence):
    """A NBT tag representing a unicode string
    
    Payload : a Short for length, then a length bytes long UTF-8 string
    """

    ID = 8
    valueType = str

    @staticmethod
    def decode(value):
        """Return decoded str, ignoring the length indicating bytes"""
        return value[2:].decode(encoding='utf-8')

    @staticmethod
    def encode(value):
        """Encode a str to bytes, adding first two bytes representing length"""
        value = str.encode(value)
        
        encoded = TAG_Short.encode(len(value))
        encoded += value
        
        return encoded

    def casefold(self):
        return self.__class__( self.value.casefold() )

    def format_map(self, mapping):
        return self.__class__( self.value.format_map(mapping) )

    def lstrip(self, *args):
        return self.__class__( self.value.lstrip(*args) )
    
    def ljust(self, *args):
        return self.__class__( self.value.ljust(*args) )

    def lower(self):
        return self.__class__( self.value.lower() )

    def rjust(self, *args):
        return self.__class__( self.value.rjust(*args) )

    def upper(self):
        return self.__class__( self.value.upper() )

    def __repr__(self):
        """Return SNBT formatted string"""
        snbt = '"'
        
        for character in self.value:
            if character == '"':
                snbt += '\"'
            else:
                snbt += character

        snbt += '"'
        return snbt

class TAG_Compound(MutableMapping):
    """A MutableMapping subclass with NBT specific functionality"""
    
    ID = 10

    def __init__(self, payload):
        self.payload = payload

    def __iter__(self):
        return iter(self.payload)

    def __delitem__(self, key):
        del self.payload[key]

    def __getitem__(self, key):
        return self.payload[key]
    
    def __setitem__(self, key, value):
        self.payload[key] = value

    def __len__(self):
        return len(self.payload)

    def __repr__(self):
        snbt = '{'
        # Recursive repr of contained tags
        for i, element in enumerate(self.payload):
            snbt += f'{element}:{self[element]}'
            if i < len(self) - 1:
                snbt += ','
        snbt += '}'
        return snbt

    def encode(value):
        encoded = bytearray()
        for element in value:
            # Recursively encode ID, Name, Payload
            encoded += TAG_Byte.encode(value[element].ID)
            encoded += TAG_String.encode(element)
            encoded += type(value[element]).encode(value[element].payload)
        encoded += (b'\x00')
        return encoded

class TAG_List(MutableSequence):
    ID = 9
    def __init__(self, payload = []):
        self.payload = payload
        
    
    def encode(value):
        encoded = bytearray()
        
        encoded += TAG_Byte.encode(value[0].ID)
        encoded += TAG_Int.encode(len(value))
        
        for element in value:
            encoded += type(element).encode(element)
            
        return encoded
  
class TAG_AbstractArray(TAG_AbstractSequence, MutableSequence):
    """Base class for all Array tag types
    Should NEVER be instanciated directly !
    """
    
    def __init__(self, value = []):
        self.value = value

    def __setitem__(self, key, value):
        if type(value) != self.elementID:
            value = self.elementID(value)
        self[key] = value
        
    def __delitem__(self, key):
        del self[key]

    def insert(self, key, value):
        self.value = self[:key] + [value] + self[key:]

    @classmethod
    def encode(cls, value):
        encoded = bytearray()
        
        encoded += TAG_Int.encode(len(value))
        
        for element in value:
            encoded += cls.elementID.encode(element)
            
        return encoded

class TAG_Byte_Array(TAG_AbstractArray):
    ID = 7
    elementID = TAG_Byte

class TAG_Int_Array(TAG_AbstractArray):
    ID = 11
    elementID = TAG_Int
    
class TAG_Long_Array(TAG_AbstractArray):
    ID = 12
    elementID = TAG_Long