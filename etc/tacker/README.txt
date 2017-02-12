To generate the sample tacker configuration files, run the following
command from the top level of the tacker directory:

tox -e config-gen

If a 'tox' environment is unavailable, then you can run the following script
instead to generate the configuration files:

./tools/generate_config_file_sample.sh
