##############################################################################
# Copyright (c) 2016 NEC Corporation and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

import argparse
from flask import Flask
from flask import request
import json
import logger as doctor_log
import sys
import time
from oslo_config import cfg

LOG = doctor_log.Logger('doctor_consumer').getLogger()


app = Flask(__name__)


@app.route('/failure', methods=['POST'])
def event_posted():
    LOG.info('doctor consumer notified at %s' % time.time())
    LOG.info('received data = %s' % request.data)
    d = json.loads(request.data)
    return "OK"


OPTS = [
    cfg.IntOpt('port',
               help='http server port')
]

def get_args():
    parser = argparse.ArgumentParser(description='Doctor Sample Consumer')
    parser.add_argument('port', metavar='PORT', type=int, nargs='?',
                        help='the port for consumer')
    return parser.parse_args()


def main():
    conf = cfg.ConfigOpts()
    conf.register_cli_opts(OPTS, group='consumer')
    conf(sys.argv[1:], default_config_files=['doctor.conf'])
    app.run(host="0.0.0.0", port=conf.consumer.port)


if __name__ == '__main__':
    main()
