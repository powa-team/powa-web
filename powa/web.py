from powa import make_app
import tornado.ioloop
import logging
from tornado.options import options, Error as terror
from powa.options import parse_options

def run_powa():
    application = make_app(debug=False, gzip=True, compress_response=True)
    application.listen(options.port, address=options.address)
    logger = logging.getLogger("tornado.application")
    logger.info("Starting powa-web on http://%s:%s%s",
                options.address, options.port, options.url_prefix)
    tornado.ioloop.IOLoop.instance().start()
