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
        #print(f'Starting tests at {pos}')
        for i in sorted(Base.subtypes, key = lambda i : i.snbtPriority):
            try:
                #print(f'Trying {i} at {pos}')
                value, pos =  i.from_snbt(snbt, pos)
            except ValueError:
                #print(f'Failed {i} at {pos}')
                continue
            else:
                #print(f'--- Success with {i} at {pos} ---')
                return value, pos
        #print(f'Everything failed at {pos}')
        raise ValueError(f'Invalid snbt at {pos}')

#-------------------------------------- Abstract Base Classes --------------------------------------

class Base(ABC):
    """Abstract Base Class of all tag types"""
    
    ID = None
    """ID of this Tag"""
    
    snbtPriority = None
    """Determines priority for from_snbt
    Lowest goes first
    """
    
    @property
    def bit_length(self):
        """Returns the BIT length of this tag's value after encoding"""
        return self.byte_length * 8
    
    @property
    def byte_length(self):
        return len(self.to_bytes())

    @classmethod
    @abstractmethod
    def decode(cls, iterable):
        """Decode a value from an iterable of byte NBT data"""
        pass

    @classmethod
    @abstractmethod
    def encode(cls, value):
        """Encode a value into byte NBT data"""
        pass

    @classmethod
    def from_bytes(cls, iterable):
        """Create a tag from an iterable of NBT data bytes"""
        return cls(cls.decode(iterable))
    
    @classmethod
    @abstractmethod
    def from_snbt(cls, snbt):
        """Create a new TAG from SNBT
        
        Return a (value, pos) tuple, where :
        - <value> is a tag created from SNBT
        - <pos> is the character index following this tag's snbt
        """
        pass

    def to_bytes(self):
        """Return NBT data bytearray from self"""
        return self.encode(self.value)

    @abstractmethod
    def to_snbt(self):
        """Return a SNBT representation of this tag"""
        pass

    @classmethod
    @property
    def subtypes(cls):
        return sorted(
            [i for i in util.all_subclasses(cls) if i.ID is not None],
            key = lambda i : i.ID
        )
    
    @abstractmethod
    def valueType(value):
        """Convert value to the same type as this tag's .value"""
        pass
    
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newValue):
        newValue = self.valueType(newValue)
        self.encode(newValue) #Raises an exception if newValue is incompatible
        self._value = newValue

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
    
    def __int__(self):
        return int(self.value)
    
    def __float__(self):
        return float(self.value)
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
        match = re.compile(cls.regex).match(snbt[pos:])
        try:
            return cls(match['value']), pos + match.end()
        except:
            raise ValueError(f'Invalid snbt for {cls} at {pos}')
    
util.make_wrappers(Value, coercedMethods = ['__add__', '__mod__', '__rmod__', '__mul__', '__rmul__'])

class Number(Value):
    """Abstract Base Class for numerical tag types

    Assignments to .value are automatically checked for compatibility
    """

    fmt = None
    """Struct format string for packing and unpacking"""
    
    suffixes = None
    """valid SNBT suffixes"""
    
    @classmethod
    def decode(cls, iterable):
        byteValue = util.read_bytes(iterable, n = len(cls()))
        return struct.unpack(cls.fmt, byteValue)[0]
    
    @classmethod
    def encode(cls, value : int = 0):
        return struct.pack(cls.fmt, cls.valueType(value))
    
    def to_snbt(self):
        return f'{self.value}' + ('' if self.suffixes is None else f'{self.suffixes[0]}')

    def __len__(self):
        """Returns the BYTE length of this tag's value after encoding"""
        return self.byte_length
    
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
        '__radd__',
        '__rdivmod__',
        '__rfloordiv__',
        '__rpow__',
        '__rsub__',
        '__rtruediv__'
    ]
)

