##############################################################################
# Copyright (c) 2016 NEC Corporation and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from datetime import datetime
import json
import logger as doctor_log
import os
import requests
import socket
import sys
import time

from keystoneauth1 import session
from congressclient.v1 import client
from oslo_config import cfg

from osprofiler import initializer as osprofiler_initializer
from osprofiler import opts as osprofiler_opts
from osprofiler import web as osprofiler_web
from osprofiler import profiler

import identity_auth

# NOTE: icmp message with all zero data (checksum = 0xf7ff)
#       see https://tools.ietf.org/html/rfc792
ICMP_ECHO_MESSAGE = '\x08\x00\xf7\xff\x00\x00\x00\x00'

LOG = doctor_log.Logger('doctor_monitor').getLogger()


class DoctorMonitorSample(object):

    interval = 0.1  # second
    timeout = 0.1  # second
    event_type = "compute.host.down"

    def __init__(self, conf):
        self.conf = conf
        self.hostname = conf.hostname
        self.inspector_type = conf.inspector_type
        self.ip_addr = conf.ip or socket.gethostbyname(self.hostname)

        if self.inspector_type == 'sample':
            self.inspector_url = conf.inspector_url
        elif self.inspector_type == 'congress':
            auth=identity_auth.get_identity_auth()
            self.session=session.Session(auth=auth)
            congress = client.Client(session=self.session, service_type='policy')
            ds = congress.list_datasources()['results']
            doctor_ds = next((item for item in ds if item['driver'] == 'doctor'),
                             None)

            congress_endpoint = congress.httpclient.get_endpoint(auth=auth)
            self.inspector_url = ('%s/v1/data-sources/%s/tables/events/rows' %
                                  (congress_endpoint, doctor_ds['id']))

    def start_loop(self):
        LOG.debug("start ping to host %(h)s (ip=%(i)s)" % {'h': self.hostname,
                                                       'i': self.ip_addr})
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                             socket.IPPROTO_ICMP)
        sock.settimeout(self.timeout)
        while True:
            try:
                sock.sendto(ICMP_ECHO_MESSAGE, (self.ip_addr, 0))
                data = sock.recv(4096)
            except socket.timeout:
                LOG.info("doctor monitor detected at %s" % time.time())

                self.report_error()
                LOG.info("ping timeout, quit monitoring...")
                if self.conf.profiler.enabled:
                    trace_id = profiler.get().get_base_id()
                    LOG.info("To display trace use the command:\n\n"
                             "  osprofiler trace show --html %s " % trace_id)
                return
            time.sleep(self.interval)

    @profiler.trace('report')
    def report_error(self):
        payload = [
            {
                'id': 'monitor_sample_id1',
                'time': datetime.now().isoformat(),
                'type': self.event_type,
                'details': {
                    'hostname': self.hostname,
                    'status': 'down',
                    'monitor': 'monitor_sample',
                    'monitor_event_id': 'monitor_sample_event1'
                },
            },
        ]
        data = json.dumps(payload)

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if osprofiler_web:
            headers.update(osprofiler_web.get_trace_id_headers())

        if self.inspector_type == 'sample':
            requests.post(self.inspector_url, data=data, headers=headers, proxies={'http': None, 'https': None})
        elif self.inspector_type == 'congress':
            headers.update({
                'X-Auth-Token':self.session.get_token()
            })
            requests.put(self.inspector_url, data=data, headers=headers)

SUPPORTED_INSPECTOR_TYPES = ['sample', 'congress']

OPTS = [
    cfg.StrOpt('hostname',
               help='a hostname to monitor connectivity'),
    cfg.StrOpt('ip',
               help='an IP address to monitor connectivity'),
    cfg.StrOpt('inspector-type',
               default=os.getenv('INSPECTOR_TYPE', 'sample'),
               choices=SUPPORTED_INSPECTOR_TYPES,
               help='supported: {}'.format(', '.join(SUPPORTED_INSPECTOR_TYPES))),
    cfg.StrOpt('inspector-url',
               default=os.getenv('INSPECTOR_URL', 'http://127.0.0.1:12345/events'),
               help='endpoint to report fault, e.g. "http://127.0.0.1:12345/events"')]


def main():

    conf = cfg.ConfigOpts()
    conf.register_cli_opts(OPTS)
    osprofiler_opts.set_defaults(conf)
    conf(sys.argv[1:], default_config_files=['doctor.conf'])
    if conf.profiler.enabled:
        osprofiler_initializer.init_from_conf(conf=conf,
                                              context={}, # TODO(yujunz) context for requests
                                              project='doctor',
                                              service='monitor',
                                              host='tester')
        profiler.init(conf.profiler.hmac_keys)

    monitor = DoctorMonitorSample(conf)
    monitor.start_loop()

if __name__ == '__main__':
    main()
