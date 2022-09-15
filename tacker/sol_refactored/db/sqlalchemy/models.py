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


import sqlalchemy as sa

from tacker.db import model_base


class LccnSubscriptionV2(model_base.BASE):
    """Type: LccnSubscription

    NFV-SOL 003
    - v3.3.1 5.5.2.16 (API version: 2.0.0)
    """

    __tablename__ = 'LccnSubscriptionV2'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    filter = sa.Column(sa.JSON(), nullable=True)
    callbackUri = sa.Column(sa.String(255), nullable=False)
    # NOTE: 'authentication' attribute is not included in the
    #       original 'LccnSubscription' data type definition.
    authentication = sa.Column(sa.JSON(), nullable=True)
    verbosity = sa.Column(sa.Enum('FULL', 'SHORT', create_constraint=True,
                                  validate_strings=True), nullable=False)


class VnfInstanceV2(model_base.BASE):
    """Type: VnfInstance

    NFV-SOL 003
    - v3.3.1 5.5.2.2 (API version: 2.0.0)
    """

    __tablename__ = 'VnfInstanceV2'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    vnfInstanceName = sa.Column(sa.String(255), nullable=True)
    vnfInstanceDescription = sa.Column(sa.Text(), nullable=True)
    vnfdId = sa.Column(sa.String(255), nullable=False)
    vnfProvider = sa.Column(sa.String(255), nullable=False)
    vnfProductName = sa.Column(sa.String(255), nullable=False)
    vnfSoftwareVersion = sa.Column(sa.String(255), nullable=False)
    vnfdVersion = sa.Column(sa.String(255), nullable=False)
    vnfConfigurableProperties = sa.Column(sa.JSON(), nullable=True)
    vimConnectionInfo = sa.Column(sa.JSON(), nullable=True)
    instantiationState = sa.Column(sa.Enum(
        'NOT_INSTANTIATED', 'INSTANTIATED', create_constraint=True,
        validate_strings=True), nullable=False)
    instantiatedVnfInfo = sa.Column(sa.JSON(), nullable=True)
    metadata__ = sa.Column("metadata", sa.JSON(), nullable=True)
    extensions = sa.Column(sa.JSON(), nullable=True)


class VnfLcmOpOccV2(model_base.BASE):
    """Type: VnfLcmOpOcc

    NFV-SOL 003
    - v3.3.1 5.5.2.13 (API version: 2.0.0)
    """

    __tablename__ = 'VnfLcmOpOccV2'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    operationState = sa.Column(sa.Enum(
        'STARTING', 'PROCESSING', 'COMPLETED', 'FAILED_TEMP',
        'FAILED', 'ROLLING_BACK', 'ROLLED_BACK',
        create_constraint=True, validate_strings=True), nullable=False)
    stateEnteredTime = sa.Column(sa.DateTime(), nullable=False)
    startTime = sa.Column(sa.DateTime(), nullable=False)
    vnfInstanceId = sa.Column(sa.String(255), nullable=False)
    grantId = sa.Column(sa.String(255), nullable=True)
    operation = sa.Column(sa.Enum(
        'INSTANTIATE', 'SCALE', 'SCALE_TO_LEVEL', 'CHANGE_FLAVOUR',
        'TERMINATE', 'HEAL', 'OPERATE', 'CHANGE_EXT_CONN',
        'MODIFY_INFO', 'CREATE_SNAPSHOT', 'REVERT_TO_SNAPSHOT',
        'CHANGE_VNFPKG', create_constraint=True, validate_strings=True),
        nullable=False)
    isAutomaticInvocation = sa.Column(sa.Boolean, nullable=False)
    operationParams = sa.Column(sa.JSON(), nullable=True)
    isCancelPending = sa.Column(sa.Boolean, nullable=False)
    cancelMode = sa.Column(sa.Enum(
        'GRACEFUL', 'FORCEFUL', create_constraint=True, validate_strings=True),
        nullable=True)
    error = sa.Column(sa.JSON(), nullable=True)
    resourceChanges = sa.Column(sa.JSON(), nullable=True)
    changedInfo = sa.Column(sa.JSON(), nullable=True)
    changedExtConnectivity = sa.Column(sa.JSON(), nullable=True)
    modificationsTriggeredByVnfPkgChange = sa.Column(sa.JSON(), nullable=True)
    vnfSnapshotInfoId = sa.Column(sa.String(255), nullable=True)


class GrantV1(model_base.BASE):
    """Type: Grant

    NFV-SOL 003
    - v3.3.1 9.5.2.3 (API version: 1.4.0)
    """

    __tablename__ = 'GrantV1'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    vnfInstanceId = sa.Column(sa.String(255), nullable=False)
    vnfLcmOpOccId = sa.Column(sa.String(255), nullable=False)
    vimConnectionInfo = sa.Column(sa.JSON(), nullable=True)
    zones = sa.Column(sa.JSON(), nullable=True)
    zoneGroups = sa.Column(sa.JSON(), nullable=True)
    addResources = sa.Column(sa.JSON(), nullable=True)
    tempResources = sa.Column(sa.JSON(), nullable=True)
    removeResources = sa.Column(sa.JSON(), nullable=True)
    updateResources = sa.Column(sa.JSON(), nullable=True)
    vimAssets = sa.Column(sa.JSON(), nullable=True)
    extVirtualLinks = sa.Column(sa.JSON(), nullable=True)
    extManagedVirtualLinks = sa.Column(sa.JSON(), nullable=True)
    additionalParams = sa.Column(sa.JSON(), nullable=True)


