#!/bin/bash

# Define various file and directory paths
local_cert_dir="${PWD}/etc/ssl/localcerts"
ca_key_file="ca.key"
ca_cert_file="ca.pem"
keycloak_key_file="keycloak.key"
keycloak_cert_file="keycloak.pem"
keycloak_csr_file="keycloak.csr"
keycloak_conf_dir="${PWD}/etc/keycloak/conf"
keycloak_conf_file="keycloak.conf"
keycloak_admin_user="admin"
keycloak_admin_pass="admin"
keycloak_version="26.0.2"
keycloak_http_port="8080"
keycloak_https_port="8443"
keycloak_host="127.0.0.1"
keycloak_realm_file="base_realm.json"
keycloak_realm_default_dir="/opt/keycloak/data/import/example-realm.json"
client_key_file="client.key"
client_cert_file="client.pem"
client_csr_file="client.csr"
tacker_host="127.0.0.1"
tacker_key_file="tacker.key"
tacker_cert_file="tacker.pem"
tacker_csr_file="tacker.csr"
TIME_OUT=600 # approximately 10min
CLIENT_ID='tacker_service'
KEY_PATH="${PWD}/private_key.pem"
CLIENT_SECRET=iIK6lARLzJgoQQyMyoymNYrGTDuR0733S
ISSUER='tacker_service'
SUBJECT='tacker_service'
SCOPE='tacker_scope'
OID_URL=http://${keycloak_host}:${keycloak_http_port}/realms/testrealm/.well-known/openid-configuration
HTTP_ENDPOINT=http://${keycloak_host}:${keycloak_http_port}/realms/testrealm/protocol/openid-connect/token
HTTPS_ENDPOINT=https://${keycloak_host}:${keycloak_https_port}/realms/testrealm/protocol/openid-connect/token

declare -a ENUM_VALUES=(\
"client_secret_post" \
"client_secret_basic" \
"private_key_jwt" \
"client_secret_jwt" \
"tls_client_auth")

# Function to display help
function display_help {
  cat << EOS
Usage: $0 [options]

Description:
This script will allow you to build and start Keycloak Docker with predefined
config pattern.

Available Options:
-h, --help          Show this help message and exit
-n, --no-server     Generate keycloak configuration file and realm.json only
                    without actually starting server

Available Authentication Types:
1. client_secret_post
2. client_secret_basic
3. private_key_jwt
4. client_secret_jwt
5. tls_client_auth

Steps to Run the Script:
1. Run the script with the -h option to display this help message.
2. Select the authentication type from the available options.
3. Enter the required information for the selected authentication type.
4. The script will generate the certificates and Keycloak configuration file.
5. The script will start the Keycloak Docker container.

Note:
Make sure to have Docker installed and running on your system.
Make sure to have the required dependencies installed on your system.
EOS
}

# Function to check if a command exists and handle errors
function check_command {
  local command_to_check="$1"
  local error_message="$2"

  if ! ${command_to_check} > /dev/null 2>&1; then
    echo "${error_message}" >&2
    exit 1
  fi
}


