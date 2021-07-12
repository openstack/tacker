# Copyright (C) 2021 NEC Corp
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

from tacker.db.db_sqlalchemy import models


def apply_filters(query, filters):
    """Apply filters to a SQLAlchemy query.

    :param query:   The query object to which we apply filters.
    :param filters: A dict or an iterable of dicts, where each one includes
                    the necesary information to create a filter to be applied
                    to the query. There are single  query filters, such as
                    filters = {'model': 'Foo', 'field': 'name', 'op': '==',
                    'value': 'foo'}. And multiple query filters, such as
                    filters = {'and': [
                    {'field': 'name', 'model': 'Foo', 'value': 'foo',
                    'op': '=='},
                    {'field': 'id', 'model': 'Bar', 'value': 'bar',
                    'op': '=='}
                    ]}
    """

    def apply_filter(query, filter):
        value = filter.get('value')
        op = filter.get('op')
        model = getattr(models, filter.get('model'))
        column_attr = getattr(model, filter.get('field'))

        if 'in' == op:
            query = query.filter(column_attr.in_(value))
        elif 'not_in' == op:
            query = query.filter(~column_attr.in_(value))
        elif '!=' == op:
            query = query.filter(column_attr != value)
        elif '>' == op:
            query = query.filter(column_attr > value)
        elif '>=' == op:
            query = query.filter(column_attr >= value)
        elif '<' == op:
            query = query.filter(column_attr < value)
        elif '<=' == op:
            query = query.filter(column_attr <= value)
        elif '==' == op:
            query = query.filter(column_attr == value)
        return query

    if 'and' in filters:
        for filter in filters.get('and'):
            query = apply_filter(query, filter)
    else:
        query = apply_filter(query, filters)
    return query
