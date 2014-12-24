#!/usr/bin/env python
from powa import make_app
import tornado.ioloop

if __name__ == "__main__":
    application = make_app(debug=True, gzip=True, compress_response=True)
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