class Integer(Number):
    """Abstract Base Class for integer numerical tag types"""
    
    valueType = int
    
    @classmethod
    @property
    def regex(cls):
        return f'(?P<value>(?P<negative>-)?\\d+){"" if cls.suffixes is None else f"(?P<suffix>[{cls.suffixes}])"}'
    
    @property
    def unsigned(self):
        """The unsigned equivalent of this tag's value"""
        return struct.unpack(self.fmt.upper(), self.to_bytes())[0]
    
    @unsigned.setter
    def unsigned(self):
        self._value = struct.pack(self.fmt.upper(), self.valueType(newValue))
        #WIP

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
    
    regex = r'(?P<value>(?P<negative>-)?(?P<integer>\d+)?(?P<dot>\.)?(?P<decimal>(?(integer)\d*|\d+)))'
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
    """Abstract Base Class for MutableSequence tag types"""
    
    prefix = None
    """SNBT list Prefix"""
    
    valueType = list
    
    def __init__(self, value = None):
        """Checks that all elements are type compatible through self.append"""
        value = [] if value is None else value
        self.value = []
        
        for i in value:
            self.append(i)

    def append(self, value):
        self.value.append(self.elementType(value))

    @classmethod
    def decode(cls, iterable):
        iterator = iter(iterable)
        
        elementType = cls.elementType
        if isinstance(elementType, property):
            elementType = Base.subtypes[ Byte.decode(iterator) ]

        length = Int.decode(iterator)
        return [elementType.from_bytes(iterator) for _ in range(length)]
    
    @staticmethod
    def encode(value = None):
        value = [] if value is None else value
        byteValue = Int.encode(len(value))
        
        for element in value:
            byteValue += element.to_bytes()
            if isinstance(element, Compound):
                byteValue += End.encode()
    
        return byteValue

    @property
    def elementID(self):
        return self.elementType.ID
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
    
        match = re.compile(f'\\[{cls.prefix}').match(snbt, pos)
        if match is None:
            raise ValueError(f'Missing "[{cls.prefix}" at {pos} for {cls}')
        
        pos = match.end()
        value = []
        
        
        if snbt[pos] != ']':
            
            if isinstance(cls.elementType, property):
                elementType = type(from_snbt(snbt, pos)[0])
            else:
                elementType = cls.elementType
            
            while True:
                itemValue, pos = elementType.from_snbt(snbt, pos)
                value.append(itemValue)
                
                if snbt[pos] == ',':
                    pos += 1
                    continue
                elif snbt[pos] == ']':
                    break
                else:
                    raise ValueError(f'Missing "," or "]"  at {pos}')
        
        return cls(value), pos+1

    def insert(self, key, value):
        self.value = self[:key] + [value] + self[key:]
    
    def sort(self, *, key=None, reverse=False):
        self.value.sort(key=key, reverse=reverse)
    
    def to_snbt(self):
        return f'[{self.prefix}{",".join( [i.to_snbt() for i in self.value] )}]'
    
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

#---------------------------------------- Concrete Classes -----------------------------------------

class End(Base):
    """You probably don't want to use this.
    
    Ends a Compound, expect erratic behavior if inserted inside one.
    """
    __slots__ = []
    ID = 0
    snbtPriority = 12
    valueType = None
    
    def __init__(self, value = None):
        pass
    
    @classmethod
    def decode(cls, iterable):
        return
    
    def encode(value = None):
        return b'\x00'
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
        if snbt[pos:] == '':
            return cls()
        else:
            raise ValueError(f'Invalid snbt for {cls} (expected empty string)')
    
    def to_snbt(self):
        return ''

class Byte(Integer):
    """Int8 tag (0 to 255)"""
    __slots__ = ['_value']
    ID = 1
    fmt = '>b'
    snbtPriority = 8
    suffixes = 'bB'

class Short(Integer):
    """Int16 tag (-32,768 to 32,767)"""
    __slots__ = ['_value']
    ID = 2
    fmt = '>h'
    snbtPriority = 9
    suffixes = 'sS'
  
class Int(Integer):
    """Int32 tag (-2,147,483,648 to 2,147,483,647)"""
    __slots__ = ['_value']
    ID = 3
    fmt = '>i'
    snbtPriority = 11

class Long(Integer):
    """Int64 tag (-9,223,372,036,854,775,808 to 9,223,372,036,854,775,807)"""
    __slots__ = ['_value']
    ID = 4
    fmt = '>q'
    snbtPriority = 10
    suffixes = 'Ll'
 
class Float(Decimal):
    """Single precision float tag (32 bits)"""
    __slots__ = ['_value']
    ID = 5
    fmt = '>f'
    regex = f'{Decimal.regex}(?P<suffix>[fF])'
    snbtPriority = 6
    suffixes = 'fF'

class Double(Decimal):
    """Double precision float tag (64 bits)"""
    __slots__ = ['_value']
    ID = 6
    fmt = '>d'
    regex = f'{Decimal.regex}(?P<suffix>(?(dot)[dD]?|[dD]))'
    snbtPriority = 7
    suffixes = 'dD'

class Byte_Array(MutableSequence):
    """A Byte array
    
    Contained tags have no name
    """
    __slots__ = ['_value']
    ID = 7
    elementType = Byte
    prefix = 'B;'
    snbtPriority = 1
    
