def bits(n, length : int = 0):
    """Return num as <length> bits"""
    return bin(n).removeprefix('0b').rjust(length, '0')

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
    
def bit_value(n, start, end, length=64):
    """Read bits from <start> to <end> of a value, return as an int"""
    mask = 2**(end-start)-1
    shift = length - (end-start) - start
    return (n & (mask << shift)) >> shift

def reverse(n):
    """Reverse the bitwise endianness of n"""
    return int(bin(n)[:1:-1], 2)