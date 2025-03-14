#!/bin/bash

PROGNAME=$(basename $0)
VERSION="0.0.1"

UUID="[A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f]-[A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f]-[A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f]-[A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f]-[A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f][A-F0-9a-f]"
HTTP_METHOD="+(GET|HEAD|POST|PUT|DELETE|CONNECT|OPTIONS|TRACE|PATCH)"

function usage() {
  echo "Usage: $PROGNAME <command> [<args>]"
  echo
  echo "Options:"
  echo "  -h, --help      show this help message and exit"
  echo "  -v, --version   print version"
  echo
  echo "Commands:"
  echo "  vim"
  echo "  vnfpkgm"
  echo "  vnflcm"
  echo "  vnffm"
  echo "  vnfpm"
  echo
  echo "Configuration:"
  echo
  echo "  Set credentials and access information as environment variables according to an authentication method"
  echo
  echo "  Examples:"
  echo
  echo '    client_secret_basic'
  echo '      export TACKER_AUTH_URL="http://127.0.0.1:8080/realms/testrealm/protocol/openid-connect/token"'
  echo '      export TACKER_CLIENT_ID="tacker_api_proj"'
  echo '      export TACKER_CLIENT_SECRET="<secret>"'
  echo '      export TACKER_AUTH_TYPE="client_secret_basic"'
  echo '      export TACKER_OAUTH2_SCOPE="tacker_scope"'
  echo '      export TACKER_URL=http://127.0.0.1:9890'
  echo ''
  echo '    client_secret_post'
  echo '      export TACKER_AUTH_URL="http://127.0.0.1:8080/realms/testrealm/protocol/openid-connect/token"'
  echo '      export TACKER_CLIENT_ID="tacker_api_proj"'
  echo '      export TACKER_CLIENT_SECRET="<secret>"'
  echo '      export TACKER_AUTH_TYPE="client_secret_post"'
  echo '      export TACKER_OAUTH2_SCOPE="tacker_scope"'
  echo '      export TACKER_URL=http://127.0.0.1:9890'
  echo ''
  echo '    private_key_jwt'
  echo '      export TACKER_AUTH_URL="http://127.0.0.1:8080/realms/testrealm/protocol/openid-connect/token"'
  echo '      export TACKER_CLIENT_ID="tacker_api_proj"'
  echo '      export TACKER_JWT_KEY="/opt/stack/workspace/ext_oauth2/keycloak/script/private_key.pem"'
  echo '      export TACKER_AUTH_TYPE="private_key_jwt"'
  echo '      export TACKER_OAUTH2_SCOPE="tacker_scope"'
  echo '      export TACKER_URL=http://127.0.0.1:9890'
  echo ''
  echo '    client_secret_jwt'
  echo '      export TACKER_AUTH_URL="http://127.0.0.1:8080/realms/testrealm/protocol/openid-connect/token"'
  echo '      export TACKER_CLIENT_ID="tacker_api_proj"'
  echo '      export TACKER_CLIENT_SECRET="<secret>"'
  echo '      export TACKER_AUTH_TYPE="client_secret_jwt"'
  echo '      export TACKER_OAUTH2_SCOPE="tacker_scope"'
  echo '      export TACKER_URL=http://127.0.0.1:9890'
  echo ''
  echo '    tls_client_auth'
  echo '      export TACKER_AUTH_URL="https://127.0.0.1:8443/realms/testrealm/protocol/openid-connect/token"'
  echo '      export TACKER_CLIENT_ID="tacker_api_proj"'
  echo '      export TACKER_AUTH_TYPE="tls_client_auth"'
  echo '      export TACKER_OAUTH2_SCOPE="tacker_scope"'
  echo '      export TACKER_CACERT="path/to/ca.pem"'
  echo '      export TACKER_CLIENT_CERT="path/to/client.pem"'
  echo '      export TACKER_CLIENT_KEY="path/to/client.key"'
  echo '      export TACKER_URL=https://127.0.0.1:9890'
  echo
}

function vim::usage() {
  echo "Usage: $PROGNAME vim <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  register"
  echo "  list"
  echo "  show"
  echo "  update"
  echo "  delete"
}

function vim::register::usage() {
  echo "Usage: $PROGNAME vim register [-h] --config-file <file>"
  echo
  echo "Register a new VIM"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --config-file <file>"
  echo "                        YAML file with VIM configuration parameters"
  echo
}

