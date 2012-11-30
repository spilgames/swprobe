# Copyright (c) 2012 Spil Games
# Copyright (c) 2010-2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 
# This piece of middleware will sit on the Swift pipeline and inspecting
# requests as they pass by. Metrics for these requests will be dumped to
# statsd over UDP. These may then be plotted in graphite.
#
# To use this middleware, add a section to the proxy.conf file:
#
# [filter:probe]
# use = egg:swprobe#oprobe
# host = localhost
# port = 8125
# prefix = swift.dev.
# suffix =
#
# Then, add it to the pipeline, like:
# pipeline = healthcheck probe cache auth staticweb proxy-server

from webob import Request, Response
from socket import *
import sys
from pprint import *
from time import time
from statsd import Statsd
from swift.common.utils import split_path, cache_from_env, get_logger


class ProbeMiddleware(object):
    """
    Probe middleware used for monitoring and statistics gathering.

    It will sit in the request pipeline doing nothing, but offers a place to
    send metrics to a system.
    """

    def __init__(self, app, conf, *args, **kwargs):
        self.statsd = Statsd(conf)
        self.logger = get_logger(conf, log_route='probe')
        self.app = app
        self.pp = PrettyPrinter(indent=4)

    def GET(self, req):
        """Returns a 200 response with "OK" in the body."""
        return Response(request=req, body="OK", content_type="text/plain")

    def statsd_event(self, env, req):
        try:
            request_time = time() - env['swprobe.start_time']
            headers = dict(env['swprobe.headers'])
            response = getattr(req, 'response', None)
            if getattr(req, 'client_disconnect', False) or \
                       getattr(response, 'client_disconnect', False):
                status_int = 499
            else:
                status_int = env['swprobe.status']
            duration = (time() - env['swprobe.start_time']) * 1000

            # Find out how much bytes were transferred. For PUTs we can get this from the request object,
            # but for GETs we look at the Content-Length header of the response
            # Don't know how to find out # bytes transferred for aborted transfers
            transferred = getattr(req, 'bytes_transferred', 0)
            transferred = 0 if transferred == '-' else int(transferred)
            if transferred is 0:
                transferred = getattr(response, 'bytes_transferred', 0)
            if req.path.startswith("/auth"):
                # Time how long auth request takes
                self.statsd.increment("req.auth")
                self.statsd.timing("auth", duration)
            elif transferred == 0 and status_int != 499 and req.method == "GET":
                transferred = headers['content-length']
                # Find out for which account the request was made
                try:
                    swift_account = env["REMOTE_USER"].split(",")[1]
                except:
                    swift_account = "anonymous"
                self.statsd.increment("req.%s.%s.%s" %(swift_account, req.method, status_int))
                if status_int >= 200 and status_int < 400:
                    # Log timers for succesful requests
                    self.statsd.timing("%s" %(req.method), duration)
                # Upload and download size statistics
                if req.method == "PUT":
                    self.statsd.update_stats("xfer.%s.bytes_uploaded" % swift_account, transferred)
                elif req.method == "GET":
                    self.statsd.update_stats("xfer.%s.bytes_downloaded" % swift_account, transferred)
        except Exception as e:
            try:
                self.logger.exception(_("Encountered error in statsd_event"))
                self.logger.exception(e)
            except Exception:
                pass


    def __call__(self, env, start_response):
        """WSGI callable"""

        def _start_response(status, headers, exc_info=None):
            """start_response wrapper to grab headers and status code"""
            # Convert all headers to lower case
            new_h = [(k.lower(), v) for k,v in headers]
            env['swprobe.headers'] = new_h
            env['swprobe.status'] = int(status.split(' ', 1)[0])
            start_response(status, headers, exc_info)

        req = Request(env)

        # Rewrite: this code is borrowed from swift-informant and seems to be the proper way to do this.
        # Get out of the main request flow and do everything after the request has been served
        try:
            # register the post-hook
            if 'eventlet.posthooks' in env:
                env['swprobe.start_time'] = time()
                env['eventlet.posthooks'].append(
                    (self.statsd_event, (req,), {}))
            return self.app(env, _start_response)
        except Exception:
            self.logger.exception('WSGI EXCEPTION:')
            _start_response('500 Internal Server Error',
                            [('Content-Length', '0')])
            return []

def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    def probe_filter(app):
        return ProbeMiddleware(app, conf)
    return probe_filter
