Swprobe
-------
A probing middleware service for Swift that gathers metrics about request and flushes those to statsd
(https://github.com/etsy/statsd)

Quick Installation
------------------
1) Check out this repository

2) Run python setup.py install

3) Alter your proxy.conf pipeline to include probe:

    [pipeline:main]
    pipeline = healthcheck probe cache auth staticweb proxy-server

4) Add a section for the probe WSGI filter:

    [filter:probe]
    use = egg:swprobe#probe
    host = localhost
    port = 8125
    prefix = swift.dev.
    suffix =

5) Restart the proxy

6) If you're running statsd and graphite, you should see the metrics popping up in graphite

Configuration
-------------

*   host: host running statsd
*   port: UDP port used by statsd
*   prefix: all stats names will have this value as prefix
*   suffix: all stats names will have this value as suffix

Metrics
-------
The following metrics are created:

1. Timers:
    auth - time spent in miliseconds on requests to /auth
    <account_name>.<HTTP_METHOD>_<HTTP_STATUS> - per account timings/counts for HTTP methods used and http responses sent.

2. Counters:
    Counters for all the timers listed
    <account_name>.bytes_uploaded - number of bytes uploaded to account
    <account_name>.bytes_downloaded - number of bytes downloaded

Disclaimer
----------
This has not yet been tested with production workloads
