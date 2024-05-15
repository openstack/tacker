# Copyright (C) 2024 Nippon Telegraph and Telephone Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from functools import wraps
import logging
import sys
from time import time

# Format of logger used as similar to oslo_log. The reason of using such an
# original logger is because oslo_log does not support to output ot stdout
# and cannot see logs on job output on zuul.
logging.Formatter(
    fmt='%(asctime)s.$(msecs)s | %(name)s | %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
fmt = '%(asctime)s.%(msecs)03d | %(name)s | %(levelname)s %(message)s'
dfmt = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(stream=sys.stdout, format=fmt, datefmt=dfmt,
                    encoding='utf-8', level=logging.DEBUG)


def get_logger(name=None):
    """Return a logger used as similar to oslo_log"""
    return logging.getLogger(name)


def measure_exec_time(f):
    """Decorator for measuring execution time of a function"""

    @wraps(f)
    def wrap(*args, **kw):
        logger = logging.getLogger(__name__)
        logger.debug('Start measuring exec time: %r' % f.__name__)
        t_start = time()
        result = f(*args, **kw)
        t_end = time()
        logger.debug('Measure exec time: %r %.3f [sec]' % (
            f.__name__, t_end - t_start))
        return result
    return wrap
