# plugin.sh - Devstack extras script to install tacker

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "tacker's plugin.sh was called with args $1 and $2 ..."
. $DEST/tacker/devstack/lib/tacker
(set -o posix; set)

# check for service enabled
if is_service_enabled tacker; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing Tacker"
        install_tacker

        if use_library_from_git heat-translator; then
            git_clone_by_name heat-translator
            setup_dev_lib heat-translator
        fi
        if use_library_from_git tosca-parser; then
            git_clone_by_name tosca-parser
            setup_dev_lib tosca-parser
        fi

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring Tacker"
        configure_tacker
        create_tacker_accounts

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the tacker service
        echo_summary "Initializing Tacker"
        init_tacker
        echo_summary "Starting Tacker API and conductor"
        start_tacker
        if is_service_enabled horizon; then
            echo_summary "Installing tacker horizon"
            tacker_horizon_install
        fi

        if [[ "${TACKER_MODE}" == "all" || "${IS_ZUUL_FT}" == "True" ]]; then
            echo_summary "Setup initial tacker network"
            tacker_create_initial_network
            echo_summary "Check and download images for tacker initial"
            tacker_check_and_download_images
            echo_summary "Setup default VIM resources"
            tacker_setup_default_vim_resources

            if is_service_enabled ceilometer; then
                echo_summary "Configure maintenance event types"
                configure_maintenance_event_types
            fi
        fi
    fi

    if [[ "$1" == "unstack" ]]; then
        # Shut down tacker services
        if is_service_enabled horizon; then
            echo_summary "Uninstall tacker horizon"
            tacker_horizon_uninstall
        fi
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