function vim::list::usage() {
  echo "Usage: $PROGNAME vim list [-h]"
  echo
  echo "List VIMs that belong to a given tenant"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vim::show::usage() {
  echo "Usage: $PROGNAME vim show [-h] <vim>"
  echo
  echo "Display VIM details"
  echo
  echo "positional arguments:"
  echo "  <vim>         VIM to display (ID)"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vim::update::usage() {
  echo "Usage: $PROGNAME vim update [-h] <vim> --config-file <file>"
  echo
  echo "Update VIM"
  echo
  echo "positional arguments:"
  echo "  <vim>          ID of vim to update"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --config-file <file>"
  echo "                        YAML file with VIM configuration parameters for update"
  echo
}

function vim::delete::usage() {
  echo "Usage: $PROGNAME vim delete [-h] <vim> [<vim> ...]"
  echo
  echo "Delete VIM(s)"
  echo
  echo "positional arguments:"
  echo "  <vim>          vim(s) to delete (ID)"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpkgm::usage() {
  echo "Usage: $PROGNAME vnfpkgm <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  create"
  echo "  upload"
  echo "  download"
  echo "  artifact-download"
  echo "  list"
  echo "  show"
  echo "  update"
  echo "  delete"
  echo
}

function vnfpkgm::create::usage() {
  echo "Usage: $PROGNAME vnfpkgm create [-h] [--param-file <param-file>]"
  echo
  echo "Create a new VNF Package"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify create request parameters in a json file"
  echo
}

function vnfpkgm::upload::usage() {
  echo "Usage: $PROGNAME vnfpkgm upload [-h] --path <file> <vnf-package>"
  echo
  echo "Upload VNF Package"
  echo
  echo "positional arguments:"
  echo "  <vnf-package>"
  echo "                        VNF package ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --path <file>"
  echo "                        upload VNF CSAR package from local zip file"
  echo
}

function vnfpkgm::download::usage() {
  echo "Usage: $PROGNAME vnfpkgm download [-h] [--file <file>] <vnf-package>"
  echo
  echo "Download VNF package contents of an on-boarded VNF package"
  echo
  echo "positional arguments:"
  echo "  <vnf-package>"
  echo "                        VNF package ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --file <FILE>"
  echo "                        Local file to save downloaded VNF Package data. If this is not specified"
  echo "                        data will be saved as <vnf-package>.zip"
  echo
  echo
}

function vnfpkgm::artifact_download::usage() {
  echo "Usage: $PROGNAME vnfpkgm artifact-download [-h] --file <file> --artifact-path <artifact-path> <vnf-package>"
  echo
  echo "Download VNF package artifact of an on-boarded VNF package"
  echo
  echo "positional arguments:"
  echo "  <vnf-package>"
  echo "                        VNF package ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --file <FILE>"
  echo "                        Local file to save downloaded artifact data"
  echo "  --artifact-path <artifact-path>"
  echo "                        The artifact file's path"
  echo
}

function vnfpkgm::list::usage() {
  echo "Usage: $PROGNAME vnfpkgm list [-h]"
  echo
  echo "List VNF Packages"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpkgm::show::usage() {
  echo "Usage: $PROGNAME vnfpkgm show [-h] <vnf-package>"
  echo
  echo "Show VNF Package Details"
  echo
  echo "positional arguments:"
  echo "  <vnf-package>"
  echo "                        VNF package ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpkgm::update::usage() {
  echo "Usage: $PROGNAME vnfpkgm update [-h] --param-file <param-file> <vnf-package>"
  echo
  echo "Update information about an individual VNF package"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify update request parameters in a json file"
  echo
}

function vnfpkgm::delete::usage() {
  echo "Usage: $PROGNAME vnfpkgm delete [-h] <vnf-package> [<vnf-package> ...]"
  echo
  echo "Delete VNF Package"
  echo
  echo "positional arguments:"
  echo "  <vnf-package>"
  echo "                        Vnf package(s) ID to delete"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnflcm::usage() {
  echo "Usage: $PROGNAME vnflcm <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  create"
  echo "  instanatiate"
  echo "  list"
  echo "  show"
  echo "  terminate"
  echo "  delete"
  echo "  heal"
  echo "  update"
  echo "  scale"
  echo "  change-ext-conn"
  echo "  change-vnfpkg"
  echo "  versions"
  echo "  op"
  echo "  subsc"
}

function vnflcm::create::usage() {
  echo "Usage: $PROGNAME vnflcm create [-h] --param-file <param-file>"
  echo
  echo "Create a new VNF Instance"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify create request parameters in a json file"
  echo
}

function vnflcm::instantiate::usage() {
  echo "Usage: $PROGNAME vnflcm instantiate [-h] --param-file <param-file> <vnf-instance>"
  echo
  echo "Instantiate a VNF Instance"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to instantiate"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify instantiate request parameters in a json file"
  echo
}

function vnflcm::list::usage() {
  echo "Usage: $PROGNAME vnflcm list [-h]"
  echo
  echo "List VNF Instances"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnflcm::show::usage() {
  echo "Usage: $PROGNAME vnflcm show [-h] <vnf-instance>"
  echo
  echo "Display VNF Instance details"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to display"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnflcm::terminate::usage() {
  echo "Usage: $PROGNAME vnflcm terminate [-h] --param-file <param-file> <vnf-instance>"
  echo
  echo "Terminate a VNF Instance"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to terminate"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify terminate request parameters in a json file"
  echo
}

function vnflcm::delete::usage() {
  echo "Usage: $PROGNAME vnflcm delete [-h] <vnf-instance> [<vnf-instance> ...]"
  echo
  echo "Delete VNF Instance(s)"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID(s) to delete"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnflcm::heal::usage() {
  echo "Usage: $PROGNAME vnflcm heal [-h] --param-file <param-file> <vnf-instance>"
  echo
  echo "Heal a VNF Instance"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to heal"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify heal request parameters in a json file"
  echo
}

function vnflcm::update::usage() {
  echo "Usage: $PROGNAME vnflcm update [-h] --param-file <param-file> <vnf-instance>"
  echo
  echo "Update a VNF Instance"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to update"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify update request parameters in a json file"
  echo
}

function vnflcm::scale::usage() {
  echo "Usage: $PROGNAME vnflcm scale [-h] --param-file <param-file> <vnf-instance>"
  echo
  echo "Scale a VNF Instance"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to scale"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify scale request parameters in a json file"
  echo
}

function vnflcm::change_ext_conn::usage() {
  echo "Usage: $PROGNAME vnflcm change-ext-conn [-h] --param-file <param-file> <vnf-instance>"
  echo
  echo "Change External VNF Connectivity"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to Change External VNF Connectivity"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify change-ext-conn request parameters in a json file"
  echo
}

function vnflcm::change_vnfpkg::usage() {
  echo "Usage: $PROGNAME vnflcm change-vnfpkg [-h] --param-file <param-file> <vnf-instance>"
  echo
  echo "Change Current VNF Package"
  echo
  echo "positional arguments:"
  echo "  <vnf-instance>"
  echo "                        VNF instance ID to Change Current VNF Package"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify change-vnfpkg request parameters in a json file"
  echo
}

function vnflcm::versions::usage() {
  echo "Usage: $PROGNAME vnflcm versions [-h]"
  echo
  echo "Show VnfLcm Api versions"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function op::usage() {
  echo "Usage: $PROGNAME vnflcm op <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  rollback"
  echo "  retry"
  echo "  fail"
  echo "  list"
  echo "  show"
  echo
}

function op::rollback::usage() {
  echo "Usage: $PROGNAME vnflcm op rollback [-h] <vnf-lcm-op-occ-id>"
  echo
  echo "Rollback LCM Operation Occurrence"
  echo
  echo "positional arguments:"
  echo "  <vnf-lcm-op-occ-id>"
  echo "                        VNF lifecycle management operation occurrence ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function op::retry::usage() {
  echo "Usage: $PROGNAME vnflcm op retry [-h] <vnf-lcm-op-occ-id>"
  echo
  echo "Retry LCM Operation Occurrence"
  echo
  echo "positional arguments:"
  echo "  <vnf-lcm-op-occ-id>"
  echo "                        VNF lifecycle management operation occurrence ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function op::fail::usage() {
  echo "Usage: $PROGNAME vnflcm op fail [-h] <vnf-lcm-op-occ-id>"
  echo
  echo "Fail LCM Operation Occurrence"
  echo
  echo "positional arguments:"
  echo "  <vnf-lcm-op-occ-id>"
  echo "                        VNF lifecycle management operation occurrence ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function op::list::usage() {
  echo "Usage: $PROGNAME vnflcm op list [-h]"
  echo
  echo "List LCM Operation Occurrences"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function op::show::usage() {
  echo "Usage: $PROGNAME vnflcm op show [-h] <vnf-lcm-op-occ-id>"
  echo
  echo "Display LCM Operation Occurrence details"
  echo
  echo "positional arguments:"
  echo "  <vnf-lcm-op-occ-id>"
  echo "                        VNF lifecycle management operation occurrence ID"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function subsc::usage() {
  echo "Usage: $PROGNAME vnflcm subsc <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  create"
  echo "  list"
  echo "  show"
  echo "  delete"
  echo
}

function subsc::create::usage() {
  echo "Usage: $PROGNAME vnflcm subsc create [-h] --param-file <param-file>"
  echo
  echo "Create a new Lccn Subscription"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify create request parameters in a json file"
  echo
}

function subsc::list::usage() {
  echo "Usage: $PROGNAME vnflcm subsc list [-h]"
  echo
  echo "List Lccn Subscriptions"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function subsc::show::usage() {
  echo "Usage: $PROGNAME vnflcm subsc show [-h] <subscription-id>"
  echo
  echo "Display Lccn Subscription details"
  echo
  echo "positional arguments:"
  echo "  <subscription-id>"
  echo "                        Lccn Subscription ID to display"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function subsc::delete::usage() {
  echo "Usage: $PROGNAME vnflcm subsc delete [-h] <subscription-id> [<subscription-id> ...]"
  echo
  echo "Delete Lccn Subscription(s)"
  echo
  echo "positional arguments:"
  echo "  <subscription-id>"
  echo "                        Lccn Subscription ID(s) to delete"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnffm::usage() {
  echo "Usage: $PROGNAME vnffm <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  alarm"
  echo "  sub"
  echo
}

function vnffm::alarm::usage() {
  echo "Usage: $PROGNAME vnffm alarm <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  list"
  echo "  show"
  echo "  update"
  echo
}

function vnffm::alarm::list::usage() {
  echo "Usage: $PROGNAME vnffm alarm list [-h]"
  echo
  echo "List VNF FM alarms"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnffm::alarm::show::usage() {
  echo "Usage: $PROGNAME vnffm alarm show [-h] <vnf-fm-alarm-id>"
  echo
  echo "Display VNF FM alarm details"
  echo
  echo "positional arguments:"
  echo "  <vnf-fm-alarm-id>"
  echo "                        VNF FM alarm ID to display"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnffm::alarm::update::usage() {
  echo "Usage: $PROGNAME vnffm alarm update [-h] --param-file <param-file> <vnf-fm-alarm-id>"
  echo
  echo "Update information about an individual VNF FM alarm"
  echo
  echo "positional arguments:"
  echo "  <vnf-fm-alarm-id>"
  echo "                        VNF FM alarm ID to update"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify update request parameters in a json file"
  echo
}

function vnffm::sub::usage() {
  echo "Usage: $PROGNAME vnffm sub <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  create"
  echo "  list"
  echo "  show"
  echo "  delete"
}

function vnffm::sub::create::usage() {
  echo "Usage: $PROGNAME vnffm sub create [-h] --param-file <param-file>"
  echo
  echo "Create a new VNF FM subscription"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify create VNF FM subscription request parameters in a json file"
  echo
}

function vnffm::sub::list::usage() {
  echo "Usage: $PROGNAME vnffm sub list [-h]"
  echo
  echo "List VNF FM subscriptions"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnffm::sub::show::usage() {
  echo "Usage: $PROGNAME vnffm sub show [-h] <vnf-fm-sub-id>"
  echo
  echo "Display VNF FM subscription details"
  echo
  echo "positional arguments:"
  echo "  <vnf-fm-sub-id>"
  echo "                        VNF FM subscription ID to display"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnffm::sub::delete::usage() {
  echo "Usage: $PROGNAME vnffm sub delete [-h] <vnf-fm-sub-id> [<vnf-fm-sub-id> ...]"
  echo
  echo "Delete VNF FM subscription(s)"
  echo
  echo "positional arguments:"
  echo "  <vnf-fm-sub-id>"
  echo "                        VNF FM subscription ID(s) to delete"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpm::usage() {
  echo "Usage: $PROGNAME vnfpm <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  job"
  echo "  report-show"
  echo "  threshold"
  echo
}

function vnfpm::job::usage() {
  echo "Usage: $PROGNAME vnfpm job <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  create"
  echo "  update"
  echo "  list"
  echo "  show"
  echo "  delete"
  echo
}

function vnfpm::job::create::usage() {
  echo "Usage: $PROGNAME vnfpm job create [-h] --param-file <param-file>"
  echo
  echo "Create a new VNF PM job"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify create VNF PM job request parameters in a json file"
  echo
}

function vnfpm::job::update::usage() {
  echo "Usage: $PROGNAME vnfpm job update [-h] --param-file <param-file> <vnf-pm-job-id>"
  echo
  echo "Update information about an individual VNF PM job"
  echo
  echo "positional arguments:"
  echo "  <vnf-pm-job-id>"
  echo "                        VNF PM job ID to update"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify update PM job request parameters in a json file"
  echo
}

function vnfpm::job::list::usage() {
  echo "Usage: $PROGNAME vnfpm job list [-h]"
  echo
  echo "List VNF PM jobs"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpm::job::show::usage() {
  echo "Usage: $PROGNAME vnfpm job show [-h] <vnf-pm-job-id>"
  echo
  echo "Display VNF PM job details"
  echo
  echo "positional arguments:"
  echo "  <vnf-pm-job-id>"
  echo "                        VNF PM job ID to display"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpm::job::delete::usage() {
  echo "Usage: $PROGNAME vnfpm job delete [-h] <vnf-pm-job-id> [<vnf-pm-job-id> ...]"
  echo
  echo "Delete VNF PM job(s)"
  echo
  echo "positional arguments:"
  echo "  <vnf-pm-job-id>"
  echo "                        VNF PM job ID(s) to delete"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify delete request parameters in a json file"
  echo
}

function vnfpm::report_show::usage() {
  echo "Usage: $PROGNAME vnfpm report-show [-h] <vnf-pm-job-id> <vnf-pm-report-id>"
  echo
  echo "Display VNF PM report details"
  echo
  echo "positional arguments:"
  echo "  <vnf-pm-job-id>"
  echo "                        VNF PM job id where the VNF PM report is located"
  echo "  <vnf-pm-report-id>"
  echo "                        VNF PM report ID to display"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpm::threshold::usage() {
  echo "Usage: $PROGNAME vnfpm threshold <command> [<args>]"
  echo
  echo "Options:"
  echo "  h-, --help   show this help message and exit"
  echo
  echo "Commands:"
  echo "  create"
  echo "  update"
  echo "  list"
  echo "  show"
  echo "  delete"
  echo
}

function vnfpm::threshold::create::usage() {
  echo "Usage: $PROGNAME vnfpm threshold create [-h] --param-file <param-file>"
  echo
  echo "Create a new VNF PM threshold"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify create request parameters in a json file"
  echo
}

function vnfpm::threshold::update::usage() {
  echo "Usage: $PROGNAME vnfpm threshold update [-h] --param-file <param-file> <vnf-pm-threshold-id>"
  echo
  echo "Update information about an individual VNF PM threshold"
  echo
  echo "positional arguments:"
  echo "  <vnf-pm-threshold-id>"
  echo "                        VNF PM threshold ID to update"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo "  --param-file <param-file>"
  echo "                        specify update PM threshold request parameters in a json file"
  echo
}

function vnfpm::threshold::list::usage() {
  echo "Usage: $PROGNAME vnfpm threshold list [-h]"
  echo
  echo "List VNF PM thresholds"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpm::threshold::show::usage() {
  echo "Usage: $PROGNAME vnfpm threshold show [-h] <vnf-pm-threshold-id>"
  echo
  echo "Display VNF PM threshold details"
  echo
  echo "positional arguments:"
  echo "  <vnf-pm-threshold-id>"
  echo "                        VNF PM threshold ID to display"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vnfpm::threshold::delete::usage() {
  echo "Usage: $PROGNAME vnfpm threshold delete [-h] <vnf-pm-threshold-id> [<vnf-pm-threshold-id> ...]"
  echo
  echo "Delete VNF PM threshold(s)"
  echo
  echo "positional arguments:"
  echo "  <vnf-pm-threshold-id>"
  echo "                        VNF PM threshold ID(s) to delete"
  echo
  echo "Options:"
  echo "  -h, --help            show this help message and exit"
  echo
}

function vim() {
  case $1 in
  -h | --help)
    vim::usage
    exit 0
    ;;
  register)
    shift
    vim::register "${@}"
    exit 0
    ;;
  list)
    shift
    vim::list "${@}"
    exit 0
    ;;
  show)
    shift
    vim::show "${@}"
    exit 0
    ;;
  update)
    shift
    vim::update "${@}"
    exit 0
    ;;
  delete)
    shift
    vim::delete "${@}"
    exit 0
    ;;
  *)
    vim::usage
    exit 1
    ;;
  esac
}

function vim::register() {
  case $1 in
  -h | --help)
    vim::register::usage
    exit 0
    ;;
  --config-file)
    config_file="$2"
    shift
    shift
    ;;
  esac

  if [[ -z "${config_file}" ]]; then
    vim::register::usage
    exit 1
  fi

  exec_curl POST /v1.0/vims -d @${config_file}
}

function vim::list() {
  case $1 in
  -h | --help)
    vim::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /v1.0/vims
}

function vim::show() {
  case $1 in
  -h | --help)
    vim::show::usage
    exit 0
    ;;
  ${UUID})
    vim_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${vim_id}" ]]; then
    vim::show::usage
    exit 1
  fi

  exec_curl GET /v1.0/vims/${vim_id}
}

function vim::update() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vim::update::usage
      exit 0
      ;;
    --config-file)
      config_file="$2"
      shift
      shift
      ;;
    ${UUID})
      vim_id="${1}"
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${config_file}" || -z "${vim_id}" ]]; then
    vim::update::usage
    exit 1
  fi

  exec_curl PUT /v1.0/vims/${vim_id} -d @${config_file}
}

function vim::delete() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vim::delete::usage
      exit 0
      ;;
    ${UUID})
      vim_ids+=("${1}")
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${vim_ids}" ]]; then
    vim::delete::usage
    exit 1
  fi

  for vim_id in "${vim_ids[@]}"; do
    exec_curl DELETE /v1.0/vims/${vim_id}
  done
}

function vnfpkgm() {
  case $1 in
  -h | --help)
    vnfpkgm::usage
    exit 0
    ;;
  create)
    shift
    vnfpkgm::create "${@}"
    exit 0
    ;;
  upload)
    shift
    vnfpkgm::upload "${@}"
    exit 0
    ;;
  download)
    shift
    vnfpkgm::download "${@}"
    exit 0
    ;;
  artifact-download)
    shift
    vnfpkgm::artifact_download "${@}"
    exit 0
    ;;
  list)
    shift
    vnfpkgm::list "${@}"
    exit 0
    ;;
  show)
    shift
    vnfpkgm::show "${@}"
    exit 0
    ;;
  update)
    shift
    vnfpkgm::update "${@}"
    exit 0
    ;;
  delete)
    shift
    vnfpkgm::delete "${@}"
    exit 0
    ;;
  *)
    vnfpkgm::usage
    exit 1
    ;;
  esac
}

