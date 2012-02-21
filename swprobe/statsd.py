# Copyright (c) 2010 Etsy
# Copyright (c) 2012 Spil Games
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

from socket import *

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
