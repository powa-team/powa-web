#!/usr/bin/env python
import logging
import tornado.ioloop
from powa import make_app
from tornado.options import options

if __name__ == "__main__":
    application = make_app(debug=True, gzip=True, compress_response=True)
    application.listen(options.port, address=options.address)
    logger = logging.getLogger("tornado.application")
    logger.info(
        "Starting powa-web on http://%s:%s%s",
        options.address,
        options.port,
        options.url_prefix,
    )
    tornado.ioloop.IOLoop.instance().start()