function vnfpkgm::create() {
  case $1 in
  -h | --help)
    vnfpkgm::create::usage
    exit 0
    ;;
  --param-file)
    param="@${2}"
    shift
    shift
    ;;
  esac

  exec_curl POST /vnfpkgm/v1/vnf_packages -d ${param:="{}"}
}

function vnfpkgm::upload() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpkgm::upload::usage
      exit 0
      ;;
    ${UUID})
      pkg_id="${1}"
      shift
      ;;
    --path)
      pkg_path="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${pkg_id}" || -z "${pkg_path}" || "${pkg_path##*.}" != "zip" ]]; then
    vnfpkgm::upload::usage
    exit 1
  fi

  exec_curl PUT /vnfpkgm/v1/vnf_packages/${pkg_id}/package_content -H "Content-Type: application/zip" -F "vnf_package_content=@${pkg_path}"
}

function vnfpkgm::download() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpkgm::download::usage
      exit 0
      ;;
    ${UUID})
      pkg_id="${1}"
      shift
      ;;
    --file)
      file="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${pkg_id}" ]]; then
    vnfpkgm::download::usage
    exit 1
  fi

  exec_curl GET /vnfpkgm/v1/vnf_packages/${pkg_id}/package_content -o ${file:="${pkg_id}.zip"}
}

