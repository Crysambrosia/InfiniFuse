from minecraft.datfile import DatFile
import minecraft.TAG as TAG
import os

class MapManager():
    """Manages all the map files in a folder"""
    
    def __init__(self, folder : str):
        self.folder = folder
    
    def __len__(self):
        return self.idcounts + 1
    
    def __getitem__(self, key):
        """Get map number <key>"""
        key = self.convert_key(key = key)
        path = os.path.join(self.folder, f'map_{key}.dat')
        return DatFile.open(path)
    
    def __iter__(self):
        """Generator object returning every contained map"""
        for key in range(len(self)):
            yield self[key]
    
    def __setitem__(self, key, value):
        """Set map number <key> to <value>"""
        key = self.convert_key(key = key)
        path = os.path.join(self.folder, f'map_{key}.dat')
        f = DatFile(path = path, value = value)
        f.write()
    
    def append(self, value):
        """Add a map to this world"""
        self.idcounts += 1
        self[self.idcount] = value

    def convert_key(self, key):
        key = int(key)
        
        if key not in range(len(self)):
            raise IndexError(f'Key must be 0 - {len(self)}, not {key}')
        
        return key

    @property
    def idcounts(self):
        """Biggest used map ID, as stored in idcounts.dat"""
        path = os.path.join(self.folder, 'idcounts.dat')
        
        with DatFile.open(path) as f:
        
            if 'DataVersion' not in f['']:
                f[''] = TAG.Compound(
                    {
                        'data' : TAG.Compound(
                            {
                                'map' : TAG.Int(f['']['map'])
                            }
                        ),
                        'DataVersion' : TAG.Int(2578)
                    }
                )
            
            return f['']['data']['map']

    @idcounts.setter
    def idcounts(self, value):
        """Change idcounts. Could result in weird behavior !"""
        path = os.path.join(self.folder, 'idcounts.dat')
        with DatFile.open(path) as f:
            f['']['data']['map'] = value