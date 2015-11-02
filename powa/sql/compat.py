from sqlalchemy.types import UserDefinedType
from sqlalchemy import util
import sqlalchemy
import json


if sqlalchemy.__version__ >= '0.9':
    from sqlalchemy.dialects.postgresql import JSON
else:
    class JSON(UserDefinedType):

        def get_col_spec(self):
            return self.__class__.__name__

        def result_processor(self, dialect, coltype):
            json_deserializer = getattr(dialect, "_json_deserializer", None) or json.loads
            if util.py2k:
                encoding = dialect.encoding

                def process(value):
                    if value is None:
                        return None
                    return json_deserializer(value.decode(encoding))
            else:
                def process(value):
                    if value is None:
                        return None
                    return json_deserializer(value)
            return process


if sqlalchemy.__version__ >= '0.9.7':
    from sqlalchemy.dialects.postgresql import JSONB
else:
    class JSONB(JSON):
        pass