function vnfpkgm::artifact_download() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpkgm::artifact_download::usage
      exit 0
      ;;
    ${UUID})
      pkg_id="${1}"
      shift
      ;;
    --file)
      file="${2}"
      shift
      shift
      ;;
    --artifact-path)
      artifact_path="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${pkg_id}" || -z "${artifact_path}" || -z "${file}" ]]; then
    vnfpkgm::artifact_download::usage
    exit 1
  fi

  exec_curl GET /vnfpkgm/v1/vnf_packages/${pkg_id}/artifacts/${artifact_path} -o ${file}
}

function vnfpkgm::list() {
  case $1 in
  -h | --help)
    vnfpkgm::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnfpkgm/v1/vnf_packages
}

function vnfpkgm::show() {
  case $1 in
  -h | --help)
    vnfpkgm::show::usage
    exit 0
    ;;
  ${UUID})
    pkg_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${pkg_id}" ]]; then
    vnfpkgm::show::usage
    exit 1
  fi

  exec_curl GET /vnfpkgm/v1/vnf_packages/${pkg_id}
}

function vnfpkgm::update() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpkgm::update::usage
      exit 0
      ;;
    ${UUID})
      pkg_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${pkg_id}" || -z "${param}" ]]; then
    vnfpkgm::update::usage
    exit 1
  fi

  exec_curl PATCH /vnfpkgm/v1/vnf_packages/${pkg_id} -d @"${param}"
}

