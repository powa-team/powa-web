from tornado.web import UIModule

class UserMenu(UIModule):

    def render(self):
        return ""


class SideBar(UIModule):

    def render(self):
        if self.current_user:
            return self.render_string("sidebar.html",
                                      databases=self.handler.databases,
                                      current_database=self.handler.database)
        else:
            return ""
