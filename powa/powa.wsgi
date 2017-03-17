#!/usr/bin/env python
from powa import make_app
import sys
import tornado

if tornado.version > '4':
    from tornado.wsgi import WSGIAdapter
    application = make_app(debug=False, gzip=True, compress_response=True)
    application = WSGIAdapter(application)
else:
    # Wrap sys.stderr because certain versions of mod_wsgi don't
    # implement isatty for the log file, and certain versions
    # of tornado don't check for the existence of isatty
    if not hasattr(sys.stderr, "isatty"):
        class StdErrWrapper(object):

            def __init__(self, wrapped):
                super(StdErrWrapper, self).__setattr__("wrapped", wrapped)

            def isatty(self):
                if hasattr(self.wrapped, "isatty"):
                    return self.wrapped.isatty
                return False

            def __getattr__(self, att):
                return getattr(self.wrapped, att)

            def __setattr__(self, att, value):
                return setattr(self.wrapped, att, value)

        sys.stderr = StdErrWrapper(sys.stderr)
    application = make_app(debug=False, gzip=True, compress_response=True, legacy_wsgi=True)
