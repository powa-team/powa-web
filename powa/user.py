from powa.framework import BaseHandler


class LoginHandler(BaseHandler):

    def get(self):
        self._status_code = 403
        return self.render("login.html", title="Login")

    def post(self, *args, **lwargs):
        username = self.get_argument('username')
        password = self.get_argument('password')
        server = self.get_argument('server')
        try:
            self.connect(username=username, password=password, server=server)
        except Exception as e:
            self.flash("Auth failed", "alert")
            self.get()
            return
        self.set_secure_cookie('username', username)
        self.set_secure_cookie('password', password)
        self.set_secure_cookie('server', server)
        self.redirect(self.get_argument('next', '/'))


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_all_cookies()
        return self.redirect('/')