# Function to create certificates
function create_certificates {
  echo "Generating Certificate"
  if check_file "${local_cert_dir}/${keycloak_key_file}"; then
    echo "Certificate will generate"
  else
    return 0
  fi


  openssl genrsa -out "${local_cert_dir}/${ca_key_file}" 4096
  openssl req -new -x509 -key "${local_cert_dir}/${ca_key_file}" \
  -out "${local_cert_dir}/${ca_cert_file}" -days 365 -subj \
  "/C=JP/ST=Tokyo/L=Chiyoda-ku/O=OpenstackORG/CN=root_a.openstack.host"

  cat << EOF > ./extfile
subjectAltName=IP.1:${keycloak_host}
EOF

  openssl genrsa -out "${local_cert_dir}/${keycloak_key_file}" 4096
  openssl req -new -key "${local_cert_dir}/${keycloak_key_file}" \
  -out "${local_cert_dir}/${keycloak_csr_file}" \
  -subj "/C=JP/ST=Tokyo/L=Chiyoda-ku/O=OpenstackORG/CN=${keycloak_host}"
  openssl x509 -req -days 365 -sha384 -CA "${local_cert_dir}/${ca_cert_file}" \
  -CAkey "${local_cert_dir}/${ca_key_file}" \
  -CAcreateserial -extfile ./extfile \
  -in "${local_cert_dir}/${keycloak_csr_file}" \
  -out "${local_cert_dir}/${keycloak_cert_file}"

  rm -f ./extfile

  cat << EOF > ./extfile
subjectAltName=IP.1:${tacker_host}
EOF

  openssl genrsa -out "${local_cert_dir}/${tacker_key_file}" 4096
  openssl req -new -key "${local_cert_dir}/${tacker_key_file}" \
  -out "${local_cert_dir}/${tacker_csr_file}" \
  -subj "/C=JP/ST=Tokyo/L=Chiyoda-ku/O=OpenstackORG/CN=${tacker_host}"
  openssl x509 -req -days 365 -sha384 \
  -CA "${local_cert_dir}/${ca_cert_file}" \
  -CAkey "${local_cert_dir}/${ca_key_file}" \
  -CAcreateserial -extfile ./extfile \
  -in "${local_cert_dir}/${tacker_csr_file}" \
  -out "${local_cert_dir}/${tacker_cert_file}"

  rm -f ./extfile

  openssl genrsa -out "${local_cert_dir}/${client_key_file}" 4096
  openssl req -new -key "${local_cert_dir}/${client_key_file}" \
  -out "${local_cert_dir}/${client_csr_file}" \
  -subj "/C=JP/ST=Tokyo/L=Chiyoda-ku/O=OpenstackORG/CN=client"
  openssl x509 -req -days 365 -sha384 \
  -CA "${local_cert_dir}/${ca_cert_file}" \
  -CAkey "${local_cert_dir}/${ca_key_file}" \
  -CAcreateserial \
  -in "${local_cert_dir}/${client_csr_file}" \
  -out "${local_cert_dir}/${client_cert_file}"

  chmod 644 "${local_cert_dir}/${keycloak_key_file}"

  echo "-------------------------"
  echo ""

}

function base64url_encode {
  echo -n "$1" | base64 -w 0 | tr '/+' '_-' | tr -d '='
}

function generate_uuid {
  if command -v uuidgen > /dev/null; then
    uuidgen
  else
    cat /proc/sys/kernel/random/uuid
  fi
}

# Function to generate client_assertion
function create_client_assertion {
  KEY_TYPE=$1
  AUDIENCE=$2
  # Set create (iat) and expire (exp) times
  CREATE_TIME=$(date +%s)
  EXPIRE_TIME=$((CREATE_TIME + 300))  # Current time + 5 minutes (300 seconds)

  # Generate UUID for jti claim
  JTI=$(generate_uuid)
  # Create JWT header
  if [ "${KEY_TYPE}" = "secret" ]; then
    HEADER='{"alg":"HS256","typ":"JWT"}'
  else
    HEADER='{"alg":"RS256","typ":"JWT"}'
  fi
  HEADER_BASE64=$(base64url_encode "${HEADER}")

  # Create JWT payload
  PAYLOAD='{
  "iss": "'${ISSUER}'",
  "sub": "'${SUBJECT}'",
  "aud": "'${AUDIENCE}'",
  "iat": "'${CREATE_TIME}'",
  "exp": "'${EXPIRE_TIME}'",
  "jti": "'${JTI}'"
  }'

  PAYLOAD_BASE64=$(base64url_encode "${PAYLOAD}")

  # Combine header and payload
  UNSIGNED_TOKEN="${HEADER_BASE64}.${PAYLOAD_BASE64}"
  # Sign the token
  if [ "${KEY_TYPE}" = "secret" ]; then
    # Sign with secret key (HS256)
    hexsecret=$(echo -n "${CLIENT_SECRET}" \
    | xxd -p \
    | paste -sd "")
    SIGNATURE=$(echo -n "${UNSIGNED_TOKEN}" \
    | openssl dgst -sha256 -mac HMAC -macopt hexkey:${hexsecret} -binary \
    | base64 \
    | tr '/+' '_-' \
    | tr -d '=')
  else
    # Sign with private key (RS256)
    SIGNATURE=$(echo -n "${UNSIGNED_TOKEN}" \
    | openssl dgst -sha256 -sign "${KEY_PATH}" \
    | base64 \
    | tr '/+' '_-' \
    | tr -d '=')
  fi

  # Create the complete JWT
  JWT="${UNSIGNED_TOKEN}.${SIGNATURE}"
  echo ${JWT}

}

# Function to generate Keycloak configuration file
function gen_keycloak_conf {
  echo "Creating Keycloak config"
  cat <<-EOF > ${keycloak_conf_file}
hostname=${keycloak_host}
https-certificate-file=\${kc.home.dir}/conf/${keycloak_cert_file}
https-certificate-key-file=\${kc.home.dir}/conf/${keycloak_key_file}
https-trust-store-file=\${kc.home.dir}/conf/${ca_cert_file}
https-client-auth=request
truststore-file-hostname-verification-policy=ANY
EOF

  mv ${keycloak_conf_file} ${keycloak_conf_dir}/${keycloak_conf_file}
  echo "-------------------------"
  echo ""
}

