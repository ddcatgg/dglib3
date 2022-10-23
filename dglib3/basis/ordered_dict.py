from collections import OrderedDict

from . import pydicti

OrderedDictCaseInsensitive = pydicti.build_dicti(OrderedDict, "OrderedDictCaseInsensitive")


def test():
    d = OrderedDictCaseInsensitive({"a": 0, "A": 1})
    assert (d == {"A": 1})
    assert (d["a"] == 1 and d.get("A") == 1)


if __name__ == '__main__':
    test()
