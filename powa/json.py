from __future__ import absolute_import
from json import JSONEncoder as BaseJSONEncoder
from datetime import datetime
from decimal import Decimal

class JSONEncoder(BaseJSONEncoder):

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S%z")
        if isinstance(obj, JSONizable):
            return obj.to_json()
        return BaseJSONEncoder.default(self, obj)

class JSONizable(object):

    def to_json(self):
        return {key: val for key, val in self.__dict__.items()
                if not key.startswith("_")}

def to_json(object):
    return JSONEncoder().encode(object)
