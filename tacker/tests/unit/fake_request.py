# Copyright (C) 2019 NTT DATA
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


import webob
import webob.request

from tacker import context
from tacker.tests import uuidsentinel
from tacker import wsgi as os_wsgi


class FakeRequestContext(context.ContextBaseWithSession):
    def __init__(self, *args, **kwargs):
        kwargs['auth_token'] = kwargs.get(
            uuidsentinel.user_id, uuidsentinel.project_id)
        super(FakeRequestContext, self).__init__(*args, **kwargs)


class HTTPRequest(webob.Request):

    @classmethod
    def blank(cls, *args, **kwargs):
        kwargs['base_url'] = 'http://localhost/'
        use_admin_context = kwargs.pop(context.get_admin_context(), True)
        out = os_wsgi.Request.blank(*args, **kwargs)
        out.environ['tacker.context'] = FakeRequestContext(
            uuidsentinel.user_id,
            uuidsentinel.project_id,
            is_admin=use_admin_context)
        return out