function vnfpkgm::delete() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpkgm::delete::usage
      exit 0
      ;;
    ${UUID})
      pkg_ids+=("${1}")
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${pkg_ids}" ]]; then
    vnfpkgm::delete::usage
    exit 1
  fi

  for pkg_id in "${pkg_ids[@]}"; do
    exec_curl DELETE /vnfpkgm/v1/vnf_packages/${pkg_id}
  done
}

function vnflcm() {
  case $1 in
  -h | --help)
    vnflcm::usage
    exit 0
    ;;
  op)
    shift
    op "${@}"
    exit 0
    ;;
  subsc)
    shift
    subsc "${@}"
    exit 0
    ;;
  create)
    shift
    vnflcm::create "${@}"
    exit 0
    ;;
  instantiate)
    shift
    vnflcm::instantiate "${@}"
    exit 0
    ;;
  list)
    shift
    vnflcm::list "${@}"
    exit 0
    ;;
  show)
    shift
    vnflcm::show "${@}"
    exit 0
    ;;
  terminate)
    shift
    vnflcm::terminate "${@}"
    exit 0
    ;;
  delete)
    shift
    vnflcm::delete "${@}"
    exit 0
    ;;
  heal)
    shift
    vnflcm::heal "${@}"
    exit 0
    ;;
  update)
    shift
    vnflcm::update "${@}"
    exit 0
    ;;
  scale)
    shift
    vnflcm::scale "${@}"
    exit 0
    ;;
  change-ext-conn)
    shift
    vnflcm::change_ext_conn "${@}"
    exit 0
    ;;
  change-vnfpkg)
    shift
    vnflcm::change_vnfpkg "${@}"
    exit 0
    ;;
  versions)
    shift
    vnflcm::versions "${@}"
    exit 0
    ;;
  *)
    vnflcm::usage
    exit 1
    ;;
  esac
}

function vnflcm::create() {
  case $1 in
  -h | --help)
    vnflcm::create::usage
    exit 0
    ;;
  --param-file)
    param="${2}"
    shift
    shift
    ;;
  esac

  if [[ -z "${param}" ]]; then
    vnflcm::create::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_instances -H "version: 2.0.0" -d @${param}
}

function vnflcm::instantiate() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::instantiate::usage
      exit 0
      ;;
    ${UUID})
      inst_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_id}" || -z "${param}" ]]; then
    vnflcm::instantiate::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_instances/${inst_id}/instantiate -H "version: 2.0.0" -d @${param}
}

function vnflcm::list() {
  case $1 in
  -h | --help)
    vnflcm::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnflcm/v2/vnf_instances -H "version: 2.0.0"
}

function vnflcm::show() {
  case $1 in
  -h | --help)
    vnflcm::show::usage
    exit 0
    ;;
  ${UUID})
    inst_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${inst_id}" ]]; then
    vnflcm::show::usage
    exit 1
  fi

  exec_curl GET /vnflcm/v2/vnf_instances/${inst_id} -H "version: 2.0.0"
}

function vnflcm::terminate() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::terminate::usage
      exit 0
      ;;
    ${UUID})
      inst_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_id}" || -z "${param}" ]]; then
    vnflcm::terminate::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_instances/${inst_id}/terminate -H "version: 2.0.0" -d @${param}
}

function vnflcm::delete() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::delete::usage
      exit 0
      ;;
    ${UUID})
      inst_ids+=("${1}")
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_ids}" ]]; then
    vnflcm::delete::usage
    exit 1
  fi

  for inst_id in "${inst_ids[@]}"; do
    exec_curl DELETE /vnflcm/v2/vnf_instances/${inst_id} -H "version: 2.0.0"
  done
}

function vnflcm::heal() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::heal::usage
      exit 0
      ;;
    ${UUID})
      inst_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_id}" || -z "${param}" ]]; then
    vnflcm::heal::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_instances/${inst_id}/heal -H "version: 2.0.0" -d @${param}
}

function vnflcm::update() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::update::usage
      exit 0
      ;;
    ${UUID})
      inst_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_id}" || -z "${param}" ]]; then
    vnflcm::update::usage
    exit 1
  fi

  exec_curl PATCH /vnflcm/v2/vnf_instances/${inst_id} -H "version: 2.0.0" -d @${param}
}

function vnflcm::scale() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::scale::usage
      exit 0
      ;;
    ${UUID})
      inst_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_id}" || -z "${param}" ]]; then
    vnflcm::scale::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_instances/${inst_id}/scale -H "version: 2.0.0" -d @${param}
}

function vnflcm::change_ext_conn() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::change_ext_conn::usage
      exit 0
      ;;
    ${UUID})
      inst_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_id}" || -z "${param}" ]]; then
    vnflcm::change_ext_conn::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_instances/${inst_id}/change_ext_conn -H "version: 2.0.0" -d @${param}
}

function vnflcm::change_vnfpkg() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnflcm::change_vnfpkg::usage
      exit 0
      ;;
    ${UUID})
      inst_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${inst_id}" || -z "${param}" ]]; then
    vnflcm::change_vnfpkg::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_instances/${inst_id}/change_vnfpkg -H "version: 2.0.0" -d @${param}
}

function vnflcm::versions() {
  case $1 in
  -h | --help)
    vnflcm::versions::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnflcm/v2/api_versions
}

function op() {
  case $1 in
  -h | --help)
    op::usage
    exit 0
    ;;
  rollback)
    shift
    op::rollback "${@}"
    exit 0
    ;;
  retry)
    shift
    op::retry "${@}"
    exit 0
    ;;
  fail)
    shift
    op::fail "${@}"
    exit 0
    ;;
  list)
    shift
    op::list "${@}"
    exit 0
    ;;
  show)
    shift
    op::show "${@}"
    exit 0
    ;;
  *)
    op::usage
    exit 1
    ;;
  esac
}

function op::rollback() {
  case $1 in
  -h | --help)
    op::rollback::usage
    exit 0
    ;;
  ${UUID})
    opocc_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${opocc_id}" ]]; then
    op::rollback::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_lcm_op_occs/${opocc_id}/rollback -H "version: 2.0.0"
}

function op::retry() {
  case $1 in
  -h | --help)
    op::retry::usage
    exit 0
    ;;
  ${UUID})
    opocc_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${opocc_id}" ]]; then
    op::retry::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_lcm_op_occs/${opocc_id}/retry -H "version: 2.0.0"
}