# Function to start Keycloak Docker container
function start_docker {
  echo "Starting Keycloak Server"
  echo ""
  docker stop keycloak && docker rm keycloak
  docker run -d --name keycloak \
  -p ${keycloak_http_port}:8080 \
  -p ${keycloak_https_port}:8443 \
  -e KEYCLOAK_ADMIN=${keycloak_admin_user} \
  -e KEYCLOAK_ADMIN_PASSWORD=${keycloak_admin_pass} \
  -v ${local_cert_dir}/${keycloak_cert_file}:/opt/keycloak/conf/${keycloak_cert_file} \
  -v ${local_cert_dir}/${ca_cert_file}:/opt/keycloak/conf/${ca_cert_file} \
  -v ${local_cert_dir}/${keycloak_key_file}:/opt/keycloak/conf/${keycloak_key_file} \
  -v ${keycloak_conf_dir}/${keycloak_conf_file}:/opt/keycloak/conf/${keycloak_conf_file} \
  -v ${keycloak_conf_dir}/${keycloak_realm_file}:${keycloak_realm_default_dir} \
  quay.io/keycloak/keycloak:${keycloak_version} start-dev --import-realm
}

# Function to print the menu and get user input
function get_auth_type {
  echo "Select the client credential grant flow type for keycloak server :"
  for i in "${!ENUM_VALUES[@]}"; do
    echo "$((i+1)). ${ENUM_VALUES[$i]}"
  done

  while true; do
    read -p "Enter your choice (1-${#ENUM_VALUES[@]}): " choice
    if [[ "$choice" =~ ^[1-${#ENUM_VALUES[@]}]$ ]]; then
      return $((choice-1))
    else
      echo "Invalid choice. Please try again."
    fi
  done
}

# Function to check if a file exists and handle user input
function check_file {
  local filename="$1"

  if [ -e "${filename}" ]; then
    echo "Certificate files already exist."
    read -p "Overwrite? (y/n) [default:n]: " choice
    case "${choice}" in
      y|Y )
        echo "${filename} will overwrite"
        return 0
        ;;
      * )
        echo "Existing file will be used"
        echo "-------------------------"
        echo ""
        return 1
        ;;
    esac
  else
    return 0
  fi
}

# Function to replace a string in a file
function replace_string {
  local replace_file="$1"
  local search_string="$2"
  local replace_string="$3"
  local info_message="$4"

  if [ ! -f "${replace_file}" ]; then
    echo "Error: File '${replace_file}' not found." >&2
    return 1
  fi

  sed -i "s|${search_string}|${replace_string}|g" "${replace_file}"

  if [ $? -eq 0 ]; then
    echo "${info_message}"
    echo "-------------------------"
    echo ""
  else
    echo "Error: Failed to replace string in file." >&2
    return 1
  fi
}


# Function to set OpenStack parameters in the Keycloak realm file
function set_os_param {
  local realm_file="${keycloak_conf_dir}/${keycloak_realm_file}"

  read -p "Enter OS username[default:nfv_user]: " os_username
  replace_string ${realm_file} "os_tacker_username" ${os_username:-nfv_user} \
  "Successfully set OS username with ${os_username:-nfv_user}";

  while true; do
    read -p "Enter OS user id: " os_user_id
    if [ -n "${os_user_id}" ]; then
      replace_string ${realm_file} "os_tacker_user_id" ${os_user_id} \
      "Successfully set OS user id with ${os_user_id}"
      break
    else
      echo "You have to set OS user id"
    fi
  done

  read -p "Enter OS user domain id[default:default]: " os_user_domain_id
  replace_string ${realm_file} "os_tacker_user_domain_id" \
  ${os_user_domain_id:-default} \
  "Successfully set OS user domain id with ${os_user_domain_id:-default}";

  read -p "Enter OS user domain name[default:Default]: " os_user_domain_name
  replace_string ${realm_file} "os_tacker_user_domain_name" \
  ${os_user_domain_name:-default} \
  "Successfully set OS user domain name with ${os_user_domain_name:-default}";

  read -p "Enter OS project name[default:nfv]: " os_project_name
  replace_string ${realm_file} "os_tacker_project_name" ${os_project_name:-nfv} \
  "Successfully set OS project name with ${os_project_name:-nfv}";

  while true; do
    read -p "Enter OS project id: " os_project_id
    if [ -n "${os_project_id}" ]; then
      replace_string ${realm_file} "os_tacker_project_id" ${os_project_id} \
      "Successfully set OS Project id with ${os_project_id}"; break
    else
    echo "You have to set OS user id"
    fi
  done

  read -p "Enter OS project domain id[default:default]: " os_project_domain_id
  replace_string ${realm_file} "os_tacker_project_domain_id" \
  ${os_project_domain_id:-default} \
  "Successfully set OS project domain id with ${os_project_domain_id:-default}";

  read -p "Enter OS project domain name[default:Default]: " os_project_domain_name
  replace_string ${realm_file} "os_tacker_project_domain_name" \
  ${os_project_domain_id:-Default} \
  "Successfully set OS project domain name with ${os_project_domain_id:-default}";

  read -p "Enter OS user roles[default:admin,member,reader]: " os_user_roles
  replace_string ${realm_file} "os_tacker_roles" \
  ${os_user_roles:-'admin,member,reader'} \
  "Successfully set OS user roles with ${os_user_roles:-'admin,member,reader'}";

}

function wait_server {
  # Main loop to check API
  echo -en Waiting Keycloak Server to start......
  while [ ${TIME_OUT} -ge 0 ]; do

    # Get HTTP response code
    RESPONSE=$(echo -en $(curl -I ${OID_URL} 2>/dev/null \
    | head -n 1 \
    | awk -F" " '{print $2}')OK)

    if [ "${RESPONSE}" = "200OK" ]; then
      echo ""
      echo -e "Keycloak server is started successfully."
      break
    else
      for X in '-' '/' '|' '\'; do echo -en "\b\b\b[$X]"
      TIME_OUT=$((TIME_OUT - 1))
      sleep 1
      done
    fi
  done

  if [ ${TIME_OUT} -le 0 ]; then
    echo ""
    echo "Time out for waiting the server to get started."
    echo "Use \"docker logs\" or \"docker ps\" command to check server status."
    exit 1
  fi
}

# Function to generate private key and set public cert to realm.json
function set_private_key {
  echo "Generating private key ${KEY_PATH}"
  openssl req -x509 -newkey rsa:2048 -keyout ${KEY_PATH} \
  -out ./cert.pem -days 365 -nodes -subj "/CN=YourCommonName" \
  -config <(echo "[req]"; echo "distinguished_name=req_distinguished_name"; \
  echo "[req_distinguished_name]")

  echo "-------------------------"
  echo ""

  pub_cert=$(awk 'NR>2 { sub(/\r/, ""); printf "%s",last} { last=$0 }' \
  ./cert.pem)

  sed -i "s|os_public_cert_string|${pub_cert}|g" ${realm_file};
}


# Main function
function main {
  AUDIENCE=${HTTP_ENDPOINT}
  base_command="curl -s -X POST ${HTTP_ENDPOINT} \
  -d 'scope=${SCOPE}' -d 'client_id=${SUBJECT}' \
  -d 'grant_type=client_credentials'"
  no_server=false
  # Create necessary directories and set permissions
  while getopts ":hn-:" opt; do
    case ${opt} in
      h)
        display_help
        exit 0
        ;;
      n)
        no_server=true
        ;;
      -)
        case "${OPTARG}" in
          help)
            display_help
            exit 0
            ;;
          no-server)
            no_server=true
            ;;
          *)
            echo "Unknown option --${OPTARG}"
            exit 1
            ;;
        esac
        ;;
      ?)
        echo "Unknown option: -${OPTARG}"
        exit 1
        ;;
      esac
  done

  if ${no_server}; then
    echo ""
  else
    check_command "docker ps" \
    "Docker not found or permission denied. Check docker again."
  fi
  mkdir -p ${local_cert_dir}
  mkdir -p ${keycloak_conf_dir}
  chmod 755 ${keycloak_conf_dir}

  # Main script
  set +e
  get_auth_type
  selected_index=$?
  auth=${ENUM_VALUES[${selected_index}]}
  echo "You selected: ${auth}"
  echo "-------------------------"
  echo ""
  cp -f "${PWD}/${keycloak_realm_file}" "${keycloak_conf_dir}/${keycloak_realm_file}"
  local realm_file="${keycloak_conf_dir}/${keycloak_realm_file}"
  read -p "Enable Oauth2 certificate-bounded token? (y/n) [default:n] :" thumb
  origin_string='"tls.client.certificate.bound.access.tokens": "false"'
  replace_string='"tls.client.certificate.bound.access.tokens": "true"'
  case ${thumb} in
    y|Y )
      AUDIENCE=${HTTPS_ENDPOINT}
      replace_string ${realm_file} "${origin_string}" "${replace_string}" \
      "Oauth2 certificate-bounded token is enabled."
      base_command="curl -s -X POST ${HTTPS_ENDPOINT} \
      -d 'scope=${SCOPE}' -d 'client_id=${SUBJECT}' \
      -d 'grant_type=client_credentials' \
      --cacert ${local_cert_dir}/${ca_cert_file} \
      --cert ${local_cert_dir}/${client_cert_file} \
      --key ${local_cert_dir}/${client_key_file}"
      ;;
    * )
      echo "Oauth2 certificate-bounded token is disabled";
      echo "-------------------------"
      echo ""
      ;;
  esac

  # Copy the appropriate realm file based on the selected auth type
  case "${auth}" in
  "client_secret_post" )
    replace_string "${realm_file}" "client_credential_grant_flow_type" \
    "client-secret" "Set auth type to client secret post."
    LAST_MSG="client_secret\t\t: ${CLIENT_SECRET}"
    base_command="${base_command} \
    -d 'client_secret=${CLIENT_SECRET}'"
    ;;
  "client_secret_basic" )
    replace_string "${realm_file}" "client_credential_grant_flow_type" \
    "client-secret" "Set auth type to client secret basic."
    LAST_MSG="client_secret\t\t: ${CLIENT_SECRET}"
    base_command="${base_command} \
    -u '${SUBJECT}:${CLIENT_SECRET}'"
    ;;
  "private_key_jwt" )
    sed -i 's|"use.jwks.url": "true"|"use.jwks.url": "false"|g' ${realm_file}
    replace_string "${keycloak_conf_dir}/${keycloak_realm_file}" \
    "client_credential_grant_flow_type" \
    "client-jwt" "Set auth type to private key signed JWT."
    LAST_MSG="private_key\t\t: ${KEY_PATH}"
    set_private_key
    CLIENT_ASSERTION=$(create_client_assertion privatekey ${AUDIENCE})
    base_command="${base_command} \
    -d 'client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer' \
    -d 'client_assertion=${CLIENT_ASSERTION}'"
    ;;
  "client_secret_jwt" )
    replace_string "${keycloak_conf_dir}/${keycloak_realm_file}" \
    "client_credential_grant_flow_type" "client-secret-jwt" \
    "Set auth type to client secret signed JWT."
    LAST_MSG="client_secret\t\t: ${CLIENT_SECRET}"
    CLIENT_ASSERTION=$(create_client_assertion secret ${AUDIENCE})
    base_command="${base_command} \
    -d 'client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer' \
    -d 'client_assertion=${CLIENT_ASSERTION}'"
    ;;
  "tls_client_auth" )
    replace_string "${keycloak_conf_dir}/${keycloak_realm_file}" \
    "client_credential_grant_flow_type" "client-x509" \
    "Set auth type to tls client authentication."
    ;;
  esac
  set_os_param
  create_certificates
  gen_keycloak_conf
  if ${no_server}; then
    echo "***********************************"
    echo "A realm configuration file has been generated without starting the Keycloak server."
  else
    start_docker
    wait_server
  fi

  echo "###################################"
  echo -e "HTTP endpoint\t\t: "${HTTP_ENDPOINT}
  echo -e "HTTPS endpoint\t\t: ${HTTPS_ENDPOINT}"
  echo -e "client_id\t\t: tacker_service, tacker_api_proj, tacker_api_domain"
  echo -e ${LAST_MSG}
  echo -e "scope\t\t\t: project_scope, domain_scope"
  echo "* If you want to use other Keycloak server, import this realm.json"
  echo -e "realm JSON file\t\t: "${keycloak_conf_dir}/${keycloak_realm_file}
  echo "* Use the following keys and certificates for Tacker and client"
  echo -e "RootCA certificate\t: "${local_cert_dir}/${ca_cert_file}
  echo -e "Tacker certificate\t: "${local_cert_dir}/${tacker_cert_file}
  echo -e "Tacker key\t\t: "${local_cert_dir}/${tacker_key_file}
  echo -e "client certificate\t: "${local_cert_dir}/${client_cert_file}
  echo -e "client key\t\t: "${local_cert_dir}/${client_cert_file}
  echo ""
  echo "------------------------------------"
  echo "You can try getting a token using following command"
  echo ""
  echo ${base_command}
  echo "###################################"
}

# Run the main function
main "$@"