"""
Dashboard for the powa-collector summary page, and other infrastructure for the
collector handling.
"""
from __future__ import absolute_import
import json
from powa.dashboards import MetricGroupDef
from powa.framework import AuthHandler


class CollectorServerDetail(MetricGroupDef):
    name = "Server details"
    data_url = r"/config/(\d+)/server_details/"
    params = ["server"]

    @property
    def query(self):
        return None

    def post_process(self, data, server, **kwargs):
        sql = """SELECT *
            FROM powa_servers s
            JOIN powa_snapshot_metas m ON m.srvid = s.id
            WHERE s.id = %(server)s"""

        row = self.execute(sql, params={'server': server}).fetchone()

        # unexisting server, bail out
        if (row is None):
            data["messages"] = {'alert': ["This server does not exists"]}
            return data

        status = 'unknown'
        if (server == '0'):
            status = self.execute("""SELECT
                    CASE WHEN count(*) = 1 THEN 'running'
                    ELSE 'stopped'
                    END
                    FROM pg_stat_activity
                    WHERE application_name LIKE 'PoWA - %%'""").fetchone()[0]
        else:
            raw = self.notify_collector('WORKERS_STATUS', [server], 2)

            status = None
            # did we receive a valid answer?
            if (len(raw) != 0 and "OK" in raw[0]):
                # just keep the first one
                tmp = raw[0]["OK"]
                if (server in tmp):
                    status = json.loads(tmp)[server]

        if (status is None):
            return {'messages': {"warning": ["Could not get status for this "
                                             "instance"]},
                    'data': []}

        msg = 'Collector status for this instance: ' + status
        level = "alert"
        if (status == "running"):
            level = "success"

        return {'messages': {level: [msg]},
                'data': []}


class CollectorReloadHandler(AuthHandler):
    """Page allowing to choose a server."""

    def get(self):
        res = False

        answers = self.notify_collector('RELOAD')

        # iterate over the results.  If at least one OK is received, report
        # success, otherwise failure
        for a in answers:
            if ("OK" in a):
                res = True
                break

        self.render_json(res)