function op::fail() {
  case $1 in
  -h | --help)
    op::fail::usage
    exit 0
    ;;
  ${UUID})
    opocc_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${opocc_id}" ]]; then
    op::fail::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/vnf_lcm_op_occs/${opocc_id}/fail -H "version: 2.0.0"
}

function op::list() {
  case $1 in
  -h | --help)
    op::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnflcm/v2/vnf_lcm_op_occs -H "version: 2.0.0"
}

function op::show() {
  case $1 in
  -h | --help)
    op::show::usage
    exit 0
    ;;
  ${UUID})
    opocc_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${opocc_id}" ]]; then
    op::show::usage
    exit 1
  fi

  exec_curl GET /vnflcm/v2/vnf_lcm_op_occs/${opocc_id} -H "version: 2.0.0"
}

function subsc() {
  case $1 in
  -h | --help)
    subsc::usage
    exit 0
    ;;
  create)
    shift
    subsc::create "${@}"
    exit 0
    ;;
  list)
    shift
    subsc::list "${@}"
    exit 0
    ;;
  show)
    shift
    subsc::show "${@}"
    exit 0
    ;;
  delete)
    shift
    subsc::delete "${@}"
    exit 0
    ;;
  *)
    subsc::usage
    exit 1
    ;;
  esac
}

function subsc::create() {
  case $1 in
  -h | --help)
    subsc::create::usage
    exit 0
    ;;
  --param-file)
    param="${2}"
    shift
    shift
    ;;
  esac

  if [[ -z "${param}" ]]; then
    subsc::create::usage
    exit 1
  fi

  exec_curl POST /vnflcm/v2/subscriptions -H "version: 2.0.0" -d@${param}
}

function subsc::list() {
  case $1 in
  -h | --help)
    subsc::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnflcm/v2/subscriptions -H "version: 2.0.0"
}

function subsc::show() {
  case $1 in
  -h | --help)
    subsc::show::usage
    exit 0
    ;;
  ${UUID})
    subsc_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${subsc_id}" ]]; then
    subsc::show::usage
    exit 1
  fi

  exec_curl GET /vnflcm/v2/subscriptions/${subsc_id} -H "version: 2.0.0"
}

function subsc::delete() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      subsc::delete::usage
      exit 0
      ;;
    ${UUID})
      subsc_ids+=("${1}")
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${subsc_ids}" ]]; then
    subsc::delete::usage
    exit 1
  fi

  for subsc_id in "${subsc_ids[@]}"; do
    exec_curl DELETE /vnflcm/v2/subscriptions/${subsc_id} -H "version: 2.0.0"
  done
}

function vnffm() {
  case $1 in
  -h | --help)
    vnffm::usage
    exit 0
    ;;
  alarm)
    shift
    vnffm::alarm "${@}"
    exit 0
    ;;
  sub)
    shift
    vnffm::sub "${@}"
    exit 0
    ;;
  *)
    vnffm::usage
    exit 1
    ;;
  esac
}

function vnffm::alarm() {
  case $1 in
  -h | --help)
    vnffm::alarm::usage
    exit 0
    ;;
  list)
    shift
    vnffm::alarm::list "${@}"
    exit 0
    ;;
  show)
    shift
    vnffm::alarm::show "${@}"
    exit 0
    ;;
  update)
    shift
    vnffm::alarm::update "${@}"
    exit 0
    ;;
  *)
    vnffm::alarm::usage
    exit 1
    ;;
  esac
}

function vnffm::alarm::list() {
  case $1 in
  -h | --help)
    vnffm::alarm::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnffm/v1/alarms -H "version: 1.3.0"
}

function vnffm::alarm::show() {
  case $1 in
  -h | --help)
    vnffm::alarm::show::usage
    exit 0
    ;;
  ${UUID})
    alarm_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${alarm_id}" ]]; then
    vnffm::alarm::show::usage
    exit 1
  fi

  exec_curl GET /vnffm/v1/alarms/${alarm_id} -H "version: 1.3.0"
}

function vnffm::alarm::update() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnffm::alarm::update::usage
      exit 0
      ;;
    ${UUID})
      alarm_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    esac
  done

  if [[ -z "${param}" ]]; then
    vnffm::alarm::update::usage
    exit 1
  fi

  exec_curl PATCH /vnffm/v1/alarms/${alarm_id} -H "version: 1.3.0" -d@${param}
}

function vnffm::sub() {
  case $1 in
  -h | --help)
    vnffm::sub::usage
    exit 0
    ;;
  create)
    shift
    vnffm::sub::create "${@}"
    exit 0
    ;;
  list)
    shift
    vnffm::sub::list "${@}"
    exit 0
    ;;
  show)
    shift
    vnffm::sub::show "${@}"
    exit 0
    ;;
  delete)
    shift
    vnffm::sub::delete "${@}"
    exit 0
    ;;
  *)
    vnffm::sub::usage
    exit 1
    ;;
  esac
}

function vnffm::sub::create() {
  case $1 in
  -h | --help)
    vnffm::sub::create::usage
    exit 0
    ;;
  --param-file)
    param="${2}"
    shift
    shift
    ;;
  esac

  if [[ -z "${param}" ]]; then
    vnffm::sub::create::usage
    exit 1
  fi

  exec_curl POST /vnffm/v1/subscriptions -H "version: 1.3.0" -d@${param}
}

function vnffm::sub::list() {
  case $1 in
  -h | --help)
    vnffm::sub::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnffm/v1/subscriptions -H "version: 1.3.0"
}

function vnffm::sub::show() {
  case $1 in
  -h | --help)
    vnffm::sub::show::usage
    exit 0
    ;;
  ${UUID})
    sub_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${sub_id}" ]]; then
    vnffm::sub::show::usage
    exit 1
  fi

  exec_curl GET /vnffm/v1/subscriptions/${sub_id} -H "version: 1.3.0"
}

function vnffm::sub::delete() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnffm::sub::delete::usage
      exit 0
      ;;
    ${UUID})
      sub_ids+=("${1}")
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${sub_ids}" ]]; then
    vnffm::sub::delete::usage
    exit 1
  fi

  for sub_id in "${sub_ids[@]}"; do
    exec_curl DELETE /vnffm/v1/subscriptions/${sub_id} -H "version: 1.3.0"
  done
}

function vnfpm() {
  case $1 in
  -h | --help)
    vnfpm::usage
    exit 0
    ;;
  job)
    shift
    vnfpm::job "${@}"
    exit 0
    ;;
  report-show)
    shift
    vnfpm::report_show "${@}"
    exit 0
    ;;
  threshold)
    shift
    vnfpm::threshold "${@}"
    exit 0
    ;;
  *)
    vnfpm::usage
    exit 1
    ;;
  esac
}

