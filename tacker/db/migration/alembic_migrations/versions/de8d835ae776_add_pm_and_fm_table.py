# Copyright 2022 OpenStack Foundation
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

"""add_pm_and_fm_table

Revision ID: de8d835ae776
Revises: 85c06a0714b7
Create Date: 2022-07-21 17:34:45.675428

"""

# flake8: noqa: E402

# revision identifiers, used by Alembic.
revision = 'de8d835ae776'
down_revision = '85c06a0714b7'

from alembic import op
import sqlalchemy as sa


def upgrade(active_plugins=None, options=None):
    op.create_table('AlarmV1',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('managedObjectId', sa.String(length=255), nullable=False),
        sa.Column('vnfcInstanceIds', sa.JSON(), nullable=True),
        sa.Column('rootCauseFaultyResource', sa.JSON(), nullable=True),
        sa.Column('alarmRaisedTime', sa.DateTime(), nullable=False),
        sa.Column('alarmChangedTime', sa.DateTime(), nullable=True),
        sa.Column('alarmClearedTime', sa.DateTime(), nullable=True),
        sa.Column('alarmAcknowledgedTime', sa.DateTime(), nullable=True),
        sa.Column('ackState', sa.Enum(
            'UNACKNOWLEDGED', 'ACKNOWLEDGED',
            name='ackState'), nullable=False),
        sa.Column('perceivedSeverity', sa.Enum(
            'CRITICAL', 'MAJOR', 'MINOR', 'WARNING',
            'INDETERMINATE', 'CLEARED',
            name='perceivedSeverity'), nullable=False),
        sa.Column('eventTime', sa.DateTime(), nullable=False),
        sa.Column('eventType', sa.Enum(
            'COMMUNICATIONS_ALARM', 'PROCESSING_ERROR_ALARM',
            'ENVIRONMENTAL_ALARM', 'QOS_ALARM',
            'EQUIPMENT_ALARM', name='eventType'), nullable=False),
        sa.Column('faultType', sa.String(length=255), nullable=True),
        sa.Column('probableCause', sa.String(length=255), nullable=False),
        sa.Column('isRootCause', sa.Boolean(), nullable=False),
        sa.Column('correlatedAlarmIds', sa.JSON(), nullable=True),
        sa.Column('faultDetails', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table('FmSubscriptionV1',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('filter', sa.JSON(), nullable=True),
        sa.Column('callbackUri', sa.String(length=255), nullable=False),
        sa.Column('authentication', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table('PmJobV2',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('objectType', sa.String(length=32), nullable=False),
        sa.Column('objectInstanceIds', sa.JSON(), nullable=False),
        sa.Column('subObjectInstanceIds', sa.JSON(), nullable=True),
        sa.Column('criteria', sa.JSON(), nullable=False),
        sa.Column('callbackUri', sa.String(length=255), nullable=False),
        sa.Column('reports', sa.JSON(), nullable=True),
        sa.Column('authentication', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )

    op.create_table('PerformanceReportV2',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('jobId', sa.String(length=255), nullable=False),
        sa.Column('entries', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB'
    )
