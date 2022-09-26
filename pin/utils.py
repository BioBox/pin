
from collections import UserDict

class DList(UserDict):
    """
    This is a dictionary that can get and set its elements as though it were a
    list. This is possible because dictionaries in python are now ordered by
    insertion.

    However, this comes with the restriction that all keys must be strings.
    """
    def __getitem__(self, k):
        if isinstance(k, str):
            return self.data[k]
        elif isinstance(k, int):
            return list(self.values())[k]
        else:
            raise KeyError(k)

    def __setitem__(self, k, v):
        if isinstance(k, str):
            self.data[k] = v
        elif isinstance(k, int):
            real_key = list(self.keys())[k]
            self.data[real_key] = v
        else:
            raise KeyError(k)

    def before(self, k: str, count=1):
        lkeys = list(self)
        index = lkeys.index(k)
        return self[index - count]

    def after(self, k: str, count=1):
        lkeys = list(self)
        index = lkeys.index(k)
        return self[index + count]