class String(Value, Sequence):
    """Unicode string tag
    
    Payload : a Short for length, then a <length> bytes long UTF-8 string
    """
    __slots__ = ['_value']
    ID = 8
    regex = r"""(?P<openQuote>['"])(?P<value>(?:(?!(?P=openQuote))[^\\]|\\.)*)(?P<endQuote>(?P=openQuote))"""
    snbtPriority = 5
    valueType = str

    @classmethod
    def decode(cls, iterable):
        iterator = iter(iterable)
        byteLength = Short.decode(iterator)
        byteValue = util.read_bytes(iterator, n = byteLength)
        return byteValue.decode(encoding='utf-8')
    
    @staticmethod
    def encode(value : str = ''):
        byteValue = str.encode( str(value) )
        return Short.encode(len(byteValue)) + byteValue
    
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
        # f-string does not allow for backslashes inside the {}, hence the workaround
        # I think this ban is stupid but I don't control python (yet ?)
        return '"{}"'.format(''.join([char if char != '"' else r'\"' for char in self]))
    
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
    __slots__ = ['_value']
    ID = 9
    prefix = ''
    snbtPriority = 4

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
    def encode(cls, value = None):
        value = [] if value is None else value
        ID = value[0].ID if len(value) > 0 else 0
        return Byte.encode(ID) + super().encode(value)
    
class Compound(Base, collections.abc.MutableMapping):
    """A Tag dictionary, containing other names tags of any type."""
    __slots__ = ['_value']
    ID = 10
    snbtPriority = 0
    valueType = dict

    def __init__(self, value=None):
        value = {} if value is None else value
        for i in value:
            if not isinstance(value[i], Base):
                raise ValueError(f'TAG.Compound can only contain other TAGs')
        self.value = value
    
    @staticmethod
    def decode(iterable):
        iterator = iter(iterable)
        value = {}
        
        while True:
            try:
                itemType = Base.subtypes[ Byte.decode(iterator) ]
            except StopIteration:
                break
            
            if itemType == End:
                break

            itemName = String.decode(iterator)
            itemValue = itemType.from_bytes(iterator)
            value[itemName] = itemValue
        
        return value
    
    @classmethod
    def from_snbt(cls, snbt : str, pos : int = 0):
        
        try:
            assert snbt[pos] == '{'
        except (AssertionError, IndexError):
            raise ValueError(f'Missing "{{" at {pos}!')
        pos += 1
        
        regex = r'(?P<openQuote>")?(?P<name>(?(openQuote)[^"]|[^":,}])*)(?(openQuote)(?P<endQuote>")):'
        pattern = re.compile(regex)
        value = {}
        
        if snbt[pos] != '}':
            while True:
                match = pattern.match(snbt, pos)
                if match is not None:
                    value[match['name']], pos = from_snbt(snbt, match.end())
                    if snbt[pos] == ',':
                        pos += 1
                        continue
                    elif snbt[pos] == '}':
                        break
                    else:
                        raise ValueError(f'Missing "," or "}}"  at {pos}')
                else:
                    raise ValueError(f'Invalid name at {pos}')
        
        return cls(value), pos+1

    @staticmethod
    def encode(value = None):
        value = {} if value is None else value
        byteValue = bytearray()
        
        for element in value:
        
            byteValue += Byte.encode(value[element].ID)
            byteValue += String.encode(element)
            byteValue += value[element].to_bytes()
            
            if isinstance(value[element], Compound):
                byteValue += End.encode()
            
        return byteValue

    def to_snbt(self):

        pairs = []
        for key in self:
            value = self[key].to_snbt()
            if ':' in key or ',' in key or '}' in key:
                key = f'"{key}"'
            pairs.append(f'{key}:{value}')
        
        return f'{{{",".join(pairs)}}}'
    
    def __setitem__(self, key, value):
        """Replace self[key] with <value>
        
        <value> must type-compatible with self[key] if it exists
        """
        
        if key in self:
            if isinstance(self[key], List) and len(self[key]) > 0:
                value = [self[key].elementType(i) for i in value]
            value = type(self[key])(value)
        
        try:
            assert isinstance(value, Base)
        except AssertionError:
            raise ValueError('TAGs can only contain other tags !')
    
        self.value[key] = value
    
util.make_wrappers( Compound,
    nonCoercedMethods = ['keys', '__delitem__', '__getitem__', '__iter__', '__len__']
)

class Int_Array(MutableSequence):
    """A Int array
    
    Contained tags have no name
    """
    __slots__ = ['_value']
    ID = 11
    elementType = Int
    prefix = 'I;'
    snbtPriority = 2
    
class Long_Array(MutableSequence):
    """A Long array
    
    Contained tags have no name
    """
    __slots__ = ['_value']
    ID = 12
    elementType = Long
    prefix = 'L;'
    snbtPriority = 3