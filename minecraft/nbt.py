from abc import ABC, abstractmethod
from collections.abc import MutableMapping, MutableSequence, Sequence
import functools
import struct

def make_wrappers(cls, coercedMethods=[], nonCoercedMethods=[]):
    """Make wrapper methods for the given class
    
    coercedMethods    : return TAG of same type
    nonCoercedMethods : return something else
    
    A lot of methods acting on tags merely redirect the call to self.value
    example : TAG_Int.__add__(n) is the same as TAG_Int.value.__add__(n)
    This functions creates these methods from a list, instead of explicitly doing so
    This reduces the likeliness of errors greatly, and should make code easier to understand
    """
    for method in coercedMethods:
        def wrapper(self, *args, _method=method, **kwargs):
            return type(self)( getattr(self.value, _method)(*args, **kwargs) )
        setattr(cls, method, wrapper)

    for method in nonCoercedMethods:
        def wrapper(self, *args, _method=method, **kwargs):
            return getattr(self.value, _method)(*args, **kwargs)
        setattr(cls, method, wrapper)
    
    # This makes sure ABC doesn't refuse instanciation
    cls.__abstractmethods__ = cls.__abstractmethods__.difference(coercedMethods, nonCoercedMethods)
    
def read_bytes(iterable, byteLength):

    iterator = iter(iterable)
    value = bytearray()
    
    for i in range(byteLength):
        
        nextByte = next(iterator)
        
        if isinstance(nextByte, int):
            value.append(nextByte)
        elif isinstance(nextByte, bytes):
            value += next(iterator)
    
    return value

#-------------------------------------- Abstract Base Classes --------------------------------------

class TAG(ABC):
    """Abstract Base Class of all tag types"""
    
    ID = NotImplemented
    """TAG_ID of this Tag"""

    @classmethod
    @abstractmethod
    def from_bytes(cls, iterable):
        """Create a tag from an iterable of bytes"""
        pass

    @abstractmethod
    def to_bytes(self):
        """Return bytearray from self"""
        pass

    @abstractmethod
    def valueType(value):
        """Convert any variable -> tag value"""
        pass

    def __eq__(self, other):
        return self.value.__eq__(self.valueType(other))
    
    def __ge__(self, other):
        return self.value.__ge__(self.valueType(other))
    
    def __gt__(self, other):
        return self.value.__gt__(self.valueType(other))
    
    def __le__(self, other):
        return self.value.__le__(self.valueType(other))
    
    def __lt__(self, other):
        return self.value.__lt__(self.valueType(other))

class TAG_Value(TAG):
    """Abstract Base Class for all simple value tag types"""

    def __init__(self, value = None):
        value = 0 if value is None else value
        self.value = value

    def bit_length(self):
        return len(self._value) * 8

    def to_bytes(self):
        """Return bytearray from self"""
        return self._value
    
make_wrappers(TAG_Value, coercedMethods = ['__add__', '__mod__', '__rmod__', '__mul__', '__rmul__'])

class TAG_Number(TAG_Value):
    """Abstract Base Class for numerical tag types

    Assignments to .value are automatically boundary checked
    """

    fmt = NotImplemented
    """Struct format string for encoding and decoding"""
    
    snbt = NotImplemented
    """SNBT value identifier"""
    
    @classmethod
    def from_bytes(cls, iterable):
        """Create a tag from an iterable of bytes"""
        byteValue = read_bytes(iterable, byteLength = len(cls()))
        return cls( struct.unpack(cls.fmt, byteValue)[0] )

    @property
    def value(self):
        return struct.unpack(self.fmt, self._value)[0]

    @value.setter
    def value(self, newValue):
        self._value = struct.pack(self.fmt, self.valueType(newValue))

    def __len__(self):
        """Return byte length of encoded value"""
        return len(self._value)

    def __repr__(self):
        """Return SNBT formatted tag"""
        return f'{self.value}{self.snbt}'
    
make_wrappers( TAG_Number, 
    coercedMethods = [
        'conjugate',
        'imag',
        'real',
        '__abs__',
        '__ceil__',
        '__floor__',
        '__floordiv__',
        '__neg__',
        '__pos__',
        '__pow__',
        '__round__',
        '__sub__',
        '__truediv__',
        '__trunc__'
    ],
    nonCoercedMethods = [
        'as_integer_ratio',
        '__bool__',
        '__divmod__',
        '__float__',
        '__int__',
        '__radd__',
        '__rdivmod__',
        '__rfloordiv__',
        '__rpow__',
        '__rsub__',
        '__rtruediv__',
        '__str__'
    ]
)

class TAG_Integer(TAG_Number):
    """Abstract Base Class for integer numerical tag types
    
    Will containe method wrappers, but doesn't contain any explicit implementations
    Still needed for code clarity via inheritance
    """
    valueType = int