function vnfpm::job() {
  case $1 in
  -h | --help)
    vnfpm::job::usage
    exit 0
    ;;
  create)
    shift
    vnfpm::job::create "${@}"
    exit 0
    ;;
  update)
    shift
    vnfpm::job::update "${@}"
    exit 0
    ;;
  list)
    shift
    vnfpm::job::list "${@}"
    exit 0
    ;;
  show)
    shift
    vnfpm::job::show "${@}"
    exit 0
    ;;
  delete)
    shift
    vnfpm::job::delete "${@}"
    exit 0
    ;;
  *)
    vnfpm::job::usage
    exit 1
    ;;
  esac
}

function vnfpm::job::create() {
  case $1 in
  -h | --help)
    vnfpm::job::create::usage
    exit 0
    ;;
  --param-file)
    param="${2}"
    shift
    shift
    ;;
  esac

  if [[ -z "${param}" ]]; then
    vnfpm::job::create::usage
    exit 1
  fi

  exec_curl POST /vnfpm/v2/pm_jobs -H "version: 2.1.0" -d@${param}
}

function vnfpm::job::update() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpm::job::update::usage
      exit 0
      ;;
    ${UUID})
      job_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    esac
  done

  if [[ -z "${param}" || -z "${job_id}" ]]; then
    vnfpm::job::update::usage
    exit 1
  fi

  exec_curl PATCH /vnfpm/v2/pm_jobs/${job_id} -H "version: 2.1.0" -d@${param}
}

function vnfpm::job::list() {
  case $1 in
  -h | --help)
    vnfpm::job::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnfpm/v2/pm_jobs -H "version: 2.1.0"
}

function vnfpm::job::show() {
  case $1 in
  -h | --help)
    vnfpm::job::show::usage
    exit 0
    ;;
  ${UUID})
    job_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${job_id}" ]]; then
    vnfpm::job::show::usage
    exit 1
  fi

  exec_curl GET /vnfpm/v2/pm_jobs/${job_id} -H "version: 2.1.0"
}

function vnfpm::job::delete() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpm::job::delete::usage
      exit 0
      ;;
    ${UUID})
      job_ids+=("${1}")
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${job_ids}" ]]; then
    vnfpm::job::delete::usage
    exit 1
  fi

  for job_id in "${job_ids[@]}"; do
    exec_curl DELETE /vnfpm/v2/pm_jobs/${job_id} -H "version: 2.1.0"
  done
}

function vnfpm::report_show() {
  case $1 in
  -h | --help)
    vnfpm::report_show::usage
    exit 0
    ;;
  ${UUID})
    job_id="${1}"
    shift
    ;;
  esac

  case $1 in
  -h | --help)
    vnfpm::report_show::usage
    exit 0
    ;;
  ${UUID})
    report_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${job_id}" || -z "${report_id}" ]]; then
    vnfpm::report_show::usage
    exit 1
  fi

  exec_curl GET /vnfpm/v2/pm_jobs/${job_id}/reports/${report_id} -H "version: 2.1.0"
}

function vnfpm::threshold() {
  case $1 in
  -h | --help)
    vnfpm::threshold::usage
    exit 0
    ;;
  create)
    shift
    vnfpm::threshold::create "${@}"
    exit 0
    ;;
  update)
    shift
    vnfpm::threshold::update "${@}"
    exit 0
    ;;
  list)
    shift
    vnfpm::threshold::list "${@}"
    exit 0
    ;;
  show)
    shift
    vnfpm::threshold::show "${@}"
    exit 0
    ;;
  delete)
    shift
    vnfpm::threshold::delete "${@}"
    exit 0
    ;;
  *)
    vnfpm::threshold::usage
    exit 1
    ;;
  esac
}

function vnfpm::threshold::create() {
  case $1 in
  -h | --help)
    vnfpm::threshold::create::usage
    exit 0
    ;;
  --param-file)
    param="${2}"
    shift
    shift
    ;;
  esac

  if [[ -z "${param}" ]]; then
    vnfpm::threshold::create::usage
    exit 1
  fi

  exec_curl POST /vnfpm/v2/thresholds -H "version: 2.1.0" -d@${param}
}

function vnfpm::threshold::update() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpm::threshold::update::usage
      exit 0
      ;;
    ${UUID})
      thr_id="${1}"
      shift
      ;;
    --param-file)
      param="${2}"
      shift
      shift
      ;;
    esac
  done

  if [[ -z "${param}" || -z ${thr_id} ]]; then
    vnfpm::threshold::update::usage
    exit 1
  fi

  exec_curl PATCH /vnfpm/v2/thresholds/${thr_id} -H "version: 2.1.0" -d@${param}
}

function vnfpm::threshold::list() {
  case $1 in
  -h | --help)
    vnfpm::threshold::list::usage
    exit 0
    ;;
  esac

  exec_curl GET /vnfpm/v2/thresholds -H "version: 2.1.0"
}

function vnfpm::threshold::show() {
  case $1 in
  -h | --help)
    vnfpm::threshold::show::usage
    exit 0
    ;;
  ${UUID})
    thr_id="${1}"
    shift
    ;;
  esac

  if [[ -z "${thr_id}" ]]; then
    vnfpm::threshold::show::usage
    exit 1
  fi

  exec_curl GET /vnfpm/v2/thresholds/${thr_id} -H "version: 2.1.0"
}

function vnfpm::threshold::delete() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    -h | --help)
      vnfpm::threshold::delete::usage
      exit 0
      ;;
    ${UUID})
      thr_ids+=("${1}")
      shift
      ;;
    *)
      break
      ;;
    esac
  done

  if [[ -z "${thr_ids}" ]]; then
    vnfpm::threshold::delete::usage
    exit 1
  fi

  for thr_id in "${thr_ids[@]}"; do
    exec_curl DELETE /vnfpm/v2/thresholds/${thr_id} -H "version: 2.1.0"
  done
}

