# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath('../../'))

# Configure Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

import django
# from django.test.utils import get_runner
# from django.conf import settings

if hasattr(django, 'setup'):
    django.setup()


# import os
# import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'JWT Allauth'
copyright = '2025, Fernando Castellanos'
author = 'Fernando Castellanos'
release = '1.4.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinxext.opengraph',
]

html_theme = 'furo'
html_static_path = ['_static']

# -- Discoverability ---------------------------------------------------------

# Sphinx would otherwise stamp the release into the <title> of every page, which makes a
# bookmark or a search result go stale on the next version.
html_title = project

# The root page names its subject instead, through _templates/base.html. Kept under 60
# characters so that search engines show it whole.
html_context = {
    'root_page_title': 'JWT Allauth: JWT sessions for Django REST Framework',
}

# Canonical URL, so that the copies Read the Docs serves for every version and every pull
# request preview do not compete with one another. The environment variable is the one
# Read the Docs sets during its own builds.
html_baseurl = os.environ.get(
    'READTHEDOCS_CANONICAL_URL', 'https://jwt-allauth.readthedocs.io/en/latest/'
)

# og: tags, so that a link pasted into Slack, Discord or a social timeline renders as
# something other than a bare URL.
ogp_site_url = html_baseurl
ogp_site_name = 'JWT Allauth'
ogp_type = 'website'
ogp_enable_meta_description = True
