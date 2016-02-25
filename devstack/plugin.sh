# plugin.sh - Devstack extras script to install tacker

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "tacker's plugin.sh was called..."
source $DEST/tacker/devstack/lib/tacker
(set -o posix; set)

# check for service enabled
if is_service_enabled tacker; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing Tacker"
        install_tacker
        install_tackerclient

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring Tacker"
        configure_tacker
        create_tacker_accounts

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the tacker service
        echo_summary "Initializing Tacker"
        init_tacker
        echo_summary "Starting Tacker API"
        start_tacker_api
        echo_summary "Installing tacker horizon"
        tacker_horizon_install
        echo_summary "Setup initial tacker network"
        tacker_create_initial_network
        echo_summary "Upload OpenWrt image"
        tacker_create_openwrt_image
        echo_summary "Registering default VIM"
        tacker_register_default_vim
    fi

    if [[ "$1" == "unstack" ]]; then
        # Shut down tacker services
	stop_tacker
    fi

    if [[ "$1" == "clean" ]]; then
        # Remove state and transient data
        # Remember clean.sh first calls unstack.sh
        cleanup_tacker
    fi
fi

# Restore xtrace
$XTRACE

# Tell emacs to use shell-script-mode
## Local variables:
## mode: shell-script
## End:

