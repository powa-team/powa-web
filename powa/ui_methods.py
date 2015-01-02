"""
Set of helper functions available from the templates.
"""

from powa import __VERSION__
from powa.json import JSONEncoder
from tornado.options import options
import pickle
try:
    from urllib import urlencode  # py2
except ImportError:
    from urllib.parse import urlencode  # py3


def version(_):
    """
    Returns:
        the current powa version.
    """
    return __VERSION__


def servers(_):
    """
    Returns:
        the servers defined in the configuration file.
    """
    return options.servers


def field(_, **kwargs):
    """
    Returns:
        a form field formatted with the given attributes.
    """
    kwargs.setdefault('id', kwargs.get('username'))
    kwargs.setdefault('tag', 'input')
    kwargs.setdefault('type', 'text')
    kwargs.setdefault('class', 'form-control')
    attrs = " ".join('%s="%s"' % (key, value) for key, value in kwargs.items()
                     if key not in ('tag', 'label'))
    kwargs['attrs'] = attrs

    def render(content):
        """
        Render the field itself.
        """
        kwargs['content'] = content.decode('utf8')
        return """
<div class="large-12 columns">
    <label for="%(id)s">%(label)s:</label>
    <%(tag)s %(attrs)s>
        %(content)s
    </%(tag)s>
</div>
""" % kwargs

    return render


def flash(self, message, category=""):
    """
    Stores a message to be displayed on the next rendered page.
    """
    flashes = self.get_pickle_cookie("_flashes") or {}
    flashes.setdefault(category, []).append(message)
    self.set_pickle_cookie("_flashes", pickle.dumps(flashes))
    self.flashed_messages = flashes


def flashed_messages(self):
    """
    Returns:
        a mapping of flashed message category to their messages
    """
    messages = self.get_pickle_cookie("_flashes") or {}
    self.set_pickle_cookie("_flashes", None)
    for key, my_messages in self.flashed_messages.items():
        messages.setdefault(key, []).extend(my_messages)
    self.flashed_messages = {}
    return messages


def to_json(_, value):
    """
    Utility function to render json in templates.
    """
    return JSONEncoder().encode(value)

def reverse_url_with_params(self, url_name, params=None, url_args=None):
    """
    Append given parameters, or those from the request, to the url.
    """
    if params == None:
        params = self.request.arguments
    url_args = url_args or []
    url = self.reverse_url(url_name, *url_args)
    if params:
        url += "?%s" % urlencode(list(params.items()), True)
    return url
