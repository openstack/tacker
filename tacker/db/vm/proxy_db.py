# Copyright 2014 Intel Corporation.
# Copyright 2014 Isaku Yamahata <isaku.yamahata at intel com>
#                               <isaku.yamahata at gmail com>
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

import sqlalchemy as sa

from tacker.db import db_base
from tacker.db import model_base


class ProxyMgmtPort(model_base.BASE):
    device_id = sa.Column(sa.String(255), primary_key=True)
    port_id = sa.Column(sa.String(36), nullable=False)
    dst_transport_url = sa.Column(sa.String(255))
    svr_proxy_id = sa.Column(sa.String(36))
    svr_ns_proxy_id = sa.Column(sa.String(36))
    clt_proxy_id = sa.Column(sa.String(36))
    clt_ns_proxy_id = sa.Column(sa.String(36))


class ProxyServicePort(model_base.BASE):
    service_instance_id = sa.Column(sa.String(255), primary_key=True)
    svr_proxy_id = sa.Column(sa.String(36))
    svr_ns_proxy_id = sa.Column(sa.String(36))
    clt_proxy_id = sa.Column(sa.String(36))
    clt_ns_proxy_id = sa.Column(sa.String(36))


class RpcProxyDb(db_base.CommonDbMixin):
    def _make_proxy_mgmt_port(self, proxy_mgmt_port):
        key_list = ('device_id', 'port_id', 'dst_transport_url',
                    'svr_proxy_id', 'svr_ns_proxy_id',
                    'clt_proxy_id', 'clt_ns_proxy_id')
        return dict((key, getattr(proxy_mgmt_port, key)) for key in key_list)

    def _make_proxy_service_port(self, proxy_service_port):
        key_list = ('service_instance_id', 'svr_proxy_id', 'svr_ns_proxy_id',
                    'clt_proxy_id', 'clt_ns_proxy_id')
        return dict((key, getattr(proxy_service_port, key))
                    for key in key_list)

    def create_proxy_mgmt_port(self, context, device_id, port_id,
                               dst_transport_url,
                               svr_proxy_id, svr_ns_proxy_id,
                               clt_proxy_id, clt_ns_proxy_id):
        with context.session.begin(subtransactions=True):
            proxy_mgmt_port = ProxyMgmtPort(
                device_id=device_id, port_id=port_id,
                dst_transport_url=dst_transport_url,
                svr_proxy_id=svr_proxy_id, svr_ns_proxy_id=svr_ns_proxy_id,
                clt_proxy_id=clt_proxy_id, clt_ns_proxy_id=clt_ns_proxy_id)
            context.session.add(proxy_mgmt_port)

    def delete_proxy_mgmt_port(self, context, port_id):
        with context.session.begin(subtransactions=True):
            context.session.query(ProxyMgmtPort).filter_by(
                port_id=port_id).delete()

    def get_proxy_mgmt_port(self, context, device_id):
        with context.session.begin(subtransactions=True):
            proxy_mgmt_port = context.session.query(ProxyMgmtPort).filter_by(
                device_id=device_id).one()
        return self._make_proxy_mgmt_port(proxy_mgmt_port)

    def create_proxy_service_port(self, context, service_instance_id,
                                  svr_proxy_id, svr_ns_proxy_id,
                                  clt_proxy_id, clt_ns_proxy_id):
        with context.session.begin(subtransactions=True):
            proxy_service_port = ProxyServicePort(
                service_instance_id=service_instance_id,
                svr_proxy_id=svr_proxy_id, svr_ns_proxy_id=svr_ns_proxy_id,
                clt_proxy_id=clt_proxy_id, clt_ns_proxy_id=clt_ns_proxy_id)
            context.session.add(proxy_service_port)

    def delete_proxy_service_port(self, context, service_instance_id):
        with context.session.begin(subtransactions=True):
            context.session.query(ProxyServicePort).filter_by(
                service_instance_id=service_instance_id).delete()

    def get_proxy_service_port(self, context, service_instance_id):
        with context.session.begin(subtransactions=True):
            proxy_service_port = context.session.query(
                ProxyServicePort).filter_by(
                    service_instance_id=service_instance_id).one()
        return self._make_proxy_service_port(proxy_service_port)
