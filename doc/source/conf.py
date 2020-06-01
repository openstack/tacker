# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinxcontrib.apidoc',
    'stevedore.sphinxext',
    'openstackdocstheme',
    'oslo_config.sphinxext',
    'oslo_config.sphinxconfiggen',
    'oslo_policy.sphinxext',
    'oslo_policy.sphinxpolicygen',
]

config_generator_config_file = '../../etc/config-generator.conf'
sample_config_basename = '_static/tacker'

policy_generator_config_file = [
    ('../../etc/tacker-policy-generator.conf', '_static/tacker'),
]
sample_policy_basename = '_static/tacker'

# sphinxcontrib.apidoc options
apidoc_module_dir = '../../tacker'
apidoc_output_dir = 'contributor/api'
apidoc_excluded_paths = [
    'tests/*',
    'tests',
    'nfvo/workflows/*',
    'nfvo/workflows',
    'vnfm/workflows/*',
    'vnfm/workflows',
    'db/migration/alembic_migrations/*',
    'db/migration/alembic_migrations',
    'hacking']
apidoc_separate_modules = True

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'tacker'
copyright = u'2013, OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['tacker.']

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_static_path = ['static']
html_theme = 'openstackdocs'

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % project

# Add any paths that contain "extra" files, such as .htaccess or
# robots.txt.
html_extra_path = ['_extra']

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     '%s.tex' % project,
     u'%s Documentation' % project,
     u'OpenStack Foundation', 'manual'),
]

# Example configuration for intersphinx: refer to the Python standard library.
#intersphinx_mapping = {'http://docs.python.org/': None}

# -- Options for openstackdocstheme -------------------------------------------
openstackdocs_repo_name = 'openstack/tacker'
openstackdocs_auto_name = False
openstackdocs_bug_project = 'tacker'
openstackdocs_bug_tag = ''
