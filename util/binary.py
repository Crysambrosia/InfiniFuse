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
    
def get_bits(num, start, end, length=64):
    '''Like bits(num)[from:to] interpreted as int'''
    mask = 2**(end-start)-1
    shift = length - (end-start) - start
    return (num & (mask << shift)) >> shift