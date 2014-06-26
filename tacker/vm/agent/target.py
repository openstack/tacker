# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013, 2014 Intel Corporation.
# Copyright 2013, 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                                     <isaku.yamahata at gmail com>
# All Rights Reserved.
#
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
#
# @author: Isaku Yamahata, Intel Corporation.


from oslo.messaging import target


_KEYS = ['exchange', 'topic', 'namespace', 'version', 'server', 'fanout']
_BOOLEAN_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                   '0': False, 'no': False, 'false': False, 'off': False}


def target_parse(target_str):
    attrs = target_str.split(',')
    kwargs = dict(attr.split('=', 1) for attr in attrs)
    if 'fanout' in kwargs:
        # should use oslo.config.types.Bool.__call__ ?
        value = kwargs['fanout']
        kwargs['fanout'] = _BOOLEAN_STATES[value.lower()]
    return target.Target(**kwargs)


def target_str(target):
    attrs = [(key, getattr(target, key))
             for key in _KEYS if getattr(target, key) is not None]
    return ','.join('%s=%s' % attr for attr in attrs)
