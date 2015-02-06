#!/usr/bin/env python
from powa import make_app
from tornado.wsgi import WSGIAdapter

application = make_app(debug=False, gzip=True, compress_response=True)
application = WSGIAdapter(application)
