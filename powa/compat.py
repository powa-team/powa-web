"""
Py2/3 compatibility layer

Mostly copied straight from six:
    http://pypi.python.org/pypi/six/

"""



def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})

class classproperty(object):

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class hybridmethod(object):

    def __init__(self, class_method=None, instance_method=None):
        self._class_method = class_method
        self._instance_method = instance_method or class_method

    def instance_method(self, instance_method):
        self._instance_method = instance_method
        return self

    def class_method(self, class_method):
        self._class_method = class_method
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return self._class_method.__get__(owner, owner.__class__)
        else:
            return self._instance_method.__get__(instance, owner)