make_wrappers( TAG_Integer,
    coercedMethods = [
        'denominator',
        'numerator',
        '__and__',
        '__invert__',
        '__lshift__',
        '__or__',
        '__rshift__',
        '__xor__'
    ],
    nonCoercedMethods = [
        '__rand__',
        '__index__',
        '__rlshift__',
        '__ror__',
        '__rrshift__',
        '__rxor__'
    ]
)

class TAG_Decimal(TAG_Number):
    """Abstract Base Class for decimal numerical tag types"""
    
    valuetype = float
    
    @classmethod
    def fromhex(cls, string):
        return cls( float.fromhex(string) )

make_wrappers(TAG_Decimal, nonCoercedMethods=['hex','is_integer'])

class TAG_Sequence(TAG, Sequence):
    """Abstract Base Class for sequence tag types"""
    pass

make_wrappers(TAG_Sequence, nonCoercedMethods = ['__getitem__', '__iter__', '__len__'])

class TAG_MutableSequence(TAG_Sequence, MutableSequence):
    """Abstract Base Class for Mutable Sequence tag types"""
    
    valueType = list
    
    def __init__(self, value = None):
        value = [] if value is None else value
        self.value = []
        
        for i in value:
            # Checks for type compatibility through self.append
            self.append(i)

    def append(self, value):
        self.value.append(self.elementType(value))

    @staticmethod
    def decode(iterable, elementType):
        """Convert bytes -> sequence for this TAG_ID"""
        iterator = iter(iterable)
        length = TAG_Int.from_bytes(iterator)
        
        value = [elementType.from_bytes(iterator) for _ in range(length)]
    
        return value

    @property
    def elementID(self):
        return self.elementType.ID

    def insert(self, key, value):
        self.value = self[:key] + [value] + self[key:]
    
    def sort(self, *, key=None, reverse=False):
        self.value.sort(key=key, reverse=reverse)
    
    def to_bytes(self):
        """Return bytearray from self"""
        encoded = TAG_Int(len(self)).to_bytes()
        
        for element in self:
            encoded += element.to_bytes()
    
        return encoded
    
    def __add__(self, other):
        return type(self)( self.value + [self.elementType(i) for i in other] )

    def __delitem__(self, key):
        del self.value[key]
    
    def __repr__(self):
        return f'[{self.snbt}{",".join( [repr(i) for i in self.value] )}]'

    def __setitem__(self, key, value):
        self.value[key] = self.elementType(value)

class TAG_Array(TAG_MutableSequence):
    """Abstract Base Class for Array tag types"""
    
    @classmethod
    def from_bytes(cls, iterable):
        """Create a tag from an iterable of bytes"""
        return cls( super().decode(iterable, cls.elementType) )

make_wrappers( TAG_MutableSequence,
    coercedMethods = [
        'copy',
        '__mul__', 
        '__rmul__'
    ],
    nonCoercedMethods = [
        '__radd__'
    ]
)

#---------------------------------------- Concrete Classes -----------------------------------------

class TAG_End(TAG):
    """You probably don't want to instanciate this. Ends a TAG_Compound."""
    ID = 0
    valueType = None
    
    def __init__(self, value = None):
        pass
    
    @staticmethod
    def from_bytes(value):
        return None
    
    def to_bytes(self):
        return b'\x00'

class TAG_Byte(TAG_Integer):
    """UInt8 tag (0 to 255)"""
    ID = 1
    fmt = 'B'
    snbt = 'b'

class TAG_Short(TAG_Integer):
    """Int16 tag (-32,768 to 32,767)"""
    ID = 2
    fmt = '>h'
    snbt = 's'
  
class TAG_Int(TAG_Integer):
    """Int32 tag (-2,147,483,648 to 2,147,483,647)"""
    ID = 3
    fmt = '>i'
    snbt = ''

class TAG_Long(TAG_Integer):
    """Int64 tag (-9,223,372,036,854,775,808 to 9,223,372,036,854,775,807)"""
    ID = 4
    fmt = '>q'
    snbt = 'L'
 
class TAG_Float(TAG_Decimal):
    """Single precision float tag (32 bits)"""
    IDD = 5
    fmt = '>f'
    snbt = 'f'

class TAG_Double(TAG_Decimal):
    """Double precision float tag (64 bits)"""
    ID = 6
    fmt = '>d'
    snbt = 'd'

class TAG_Byte_Array(TAG_Array):
    """A TAG_Byte array"""
    ID = 7
    elementType = TAG_Byte
    snbt = 'B;'
    
