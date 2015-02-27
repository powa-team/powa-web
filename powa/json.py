from __future__ import absolute_import
from json import JSONEncoder as BaseJSONEncoder
from datetime import datetime
from decimal import Decimal

class JSONEncoder(BaseJSONEncoder):
    """
    JSONEncoder used throughout the application.
    Handle Decimal, datetime and JSONizable objects.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S%z")
        if isinstance(obj, JSONizable):
            return obj.to_json()
        return BaseJSONEncoder.default(self, obj)

class JSONizable(object):
    """
    Base class for an object which is serializable to JSON.
    """

    def to_json(self):
        """
        Serialize the object to JSON

        Returns:
            an object which can be encoded by the BaseJSONEncoder.
        """
        return dict(((key, val) for key, val in self.__dict__.items()
                if not key.startswith("_")))

def to_json(object):
    """
    Shortcut for encoding something to JSON.

    Arguments:
        object (object): the object to serialize to JSON
    Returns:
        a json-encoded representation of the object.
    """
    return JSONEncoder().encode(object)
