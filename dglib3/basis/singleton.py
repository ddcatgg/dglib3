# http://blog.csdn.net/ghostfromheaven/article/details/7671853
import threading


class Singleton(object):
    """
    usage:
        class MyClass(Singleton):
            pass
    """

    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls, *args, **kw)
        return cls._instance


class Singleton2(type):
    """
    usage:
        class MyClass(object):
            __metaclass__ = Singleton2
    """

    def __init__(cls, name, bases, _dict):
        super(Singleton2, cls).__init__(name, bases, _dict)
        cls._instance = None

    @classmethod
    def __call__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = super(Singleton2, cls).__call__(*args, **kw)
        return cls._instance


class SingletonMixin(object):
    __instance = None
    __lock = threading.RLock()

    @classmethod
    def get_instance(cls, *args, **kw):
        with cls.__lock:
            if cls.__instance is None:
                cls.__instance = cls(*args, **kw)
            return cls.__instance


def singleton(strict=True):
    """
    usage:
        @singleton()
        class MyClass(object):
            pass
    """

    def _singleton(cls):
        return _Singleton(cls)

    class _Singleton(object):
        def __init__(self, cls):
            self.__cls = cls
            self.__lock = threading.RLock()
            self.__instance = None

        def __call__(self, *args, **kw):
            if strict:
                return self.get_instance(*args, **kw)

            return self.create_instance(*args, **kw)

        def get_instance(self, *args, **kw):
            with self.__lock:
                if not self.__instance:
                    self.__instance = self.create_instance(*args, **kw)
                return self.__instance

        def create_instance(self, *args, **kw):
            return self.__cls(*args, **kw)

    return _singleton


def test():
    @singleton()
    class MyClass(object):
        def __init__(self, a, b, c=0):
            print("my class", a, b, c)

    @singleton(strict=False)
    class MyUnStrictClass(object):
        def __init__(self, a, b, c=0):
            print("my unstrict class", a, b, c)

    my1 = MyClass(1, 2)
    my2 = MyClass(3, 4, 5)
    assert (my1 == my2)
    assert (MyClass.get_instance(11, 22) == MyClass.get_instance() == my1 == my2)

    my3 = MyUnStrictClass(1, 2)
    my4 = MyUnStrictClass(3, 4, 5)
    assert (my3 != my4)
    assert (MyUnStrictClass.get_instance(11, 22) == MyUnStrictClass.get_instance())


if __name__ == '__main__':
    test()