function authenticate::create_client_assertion() {
  # Usage: authenticate::create_client_assertion [secret|key]

  key_type="${1}"

  # Set create (iat) and expire (exp) times
  create_time=$(date +%s)
  expire_time=$((create_time + 300)) # Current time + 5 minutes (300 seconds)

  # Generate UUID for jti claim
  jti=$(generate_uuid)

  # Create JWT header
  if [ "${key_type}" = "secret" ]; then
    header='{"alg":"HS256","typ":"JWT"}'
  else
    header='{"alg":"RS256","typ":"JWT"}'
  fi
  header_b64=$(base64url_encode "${header}")

  # Create JWT payload
  payload='{
  "iss": "'${TACKER_CLIENT_ID}'",
  "sub": "'${TACKER_CLIENT_ID}'",
  "aud": "'${TACKER_AUTH_URL}'",
  "iat": "'${create_time}'",
  "exp": "'${expire_time}'",
  "jti": "'${jti}'"
  }'
  payload_b64=$(base64url_encode "${payload}")
  # Combine header and payload
  unsigned_token="${header_b64}.${payload_b64}"
  # Sign the token
  if [ "${key_type}" = "secret" ]; then
    # Sign with secret key (HS256)
    hexsecret=$(echo -n "${TACKER_CLIENT_SECRET}" |
      xxd -p |
      paste -sd "")
    signature=$(echo -n "${unsigned_token}" |
      openssl dgst -sha256 -mac HMAC -macopt hexkey:"${hexsecret}" -binary |
      base64 |
      tr '/+' '_-' |
      tr -d '=')
  else
    # Sign with private key (RS256)
    signature=$(echo -n "${unsigned_token}" |
      openssl dgst -sha256 -sign "${TACKER_JWT_KEY}" |
      base64 |
      tr '/+' '_-' |
      tr -d '=')
  fi
  # Create the complete JWT
  jwt="${unsigned_token}.${signature}"
  echo "${jwt}"
}

function authenticate::client_secret_basic() {
  TACKER_ACCESS_TOKEN=$(curl -s -X POST "${TACKER_AUTH_URL}" -u "${TACKER_CLIENT_ID}:${TACKER_CLIENT_SECRET}" -d "grant_type=client_credentials" -d "scope=${TACKER_OAUTH2_SCOPE}" "${@}" | jq -r ".access_token")
  export TACKER_ACCESS_TOKEN
}

function authenticate::client_secret_post() {
  TACKER_ACCESS_TOKEN=$(curl -s -X POST "${TACKER_AUTH_URL}" -d "client_id=${TACKER_CLIENT_ID}" -d "client_secret=${TACKER_CLIENT_SECRET}" -d "grant_type=client_credentials" -d "scope=${TACKER_OAUTH2_SCOPE}" "${@}" | jq -r ".access_token")
  export TACKER_ACCESS_TOKEN
}

function authenticate::private_key_jwt() {
  assertion=$(authenticate::create_client_assertion "key")
  TACKER_ACCESS_TOKEN=$(curl -s -X POST "${TACKER_AUTH_URL}" -d "client_id=${TACKER_CLIENT_ID}" -d "grant_type=client_credentials" -d "scope=${TACKER_OAUTH2_SCOPE}" -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" -d "client_assertion=${assertion}" "${@}" | jq -r ".access_token")
  export TACKER_ACCESS_TOKEN
}

function authenticate::client_secret_jwt() {
  assertion=$(authenticate::create_client_assertion "secret")
  TACKER_ACCESS_TOKEN=$(curl -s -X POST "${TACKER_AUTH_URL}" -d "client_id=${TACKER_CLIENT_ID}" -d "grant_type=client_credentials" -d "scope=${TACKER_OAUTH2_SCOPE}" -d "client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer" -d "client_assertion=${assertion}" "${@}" | jq -r ".access_token")
  export TACKER_ACCESS_TOKEN
}

function authenticate::tls_client_auth() {
  TACKER_ACCESS_TOKEN=$(curl -s -X POST "${TACKER_AUTH_URL}" -d "client_id=${TACKER_CLIENT_ID}" -d "grant_type=client_credentials" -d "scope=${TACKER_OAUTH2_SCOPE}" "${@}" | jq -r ".access_token")
  export TACKER_ACCESS_TOKEN
}

function authenticate() {
  case ${TACKER_AUTH_TYPE} in
  client_secret_basic)
    authenticate::client_secret_basic "${@}"
    return
    ;;
  client_secret_post)
    authenticate::client_secret_post "${@}"
    return
    ;;
  private_key_jwt)
    authenticate::private_key_jwt "${@}"
    return
    ;;
  client_secret_jwt)
    authenticate::client_secret_jwt "${@}"
    return
    ;;
  tls_client_auth)
    authenticate::tls_client_auth "${@}"
    return
    ;;
  *)
    echo "Unknown auth type: ${TACKER_AUTH_TYPE}"
    exit 1
    ;;
  esac
}

function exec_curl::setup_mtls() {
  if [[ "${TACKER_CACERT:+defined}" ]]; then
    set -- "${@}" --cacert "${TACKER_CACERT}"
  fi
  if [[ "${TACKER_CLIENT_KEY:+defined}" && "${TACKER_CLIENT_CERT:+defined}" ]]; then
    set -- "${@}" --key "${TACKER_CLIENT_KEY}" --cert "${TACKER_CLIENT_CERT}"
  fi
  echo "${@}"
}

function generate_uuid() {
  if command -v uuidgen >/dev/null; then
    uuidgen
  else
    cat /proc/sys/kernel/random/uuid
  fi
}

function base64url_encode() {
  echo -n "$1" | base64 -w 0 | tr '/+' '_-' | tr -d '='
}

function exec_curl() {
  # Usage: exec_curl [<http_method>] <path> [<curl_arg> ...]

  # set HTTP method if specified
  if [[ ${1} == ${HTTP_METHOD} ]]; then
    method="${1}"
    shift
  fi

  # set path in URL
  if [[ ${1} == /* ]]; then
    path="${1}"
    shift
  else
    echo "invalid path: ${1}"
    exit 1
  fi

  # set opts to use certs if tls_client_auth is selected
  mtls_args=$(exec_curl::setup_mtls)

  # get OAuth2.0 token to call Tacker API
  authenticate ${mtls_args}
  set -- "${@}" -H "Authorization: Bearer ${TACKER_ACCESS_TOKEN}"

  # set default content-type if not set
  if ! echo "${@}" | grep -q "Content-Type:"; then
    set -- "${@}" -H "Content-Type: application/json"
  fi

  curl -X ${method:-GET} ${TACKER_URL}/${path} "${@}" ${mtls_args:+$mtls_args}
}

function main() {
  case $1 in
  -h | --help)
    usage | less -F
    exit 0
    ;;
  -v | --version)
    echo "${VERSION}"
    exit 0
    ;;
  vim)
    shift
    vim "${@}"
    exit 0
    ;;
  vnfpkgm)
    shift
    vnfpkgm "${@}"
    exit 0
    ;;
  vnflcm)
    shift
    vnflcm "${@}"
    exit 0
    ;;
  vnffm)
    shift
    vnffm "${@}"
    exit 0
    ;;
  vnfpm)
    shift
    vnfpm "${@}"
    exit 0
    ;;
  *)
    usage | less -F
    exit 1
    ;;
  esac
}

main "${@}"
