#!/bin/bash

podman run -d \
--net=host \
-e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin \
-e KC_HTTP_PORT=8080 -e KC_HTTPS_PORT=8443 \
-e KC_HTTPS_CERTIFICATE_FILE=/opt/keycloak/conf/keycloak.crt \
-e KC_HTTPS_CERTIFICATE_KEY_FILE=/opt/keycloak/conf/keycloak.key \
-v /etc/keycloak/ssl:/opt/keycloak/conf quay.io/keycloak/keycloak:18.0.2 \
start-dev
