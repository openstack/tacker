#!/bin/bash

wk_dir=/tmp/oidc
req_conf=$wk_dir/ssl_csr.conf
ssl_dir=/etc/keycloak/ssl
key_file=$ssl_dir/keycloak.key
csr_file=$ssl_dir/keycloak.csr
crt_file=$ssl_dir/keycloak.crt

k8s_ssl_dir=/etc/kubernetes/pki
k8s_ca_crt=$k8s_ssl_dir/ca.crt
k8s_ca_key=$k8s_ssl_dir/ca.key

# make a directory for storing certificate
mkdir -p $ssl_dir

# generate private key
openssl genrsa -out $key_file 2048

# generate certificate signing request
openssl req -new -key $key_file -out $csr_file -subj "/CN=Keycloak" -config $req_conf

# use Kubernetes’s CA for issuing certificate
openssl x509 -req -in $csr_file -CA $k8s_ca_crt -CAkey $k8s_ca_key -CAcreateserial -out $crt_file -days 365 -extensions v3_req -extfile $req_conf

# add executeable permission to key file
chmod 755 $key_file
