from __future__ import unicode_literals
from powa.framework import BaseHandler
from powa import __VERSION_NUM__


class LoginHandler(BaseHandler):

    def get(self):
        self._status_code = 403
        return self.render("login.html", title="Login")

    def post(self, *args, **kwargs):
        username = self.get_argument('username')
        password = self.get_argument('password')
        server = self.get_argument('server')
        try:
            self.connect(username=username, password=password, server=server)
        except Exception as e:
            self.flash("Auth failed", "alert")
            self.logger.error(e)
            self.get()
            return
        # Check that the database is correctly installed
        version = self.get_powa_version(username=username,
                                        password=password,
                                        server=server)
        if version is None:
            self.flash('PoWA is not installed on your target database. '
                       'You should check your installation.', 'alert')
            self.redirect('/')
        # Major.Minor version should be the same
        if version[0:2] != __VERSION_NUM__[0:2]:
            self.flash(
                'Unable to connect: powa-archivist version %s.X does not match powa-web version %s.X' %
                ('.'.join(str(x) for x in version[0:2]),
                 '.'.join(str(x) for x in __VERSION_NUM__[0:2])),
                'alert')
            self.redirect('/')
        self.set_secure_cookie('username', username)
        self.set_secure_cookie('password', password)
        self.set_secure_cookie('server', server)
        self.redirect(self.get_argument('next', '/'))


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_all_cookies()
        return self.redirect('/')
