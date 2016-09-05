#    Copyright 2012 OpenStack Foundation
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
from keystoneauth1.identity import v3
from keystoneauth1 import session


class Token(object):
    def __init__(self, username, password, project_name,
                 auth_url, user_domain_name, project_domain_name):
        self.username = username
        self.password = password
        self.auth_url = auth_url
        self.project_name = project_name
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name

    def create_token(self):
        auth = v3.Password(auth_url=self.auth_url,
                           username=self.username,
                           password=self.password,
                           project_name=self.project_name,
                           user_domain_name=self.user_domain_name,
                           project_domain_name=self.project_domain_name)
        sess = session.Session(auth=auth)
        token_id = sess.auth.get_token(sess)
        return token_id
