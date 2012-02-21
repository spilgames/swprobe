# Copyright (c) 2012, Spil Games
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
import datetime
from swift.common.utils import split_path, cache_from_env, get_logger

class Statsd(object):
    # Modified version of https://github.com/etsy/statsd/blob/master/examples/python_example.py
 
    def __init__(self, config):
        self.host = config.get("host")
        self.port = int(config.get("port"))
        self.prefix = config.get("prefix")
        self.suffix = config.get("suffix")
        self.addr = (self.host, self.port)
        self.udp_sock = socket(AF_INET, SOCK_DGRAM)
    
    def timing(self, stat, time, sample_rate=1):
        """
        Log timing information
        >>> from python_example import Statsd
        >>> Statsd.timing('some.time', 500)
        """
        stats = {}
        stats[stat] = "%d|ms" % time
        self.send(stats, sample_rate)

    def increment(self, stats, sample_rate=1):
        """
        Increments one or more stats counters
        >>> Statsd.increment('some.int')
        >>> Statsd.increment('some.int',0.5)
        """
        self.update_stats(stats, 1, sample_rate)

    def decrement(self, stats, sample_rate=1):
        """
        Decrements one or more stats counters
        >>> Statsd.decrement('some.int')
        """
        self.update_stats(stats, -1, sample_rate)
    
    def update_stats(self, stats, delta=1, sampleRate=1):
        """
        Updates one or more stats counters by arbitrary amounts
        >>> Statsd.update_stats('some.int',10)
        """
        if (type(stats) is not list):
            stats = [stats]
        data = {}
        for stat in stats:
            data[stat] = "%s|c" % delta

        self.send(data, sampleRate)
    
    def send(self, data, sample_rate=1):
        """
        Squirt the metrics over UDP
        """
        
        sampled_data = {}
        
        if(sample_rate < 1):
            import random
            if random.random() <= sample_rate:
                for stat in data.keys():
                    value = sampled_data[stat]
                    sampled_data[stat] = "%s|@%s" %(value, sample_rate)
        else:
            sampled_data=data
        

        try:
            for stat in sampled_data.keys():
                value = data[stat]
                send_data = "%s%s%s:%s" % (self.prefix, stat, self.suffix, value)
                self.udp_sock.sendto(send_data, self.addr)
        except:
            print "Unexpected error:", pprint(sys.exc_info())
            pass # we don't care

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

    def __call__(self, env, start_response):
        req = Request(env)

        # Go to the next app in the pipeline
        # try to capture response before sending it back
        start = datetime.datetime.now()
        response = self.app(env, start_response)
        end = datetime.datetime.now()
        time = float((end-start).microseconds) / 1000.0
        # Get response object from environment
        response_obj = env["webob.adhoc_attrs"]["response"]
        # Convert 204 into 200 etc
        response_code = response_obj.status_int // 100 * 100
        # This is the response size for GETs
        response_size = response_obj.content_length

        if req.path.startswith("/auth"):
            # Time how long auth request takes
            self.statsd.timing("auth", time)
        else:
            # Find out for which account the request was made
            swift_account = env["REMOTE_USER"].split(",")[1]
            self.statsd.timing("%s.%s_%s" %(swift_account, req.method, response_code), time)
            # Upload and download size statistics
            if req.method == "PUT":
                size = env["webob.adhoc_attrs"]["bytes_transferred"]
                self.statsd.update_stats("%s.bytes_uploaded" % swift_account, size)
            elif req.method == "GET":
                self.statsd.update_stats("%s.bytes_downloaded" % swift_account, response_size)
                
        return response


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    def probe_filter(app):
        return ProbeMiddleware(app, conf)
    return probe_filter
