from powa.framework import AuthHandler
from powa import queries
from tornado.web import HTTPError
from tornado.escape import json_encode


class QueryHandler(AuthHandler):

    def get(self, queryname):
        query = getattr(queries, queryname, None)
        if query is None:
            raise HTTPError(404)
        values = self.execute(
            query,
            params={key: value[0].decode('utf8')
                    for key, value
                    in self.request.query_arguments.items()})
        data = {"data": [dict(val) for val in values]}
        self.render_json(data)