class GrantRequestV1(model_base.BASE):
    """Type: GrantRequest

    NFV-SOL 003
    - v3.3.1 9.5.2.2 (API version: 1.4.0)
    """

    __tablename__ = 'GrantRequestV1'
    vnfInstanceId = sa.Column(sa.String(255), nullable=False)
    vnfLcmOpOccId = sa.Column(sa.String(255), nullable=False, primary_key=True)
    vnfdId = sa.Column(sa.String(255), nullable=False)
    dstVnfdId = sa.Column(sa.String(255), nullable=True)
    flavourId = sa.Column(sa.String(255), nullable=True)
    operation = sa.Column(sa.Enum(
        'INSTANTIATE', 'SCALE', 'SCALE_TO_LEVEL', 'CHANGE_FLAVOUR',
        'TERMINATE', 'HEAL', 'OPERATE', 'CHANGE_EXT_CONN',
        'CREATE_SNAPSHOT', 'REVERT_TO_SNAPSHOT', 'CHANGE_VNFPKG',
        create_constraint=True, validate_strings=True),
        nullable=False)
    isAutomaticInvocation = sa.Column(sa.Boolean, nullable=False)
    instantiationLevelId = sa.Column(sa.String(255), nullable=True)
    addResources = sa.Column(sa.JSON(), nullable=True)
    tempResources = sa.Column(sa.JSON(), nullable=True)
    removeResources = sa.Column(sa.JSON(), nullable=True)
    updateResources = sa.Column(sa.JSON(), nullable=True)
    placementConstraints = sa.Column(sa.JSON(), nullable=True)
    vimConstraints = sa.Column(sa.JSON(), nullable=True)
    additionalParams = sa.Column(sa.JSON(), nullable=True)


class AlarmV1(model_base.BASE):
    """Type: Alarm

    NFV-SOL 003
    - v3.3.1 7.5.2.4 (API version: 1.3.0)
    """

    __tablename__ = 'AlarmV1'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    managedObjectId = sa.Column(sa.String(255), nullable=False)
    vnfcInstanceIds = sa.Column(sa.JSON(), nullable=True)
    rootCauseFaultyResource = sa.Column(sa.JSON(), nullable=True)
    alarmRaisedTime = sa.Column(sa.DateTime(), nullable=False)
    alarmChangedTime = sa.Column(sa.DateTime(), nullable=True)
    alarmClearedTime = sa.Column(sa.DateTime(), nullable=True)
    alarmAcknowledgedTime = sa.Column(sa.DateTime(), nullable=True)
    ackState = sa.Column(sa.Enum(
        'UNACKNOWLEDGED', 'ACKNOWLEDGED', create_constraint=True,
        validate_strings=True), nullable=False)
    perceivedSeverity = sa.Column(sa.Enum(
        'CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'INDETERMINATE', 'CLEARED',
        create_constraint=True, validate_strings=True), nullable=False)
    eventTime = sa.Column(sa.DateTime(), nullable=False)
    eventType = sa.Column(sa.Enum(
        'COMMUNICATIONS_ALARM', 'PROCESSING_ERROR_ALARM',
        'ENVIRONMENTAL_ALARM', 'QOS_ALARM', 'EQUIPMENT_ALARM',
        create_constraint=True, validate_strings=True), nullable=False)
    faultType = sa.Column(sa.String(255), nullable=True)
    probableCause = sa.Column(sa.String(255), nullable=False)
    isRootCause = sa.Column(sa.Boolean, nullable=False)
    correlatedAlarmIds = sa.Column(sa.JSON(), nullable=True)
    faultDetails = sa.Column(sa.JSON(), nullable=True)


class FmSubscriptionV1(model_base.BASE):
    """Type: FmSubscription

    NFV-SOL 003
    - v3.3.1 7.5.2.3 (API version: 1.3.0)
    """

    __tablename__ = 'FmSubscriptionV1'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    filter = sa.Column(sa.JSON(), nullable=True)
    callbackUri = sa.Column(sa.String(255), nullable=False)
    # NOTE: 'authentication' attribute is not included in the
    #       original 'FmSubscription' data type definition.
    authentication = sa.Column(sa.JSON(), nullable=True)


class PmJobV2(model_base.BASE):
    """Type: PmJob

    NFV-SOL 003
    - v3.3.1 6.5.2.7 (API version: 2.1.0)
    """

    __tablename__ = 'PmJobV2'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    objectType = sa.Column(sa.String(32), nullable=False)
    objectInstanceIds = sa.Column(sa.JSON(), nullable=False)
    subObjectInstanceIds = sa.Column(sa.JSON(), nullable=True)
    criteria = sa.Column(sa.JSON(), nullable=False)
    callbackUri = sa.Column(sa.String(255), nullable=False)
    reports = sa.Column(sa.JSON(), nullable=True)
    # NOTE: 'authentication' attribute is not included in the
    #       original 'PmJob' data type definition.
    authentication = sa.Column(sa.JSON(), nullable=True)
    # NOTE: 'metadata' attribute is not included in the
    #       original 'PmJob' data type definition.
    metadata__ = sa.Column("metadata", sa.JSON(), nullable=True)


class PerformanceReportV2(model_base.BASE):
    """Type: Report

    NFV-SOL 003
    - v3.3.1 6.5.2.10 (API version: 2.1.0)
    """
    __tablename__ = 'PerformanceReportV2'
    id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    jobId = sa.Column(sa.String(255), nullable=False, primary_key=False)
    entries = sa.Column(sa.JSON(), nullable=False)
