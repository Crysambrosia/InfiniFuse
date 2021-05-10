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
        with DatFile(path) as f:
            return TAG.Compound(f)
    
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
        self[self.idcounts] = value

    def convert_key(self, key):
        key = int(key)
        
        if key not in range(len(self)):
            raise IndexError(f'Key must be 0 - {len(self)}, not {key}')
        
        return key

    @property
    def idcounts(self):
        """Biggest used map ID, as stored in idcounts.dat"""
        path = os.path.join(self.folder, 'idcounts.dat')
        
        with DatFile(path) as f:
            if f == {}:
                return -1
            elif 'DataVersion' in f['']:
                return f['']['data']['map']
            else:
                return f['']['map']

    @idcounts.setter
    def idcounts(self, value):
        """Change idcounts. Could result in weird behavior !"""
        
        if value < 0:
            raise ValueError('idcounts must be at least 0 !')
        
        path = os.path.join(self.folder, 'idcounts.dat')
        
        with DatFile(path) as f:
            if f == {}:
            
                f.value = TAG.Compound({
                    '' : TAG.Compound({
                        'data' : TAG.Compound({
                            'map' : TAG.Int(value)
                        }),
                        'DataVersion' : TAG.Int(2578)
                    })
                })
                
            elif 'Dataversion' in f['']:
                f['']['data']['map'] = value
                
            else:
                f['']['map'] = value