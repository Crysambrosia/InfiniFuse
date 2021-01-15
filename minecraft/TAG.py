from abc import ABC, abstractmethod
from .compression import compress, decompress
import collections.abc
import functools
import operator
import re
import struct
import util

#-------------------------------------------- Functions --------------------------------------------

def from_snbt(snbt : str, pos : int = 0):
        """Create a TAG from SNBT when type is unknown"""
        if snbt[pos] == '{':
            return Compound.from_snbt(snbt)
        elif smnt[pos] == '[':
            for i in Array.subtypes:
                pass
        return value, pos

#-------------------------------------- Abstract Base Classes --------------------------------------

class Base(ABC):
    """Abstract Base Class of all tag types"""
    
    ID = NotImplemented
    """ID of this Tag"""

    @classmethod
    @abstractmethod
    def from_bytes(cls, iterable):
        """Create a tag from an iterable of NBT data bytes"""
        pass
    '''
    @classmethod
    @abstractmethod
    def from_snbt(cls, snbt):
        """Create a tag from a SNBT formatted string
        Return a (value, pos) tuple, where :
        - <value> is the created tag
        - <pos> is the character index following this tag's snbt
        """
        pass
    '''
    @classmethod
    def check_snbt(cls, snbt):
        """Check if provided SNBT is valid"""
        if not re.compile(cls.regex).fullmatch(snbt):
            raise ValueError(f'Invalid SNBT \'{snbt}\' for {cls}')

    @abstractmethod
    def to_bytes(self):
        """Return NBT data bytearray from self"""
        pass

    @abstractmethod
    def to_snbt(self):
        """Return a SNBT representation of this tag"""
        pass

    @classmethod
    @property
    def subtypes(cls):
        return sorted(
            [i for i in util.all_subclasses(cls) if i.ID is not NotImplemented],
            key = lambda i : i.ID
        )
    
    @abstractmethod
    def valueType(value):
        """Convert value to the same type as this tag's .value"""
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
    
    def __repr__(self):
        return self.to_snbt()

class Value(Base):
    """Abstract Base Class for all simple value tag types"""

    def __init__(self, value = None):
        value = 0 if value is None else value
        self.value = value

    def bit_length(self):
        """Returns the BIT length of this tag's value after encoding"""
        return len(self._value) * 8

    def to_bytes(self):
        return self._value
    
util.make_wrappers(Value, coercedMethods = ['__add__', '__mod__', '__rmod__', '__mul__', '__rmul__'])

class Number(Value):
    """Abstract Base Class for numerical tag types

    Assignments to .value are automatically encoded and boundary checked
    """

    fmt = NotImplemented
    """Struct format string for packing and unpacking"""
    
    suffix = NotImplemented
    """SNBT value suffix"""
    
    @classmethod
    def from_bytes(cls, iterable):
        byteValue = util.read_bytes(iterable, n = len(cls()))
        return cls( struct.unpack(cls.fmt, byteValue)[0] )
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
        
        value = ''
        
        for i, char in enumerate(snbt[pos:]):
            if char.isdigit() or char == '.':
                value += char
                continue
            elif char in cls.suffixes:
                break
            elif '' in cls.suffixes:
                i -= 1
                break
            else:
                raise ValueError(f'Missing suffix for {cls} at {pos+i+1} (expected {" or ".join(cls.suffixes)})')
        else:
            if '' not in cls.suffixes and snbt[pos:] != '':
                raise ValueError(f'Missing suffix for {cls} at {pos+i+1} (expected {" or ".join(cls.suffixes)})')
        
        try:
            return cls(value), pos+i+1
        except ValueError:
            raise ValueError(f'Invalid value for {cls} at {pos} !')
    
    def to_snbt(self):
        return f'{self.value}{self.suffixes[0]}'

    @property
    def value(self):
        return struct.unpack(self.fmt, self._value)[0]

    @value.setter
    def value(self, newValue):
        self._value = struct.pack(self.fmt, self.valueType(newValue))

    def __len__(self):
        """Returns the BYTE length of this tag's value after encoding"""
        return len(self._value)
    
