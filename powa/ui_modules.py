from tornado.web import UIModule


class Messages(UIModule):

    def render(self):
        return self.render_string("messages.html")


class MenuEntry(object):

    def __init__(self, title, url_name, url_params=None, children=None):
        self.title = title
        self.url_name = url_name
        self.url_params = url_params or {}
        # Setting children helps showing dropdown menu in breadcrumb
        # Useful for listing databases for examples
        self.children = children
