# Copyright 2015 Red Hat, Inc.
# Copyright (c) 2014-2018 China Mobile (SuZhou) Software Technology Co.,Ltd.
# All Rights Reserved
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

import six
import sys
import testtools


def requires_py2(testcase):
    return testtools.skipUnless(six.PY2, "requires python 2.x")(testcase)


def requires_py3(testcase):
    return testtools.skipUnless(six.PY3, "requires python 3.x")(testcase)


if sys.version_info < (3,):
    def compact_byte(x):
        return x
else:
    def compact_byte(x):
        return bytes(x, 'utf-8')
