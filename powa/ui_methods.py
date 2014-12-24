from powa import __VERSION__
from powa import queries
from powa.json import JSONEncoder
from tornado.options import options
import pickle


def version(self):
    return __VERSION__


def servers(self):
    return options.servers


def databases(self):
    return self.execute(queries.DBLIST)


def field(self, **kwargs):
    kwargs.setdefault('id', kwargs.get('username'))
    kwargs.setdefault('tag', 'input')
    kwargs.setdefault('type', 'text')
    kwargs.setdefault('class', 'form-control')
    attrs = " ".join('%s="%s"' % (key, value) for key, value in kwargs.items()
                     if key not in ('tag', 'label'))
    kwargs['attrs'] = attrs

    def render(content):
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
    flashes = self.get_pickle_cookie("_flashes") or {}
    flashes.setdefault(category, []).append(message)
    self.set_pickle_cookie("_flashes", pickle.dumps(flashes))
    self._flashed_messages = flashes


def flashed_messages(self):
    messages = self.get_pickle_cookie("_flashes") or {}
    self.set_pickle_cookie("_flashes", None)
    for key,  my_messages in self._flashed_messages.items():
        messages.setdefault(key, []).extend(my_messages)
    self._flashed_messages = {}
    return messages


def to_json(self, value):
    return JSONEncoder().encode(value)
