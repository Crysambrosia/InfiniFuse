def all_subclasses(cls):
        return set([
            i for i in cls.__subclasses__() + 
            [s for c in cls.__subclasses__() for s in all_subclasses(c)]
        ])