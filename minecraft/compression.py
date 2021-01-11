import gzip
import zlib

def compress(data, compression : int = 3):
    """Compress a bytes-like object, return (data)
    
    Uses the compression methods specified by minecraft
    """
    if compression == 1:
        return gzip.compress(data)
    elif compression == 2:
        return zlib.compress(data)
    elif compression == 3:
        return data
    else:
        raise ValueError(f'Unknown compression method {compression}')

def decompress(data, compression : int = None):
    """Decompress a bytes-like object, return (data, compression)
    
    Uses the compression methods specified by minecraft
    """
    if compression is None:
        for tryCompression in [1,2,3]:
            try:
                return decompress(data, tryCompression)
            except (gzip.BadGzipFile, zlib.error):
                continue
        raise RuntimeError('Unknown compression method.')
    elif compression == 1:
        data = gzip.decompress(data)
    elif compression == 2:
        data = zlib.decompress(data)
    elif compression == 3:
        data = data
    else:
        raise ValueError(f'Unknown compression method {compression}')
    return data, compression