#!/usr/bin/env python
from powa import make_app
import tornado

if tornado.version > '4':
    from tornado.wsgi import WSGIAdapter
    application = make_app(debug=False, gzip=True, compress_response=True)
    application = WSGIAdapter(application)
else:
    application = make_app(debug=False, gzip=True, compress_response=True, legacy_wsgi=True)
