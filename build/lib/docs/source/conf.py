# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
# test_dir = os.path.join(os.path.dirname(__file__), 'tests')
# sys.path.insert(0, test_dir)

import django
# from django.test.utils import get_runner
# from django.conf import settings

if hasattr(django, 'setup'):
    django.setup()


# import os
# import sys

sys.path.insert(0, os.path.abspath('../../'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'JWT Allauth'
copyright = '2025, Fernando Castellanos'
author = 'Fernando Castellanos'
release = '1.0.0'

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
]

html_theme = 'furo'
html_static_path = ['_static']
