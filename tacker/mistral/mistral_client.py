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

from mistralclient.api import client as mistral_client


class MistralClient(object):
    """Mistral Client class for NSD"""

    def __init__(self, keystone, auth_token):
        endpoint = keystone.session.get_endpoint(
            service_type='workflowv2', region_name=None)

        self.client = mistral_client.client(auth_token=auth_token,
            mistral_url=endpoint)

    def get_client(self):
        return self.client
