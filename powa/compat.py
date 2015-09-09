"""
Py2/3 compatibility layer

Mostly copied straight from six:
    http://pypi.python.org/pypi/six/

"""
from __future__ import absolute_import
import psycopg2
from psycopg2 import extensions
import json

# If psycopg2 < 2.5, register json type
psycopg2_version = tuple(psycopg2.__version__.split(' ')[0].split('.'))
if psycopg2_version < ('2', '5'):
    JSON_OID = 114
    newtype = extensions.new_type(
        (JSON_OID,), "JSON", lambda data, cursor: json.loads(data))
    extensions.register_type(newtype)

def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        """The actual metaclass."""
        def __new__(cls, name, _, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})

class classproperty(object):
    """
    A descriptor similar to property, but using the class.
    """

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class hybridmethod(object):
    """
    Decorator allowing to define method which behaves differently
    if called at the instance or at the class level.
    """

    def __init__(self, class_method=None, instance_method=None):
        self._class_method = class_method
        self._instance_method = instance_method or class_method

    def instance_method(self, instance_method):
        """Setter for the instance method."""
        self._instance_method = instance_method
        return self

    def class_method(self, class_method):
        """Setter for class method."""
        self._class_method = class_method
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return self._class_method.__get__(owner, owner.__class__)
        else:
            return self._instance_method.__get__(instance, owner)
