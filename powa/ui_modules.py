from tornado.web import UIModule

class UserMenu(UIModule):

    def render(self):
        return ""


class SideBar(UIModule):

    def render(self, menu):
        if self.current_user:
            return self.render_string("sidebar.html",
                                      menu=menu,
                                      databases=self.handler.databases,
                                      current_database=self.handler.database)
        else:
            return ""


class Messages(UIModule):

    def render(self):
        return self.render_string("messages.html")


class MenuEntry(UIModule):

    def __init__(self, title, url_name, url_params=None, children=None, active=False):
        self.title = title
        self.url_name = url_name
        self.children = children or []
        self.url_params = url_params or {}
        self.active = active

    def findMenu(self, url_name, url_params):
        if self.url_name == url_name:
            if all(url_params.get(key) == value
                   for key, value in self.url_params.items()):
                return self
        for child in self.children:
            result = child.findMenu(url_name, url_params)
            if result is not None:
                return result
        return None

    def render(self, handler):
        return handler.render_string("menuitem.html",
                           menu=self)

    def get_breadcrumb(self):
        base = []
        if self.active and self.url_name:
            base.append(self)
        for child in self.children:
            base.extend(child.get_breadcrumb())
        return base

GlobalMenu = [MenuEntry("Server configuration", "ConfigOverview"),
              MenuEntry("All databases", "Overview")]
