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

from oslo_db.sqlalchemy import utils as sqlalchemyutils

import tacker.context


def model_query(context, model, args=None, read_deleted=None,
                project_only=False):
    """Query helper that accounts for context's `read_deleted` field.

    :param context:     TackerContext of the query.
    :param model:       Model to query. Must be a subclass of ModelBase.
    :param args:        Arguments to query. If None - model is used.
    :param read_deleted: If not None, overrides context's read_deleted field.
                        Permitted values are 'no', which does not return
                        deleted values; 'only', which only returns deleted
                        values; and 'yes', which does not filter deleted
                        values.
    :param project_only: If set and context is user-type, then restrict
                        query to match the context's project_id. If set to
                        'allow_none', restriction includes project_id = None.
    """

    query_kwargs = {}
    if read_deleted:
        if 'no' == read_deleted:
            query_kwargs['deleted'] = False
        elif 'only' == read_deleted:
            query_kwargs['deleted'] = True
        elif 'yes' == read_deleted:
            pass
        else:
            raise ValueError(_("Unrecognized read_deleted value '%s'")
                             % read_deleted)

    query = sqlalchemyutils.model_query(
        model, context.session, args, **query_kwargs)

    if tacker.context.is_user_context(context) and project_only:
        query = query.filter_by(tenant_id=context.project_id)

    return query
