def bitstr(n, length : int = 0):
    """Return num as <length> bits"""
    return bin(n).removeprefix('-').removeprefix('0b').rjust(length, '0')

def read_bytes(iterable, n=0):
    """Read n bytes from the iterable and return them as a bytearray"""

    iterator = iter(iterable)
    value = bytearray()
    
    for i in range(n):
        
        nextByte = next(iterator)
        
        if isinstance(nextByte, int):
            value.append(nextByte)
        elif isinstance(nextByte, bytes):
            value += next(iterator)
    
    return value
    
def get_bits(n, start, end, length : int = None):
    """Read bits [<start>:<end>] of <n> and return them
    <length> forces <n> into that bit length"""
    mask, shift = mask_and_shift(start, end, length = n.bit_length() if length is None else length)
    return (n & mask) >> shift

def mask_and_shift(start, end, length):
    """Return a mask and shift value to access [<start>:<end>] of <length> bits"""
    shift = length - end
    mask = (1 << end - start) - 1 << shift
    return mask, shift

def reverse(n):
    """Reverse the bitwise endianness of n"""
    return int(bin(n)[:1:-1], 2)

def set_bits(n, start, end, newValue, length : int = None):
    """Change bits [<start>:<end>] of <n> to <newValue> and return <n>
    <length> forces <n> into that bit length"""
    mask, shift = mask_and_shift(start, end, length = n.bit_length() if length is None else length)
    return (n & ~mask) | (newValue << shift)