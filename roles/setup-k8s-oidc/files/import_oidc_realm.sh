#!/bin/bash

KEYCLOAK_BASE_URL=https://127.0.0.1:8443

ADMIN_TOKEN=$(curl -k -sS -X POST "${KEYCLOAK_BASE_URL}/realms/master/protocol/openid-connect/token" \
-H 'Content-Type: application/x-www-form-urlencoded' \
-d 'username=admin' \
-d 'password=admin' \
-d 'grant_type=password' \
-d 'client_id=admin-cli' | jq -r .access_token)
if [ $? -ne 0 ]
then
    exit $?
fi

curl -k -L -X POST "${KEYCLOAK_BASE_URL}/admin/realms" \
-H 'Content-Type: application/json' \
-H "Authorization: Bearer $ADMIN_TOKEN" \
-d @"oidc_realm.json"