util.make_wrappers( Number, 
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

class Integer(Number):
    """Abstract Base Class for integer numerical tag types"""
    
    valueType = int
    
    @property
    def unsigned(self):
        """The unsigned equivalent of this tag's value"""
        return struct.unpack(self.fmt.upper(), self._value)[0]
    
    @unsigned.setter
    def unsigned(self):
        self._value = struct.pack(self.fmt.upper(), self.valueType(newValue))

util.make_wrappers( Integer,
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

class Decimal(Number):
    """Abstract Base Class for decimal numerical tag types"""
    
    valueType = float
    
    @classmethod
    def fromhex(cls, string):
        return cls( float.fromhex(string) )

util.make_wrappers(Decimal, nonCoercedMethods=['hex','is_integer'])

class Sequence(Base, collections.abc.Sequence):
    """Abstract Base Class for sequence tag types"""
    pass

util.make_wrappers(Sequence, nonCoercedMethods = ['__getitem__', '__iter__', '__len__'])

class MutableSequence(Sequence, collections.abc.MutableSequence):
    """Abstract Base Class for Mutable collections.abc.Sequence tag types"""
    
    valueType = list
    
    def __init__(self, value = None):
        """Checks that all elements are type compatible through self.append"""
        value = [] if value is None else value
        self.value = []
        
        for i in value:
            self.append(i)

    def append(self, value):
        self.value.append(self.elementType(value))

    @staticmethod
    def decode_bytes(iterable, elementType):
        """Convert bytes -> sequence of values of elementType"""
        iterator = iter(iterable)
        length = Int.from_bytes(iterator)
        
        return [elementType.from_bytes(iterator) for _ in range(length)]
    
    @staticmethod
    def decode_snbt(snbt, elementType):
        """Convert snbt -> collections.abc.Sequence of values of elementType"""
        return [elementType(i) for i in snbt.strip('[]').split(',')]

    @property
    def elementID(self):
        return self.elementType.ID

    def insert(self, key, value):
        self.value = self[:key] + [value] + self[key:]
    
    def sort(self, *, key=None, reverse=False):
        self.value.sort(key=key, reverse=reverse)
    
    def to_bytes(self):
        encoded = Int(len(self)).to_bytes()
        
        for element in self:
            encoded += element.to_bytes()
            if isinstance(element, Compound):
                encoded += End().to_bytes()
    
        return encoded
    
    def to_snbt(self):
        return f'[{self.prefix}{",".join( [repr(i) for i in self.value] )}]'
    
    def __add__(self, other):
        return type(self)( self.value + [self.elementType(i) for i in other] )

    def __delitem__(self, key):
        del self.value[key]


    def __setitem__(self, key, value):
        """Replace self[key] with value.
        
        Value must be able to convert to self.elementType
        """
        self.value[key] = self.elementType(value)

util.make_wrappers( MutableSequence,
    coercedMethods = [
        'copy',
        '__mul__', 
        '__rmul__'
    ],
    nonCoercedMethods = [
        '__radd__'
    ]
)

class Array(MutableSequence):
    """Abstract Base Class for Array tag types"""
    
    prefix = NotImplemented
    """SNBT list Prefix"""
    
    @classmethod
    def from_bytes(cls, iterable):
        return cls( super().decode_bytes(iterable, cls.elementType) )
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
        
        try:
            assert snbt[pos] == '['
        except (AssertionError, IndexError):
            raise ValueError(f'Missing "[" at {pos}')
        
        try:
            assert snbt[pos+1:pos+3] == cls.prefix
        except (AssertionError, IndexError):
            raise ValueError(f'Missing prefix for {cls} at {pos+1}-{pos+2} (expected {cls.prefix})')
        
        pos += 3
        value = []
        
        try:
            if snbt[pos] != "]":
                while True:
                    itemValue, pos = cls.elementType.from_snbt(snbt, pos)
                    value.append(itemValue)
                    if snbt[pos] == ',':
                        pos += 1
                        continue
                    elif snbt[pos] == ']':
                        break
                    else:
                        raise ValueError(f'Missing "," or "]" at {pos}')
        except IndexError:
            raise ValueError(f'Missing "]" at {pos}')
        
        return cls(value), pos+1

    @classmethod
    @property
    def regex(cls):
        prefix = cls.prefix
        elem = cls.elementType.regex
        return f'\\[{prefix}({elem})?(?(1)(,{elem})*)\\]'

#---------------------------------------- Concrete Classes -----------------------------------------

class End(Base):
    """You probably don't want to use this.
    
    Ends a Compound, expect erratic behavior if inserted inside one.
    """
    ID = 0
    valueType = None
    
    def __init__(self, value = None):
        pass
    
    @classmethod
    def from_bytes(cls, value):
        return cls(value)
    
    def to_bytes(self):
        return b'\x00'
    
    def to_snbt(self):
        return ''

class Byte(Integer):
    """Int8 tag (0 to 255)"""
    ID = 1
    fmt = '>b'
    suffixes = ['b','B']

class Short(Integer):
    """Int16 tag (-32,768 to 32,767)"""
    ID = 2
    fmt = '>h'
    suffixes = ['s','S']
  
class Int(Integer):
    """Int32 tag (-2,147,483,648 to 2,147,483,647)"""
    ID = 3
    fmt = '>i'
    suffixes = ['']

class Long(Integer):
    """Int64 tag (-9,223,372,036,854,775,808 to 9,223,372,036,854,775,807)"""
    ID = 4
    fmt = '>q'
    suffixes = ['L','l']
 
class Float(Decimal):
    """Single precision float tag (32 bits)"""
    ID = 5
    fmt = '>f'
    suffixes = ['f','F']

class Double(Decimal):
    """Double precision float tag (64 bits)"""
    ID = 6
    fmt = '>d'
    suffixes = ['d','D','']

class Byte_Array(Array):
    """A Byte array
    
    Contained tags have no name
    """
    ID = 7
    elementType = Byte
    prefix = 'B;'
    
class String(Value, Sequence):
    """Unicode string tag
    
    Payload : a Short for length, then a <length> bytes long UTF-8 string
    """
    ID = 8
    regex = r"""(['"])((?!\1)[^\\]|\\.)*\1"""
    valueType = str

    @classmethod
    def from_bytes(cls, iterable):
        iterator = iter(iterable)
        byteLength = Short.from_bytes(iterator)
        byteValue = util.read_bytes(iterator, n = byteLength)
        return cls( byteValue.decode(encoding='utf-8') )
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
        pass
    
    def isidentifier(self):
        return False
    
    def join(self, iterable):
        iterable = [i if isinstance(i, str) else str(i) for i in iterable]
        return self.__class__( self.value.join(iterable) )

    def partition(self, sep):
        """Partition the String into three parts using the given separator.
    
        This will search for the separator in the String.  If the separator is found,
        returns a 3-tuple containing the part before the separator, the separator
        itself, and the part after it.
            
        If the separator is not found, returns a 3-tuple containing the original String
        and two empty TAG.String.
        """
        return tuple( [self.__class__(i) for i in self.value.partition(sep)] )

    def rpartition(self, sep):
        return tuple( [self.__class__(i) for i in self.value.rpartition(sep)] )

    def rsplit(self, sep=None, maxsplit=-1):
        return [self.__class__(i) for i in self.value.rsplit(sep, maxsplit)]
    
    def split(self, sep=None, maxsplit=-1):
        return [self.__class__(i) for i in self.value.split(sep, maxsplit)]

    def splitlines(self, keepends=False):
        return [self.__class__(i) for i in self.value.splitlines(keepends)]
    
    def to_snbt(self):
        snbt = '"'
        
        # Escape double quotes
        for character in self.value:
            if character == '"':
                snbt += '\\"'
            else:
                snbt += character

        snbt += '"'
        return snbt

    @property
    def value(self):
        return self._value[2:].decode(encoding='utf-8')

    @value.setter
    def value(self, newValue):
        newValue = str.encode( self.valueType(newValue) )
        self._value = Short(len(newValue)).to_bytes() + newValue
   
    def __str__(self):
        return self.value

util.make_wrappers( String,
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

class List(MutableSequence):
    """A list of tags, all of type self.elementType
    
    Type checks any additions unless it is empty
    If empty, self.elementType will be End
    """

    ID = 9
    prefix = ''

    def append(self, value):
        """Append to the list, perform type checking unless it is empty"""
        if self.elementType == End and isinstance(value, Base):
            self.value.append(value)
        elif self.elementType != End:
            super().append(value)
        else:
            raise ValueError('Can only append TAGs to empty List')

    @property
    def elementType(self):
        if len(self) > 0:
            return type(self[0])
        else:
            return End

    @classmethod
    def from_bytes(cls, iterable):
        iterator = iter(iterable)
        elementType = Base.subtypes[ Byte.from_bytes(iterator) ]
        return cls( super().decode_bytes(iterator, elementType) )
    
    @classmethod
    @property
    def regex(cls):
        pass
    
    def to_bytes(self):
        return Byte(self.elementID).to_bytes() + super().to_bytes()
    
class Compound(Base, collections.abc.MutableMapping):
    """A Tag dictionary, containing other names tags of any type."""
    ID = 10
    regex = r'{([^,:]*:[^,:]*)?(?(1)(,[^,:]*:[^,:]*)*)}'
    valueType = dict

    def __init__(self, value=None):
        value = {} if value is None else value
        for i in value:
            if not isinstance(value[i], Base):
                raise ValueError(f'TAG.Compound can only contain other TAGs')
        self.value = value
    
    @classmethod
    def from_bytes(cls, iterable):
        iterator = iter(iterable)
        value = {}
        
        while True:
            try:
                itemType = Base.subtypes[ Byte.from_bytes(iterator) ]
            except StopIteration:
                break
            
            if itemType == End:
                break

            itemName = String.from_bytes(iterator).value
            itemValue = itemType.from_bytes(iterator)
            value[itemName] = itemValue
        
        return cls(value)
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
        
        try:
            assert snbt[pos] == '{'
        except (AssertionError, IndexError):
            raise ValueError(f'Missing "{{" at {pos}!')
    
        itemName = ''
        value = {}
        
        try:
            while True:
                pos += 1
                if snbt[pos] != ':':
                    itemName += snbt[pos]
                else:
                    value[itemName], pos = from_snbt(snbt, pos+1)
                    if snbt[pos] == ',':
                        itemName = ''
                        continue
                    elif snbt[pos] == '}':
                        break
                    else:
                        raise ValueError(f'Missing "," or "}}" at {pos} !')
        except IndexError:
            raise ValueError(f'Missing value for item "{itemName}" at {pos-len(itemName)}')
        
        return cls(value), pos+1

    def to_bytes(self):
        encoded = bytearray()
        
        for element in self:
        
            encoded += Byte( self[element].ID ).to_bytes()
            encoded += String(element).to_bytes()
            encoded += self[element].to_bytes()
            
            if isinstance(self[element], Compound):
                encoded += End().to_bytes()
            
        return encoded

    def to_snbt(self):
        return f'{{{",".join( [f"{key}:{self[key].to_snbt()}" for key in self] )}}}'
    
    def __setitem__(self, key, value):
        """Replace self[key] with value.
        
        Value must type-compatible with self[key]
        """
        try:
            if isinstance(self[key], List) and len(self[key]) > 0:
                value = [self[key].elementType(i) for i in value]
            value = type(self[key])(value)
        except KeyError:
            pass
    
        self.value[key] = value
    
util.make_wrappers( Compound,
    nonCoercedMethods = ['__delitem__', '__getitem__', '__iter__', '__len__']
)

class Int_Array(Array):
    """A Int array
    
    Contained tags have no name
    """
    ID = 11
    elementType = Int
    prefix = 'I;'
    
class Long_Array(Array):
    """A Long array
    
    Contained tags have no name
    """
    ID = 12
    elementType = Long
    prefix = 'L;'