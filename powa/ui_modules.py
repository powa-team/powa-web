from tornado.web import UIModule


class Messages(UIModule):

    def render(self):
        return self.render_string("messages.html")