class TAG_String(TAG_Value, TAG_Sequence):
    """Unicode string tag
    
    Payload : a Short for length, then a length bytes long UTF-8 string
    """
    ID = 8
    valueType = str

    @classmethod
    def from_bytes(cls, iterable):
        """Return decoded str"""
        iterator = iter(iterable)
        byteLength = TAG_Short.from_bytes(iterator)
        byteValue = read_bytes(iterator, byteLength)
        return cls( byteValue.decode(encoding='utf-8') )
    
    def isidentifier(self):
        return False
    
    def join(self, iterable):
        iterable = [i if isinstance(i, str) else str(i) for i in iterable]
        return self.__class__( self.value.join(iterable) )

    def partition(self, sep):
        return tuple( [self.__class__(i) for i in self.value.partition(sep)] )

    def rpartition(self, sep):
        return tuple( [self.__class__(i) for i in self.value.rpartition(sep)] )

    def rsplit(self, sep=None, maxsplit=-1):
        return [self.__class__(i) for i in self.value.rsplit(sep, maxsplit)]
    
    def split(self, sep=None, maxsplit=-1):
        return [self.__class__(i) for i in self.value.split(sep, maxsplit)]

    def splitlines(self, keepends=False):
        return [self.__class__(i) for i in self.value.splitlines(keepends)]

    @property
    def value(self):
        return self._value[2:].decode(encoding='utf-8')

    @value.setter
    def value(self, newValue):
        newValue = str.encode( self.valueType(newValue) )
        self._value = TAG_Short(len(newValue)).to_bytes() + newValue

    def __repr__(self):
        """Return SNBT formatted string"""
        snbt = '"'
        
        # Escape double quotes
        for character in self.value:
            if character == '"':
                snbt += '\"'
            else:
                snbt += character

        snbt += '"'
        return snbt
    
    def __str__(self):
        return self.value

make_wrappers( TAG_String,
    coercedMethods = [
        'capitalize',
        'casefold',
        'center',
        'expandtabs',
        'format',
        'format_map',
        'lstrip',
        'ljust',
        'lower',
        'replace',
        'rjust',
        'rstrip',
        'strip',
        'swapcase',
        'title',
        'translate',
        'upper',
        'zfill'
    ],
    nonCoercedMethods = [
        'endswith',
        'find',
        'isalnum',
        'isalpha',
        'isascii',
        'isdecimal',
        'isdigit',
        'islower',
        'isnumeric',
        'isprintable',
        'isspace',
        'istitle',
        'isupper',
        'maketrans',
        'rfind',
        'rindex',
        'startswith'
    ]
)

class TAG_List(TAG_MutableSequence):
    ID = 9
    snbt = ''
    
    def append(self, value):
        if self.elementType == TAG_End and isinstance(value, TAG):
            self.value.append(value)
        elif self.elementType != TAG_End:
            super().append(value)
        else:
            raise ValueError('Can only append TAGs to empty TAG_List')

    @property
    def elementType(self):
        if len(self) > 0:
            return type(self[0])
        else:
            return TAG_End

    @classmethod
    def from_bytes(cls, iterable):
        """Create TAG_List from an iterable of bytes"""
        iterator = iter(iterable)
        elementType = TAG_ID( TAG_Byte.from_bytes(iterator) )
        return cls( super().decode(iterator, elementType) )
    
    def to_bytes(self):
        """Return this tag as a bytearray"""
        return TAG_Byte(self[0].ID).to_bytes() + super().to_bytes()
    
class TAG_Compound(TAG, MutableMapping):
    """A MutableMapping subclass with NBT specific functionality"""
    ID = 10
    valueType = dict

    def __init__(self, value=None):
        value = {} if value is None else value
        self.value = value

    def __repr__(self):
        return f'{{{",".join( [f"{key}:{repr(self[key])}" for key in self] )}}}'
    
    @classmethod
    def from_bytes(cls, iterable):
        """Create a TAG_Compound from an iterable of bytes"""
        iterator = iter(iterable)
        value = {}
        
        while True:
            itemType = TAG_ID(TAG_Byte.from_bytes(iterator))
            if itemType == TAG_End:
                break
            
            itemName = TAG_String.from_bytes(iterator).value
            itemValue = itemType.from_bytes(iterator)
            value[itemName] = itemValue
        
        return cls(value)

    def to_bytes(self):
        encoded = bytearray()
        for element in self:
            # Recursively encode ID, Name, Payload
            encoded += TAG_Byte( self[element].ID ).to_bytes()
            encoded += TAG_String(element).to_bytes()
            encoded += self[element].to_bytes()
        encoded += TAG_End().to_bytes()
        return encoded
    
make_wrappers( TAG_Compound,
    nonCoercedMethods = ['__delitem__', '__getitem__', '__iter__', '__len__', '__setitem__']
)

class TAG_Int_Array(TAG_Array):
    ID = 11
    elementType = TAG_Int
    snbt = 'I;'
    
class TAG_Long_Array(TAG_Array):
    ID = 12
    elementType = TAG_Long
    snbt = 'L;'

# Look up table to get types from ID number
def TAG_ID(value):
    return [
        TAG_End,        #0
        TAG_Byte,       #1
        TAG_Short,      #2
        TAG_Int,        #3
        TAG_Long,       #4
        TAG_Float,      #5
        TAG_Double,     #6
        TAG_Byte_Array, #7
        TAG_String,     #8
        TAG_List,       #9
        TAG_Compound,   #10
        TAG_Int_Array,  #11
        TAG_Long_Array  #12
    ][value]