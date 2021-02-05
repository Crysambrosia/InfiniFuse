def bitstr(n, length : int = 0):
    """Return <n> as <length> bits"""
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
    
def get_bits(n, start, end):
    """Return value of bits [<start>:<end>] of <n>"""
    return (int(n) & ((1 << end) - 1)) >> start
    
def reverse(n):
    """Reverse the bits of <n>"""
    return int(bin(n)[:1:-1], 2)

def set_bits(n, start, end, value):
    """Set bits [<start>:<end>] of <n> to <value> and return <n>"""
    mask = ( 1 << end ) - ( 1 << start ) 
    return (int(n) & ~mask) | (value << start) & mask