"""
Set of helper functions available from the templates.
"""

from datetime import datetime
from powa import __VERSION__
from powa.json import JSONEncoder
from tornado.options import options
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


def year(_):
    """
    Returns:
        the current year.
    """
    return datetime.now().year


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
    <label>%(label)s:
    <%(tag)s %(attrs)s>
        %(content)s
    </%(tag)s>
    </label>
</div>
""" % kwargs

    return render


def flash(self, message, category=""):
    """
    Stores a message to be displayed on the next rendered page.
    """
    flashes = self.get_pickle_cookie("_flashes") or {}
    flashes.setdefault(category, []).append(message)
    self.set_pickle_cookie("_flashes", flashes)
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


def sanitycheck_messages(self):
    messages = {'alert': []}

    # Check if now collector is running
    sql = """SELECT
        CASE WHEN val LIKE 'PoWA collector - main thread (%%'
            THEN 'Remote collector'
            ELSE 'Backgound worker'
        END AS powa_kind,
        date_trunc('second', backend_start) as start,
        datname, usename,
        coalesce(host(client_addr), '<local>') AS client_addr,
        count(datname) OVER () AS nb_found
        FROM (
            SELECT 'PoWA - %%' AS val
            UNION ALL
            SELECT 'PoWA collector - main thread (%%'
        ) n
        JOIN pg_stat_activity a ON a.application_name LIKE n.val"""
    rows = self.execute(sql).fetchall()

    if (rows is None):
        messages["alert"].append("No collector is running!")

    sql = """SELECT
       CASE WHEN id = 0 THEN
          '<local>'
       ELSE
          COALESCE(alias, hostname || ':' || port)
       END AS alias,
        error
        FROM powa_servers s
        JOIN (SELECT srvid, unnest(errors) error
            FROM powa_snapshot_metas
            WHERE errors IS NOT NULL
        ) m ON m.srvid = s.id"""
    rows = self.execute(sql).fetchall()

    if (rows is not None and len(rows) > 0):
        for r in rows:
            messages["alert"].append("%s: %s" % (r[0], r[1]))
        return messages

    return {}


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
