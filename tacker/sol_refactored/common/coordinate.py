# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
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

import functools
import inspect

from oslo_log import log as logging

from tacker.common import coordination

from tacker.sol_refactored.common import exceptions as sol_ex


LOG = logging.getLogger(__name__)


# NOTE: It is used to prevent operation for the same vnf instance
# from being processed at the same time. It can be applied between
# threads of a process and different processes (e.g. tacker-server
# and tacker-conductor) on a same host.
# Note that race condition of very short time is not considered.

def lock_vnf_instance(inst_arg, delay=False):
    # NOTE: tacker-server issues RPC call to tacker-conductor
    # (just) before the lock released. 'delay' is for tacker-conductor
    # to be able to wait if it receives RPC call before tacker-server
    # releases the lock.

    def operation_lock(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            coord = coordination.COORDINATOR
            # ensure coordination start
            # NOTE: it is noop if already started.
            coord.start()

            sig = inspect.signature(func)
            call_args = sig.bind(*args, **kwargs).arguments
            inst_id = inst_arg.format(**call_args)
            lock = coord.get_lock(inst_id)

            blocking = False if not delay else 10
            # NOTE: 'with lock' is not used since it can't handle
            # lock failed exception well.
            if not lock.acquire(blocking=blocking):
                LOG.debug("Locking vnfInstance %s failed.", inst_id)
                raise sol_ex.OtherOperationInProgress(inst_id=inst_id)

            try:
                LOG.debug("vnfInstance %s locked.", inst_id)
                return func(*args, **kwargs)
            finally:
                lock.release()

        return wrapper

    return operation_lock
