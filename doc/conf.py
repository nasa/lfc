# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

import os
import sys
import datetime

# Current date
now = datetime.datetime.now()

# Path to database and test modules
fgit = os.path.abspath("..")
fdoc = os.path.abspath(".")

# Name of repo
repo = os.path.basename(fgit)

# Basic title/subtitle
desc = "a git extension for large files"

# Paths to append
for _f in [fgit]:
    if _f not in sys.path:
        sys.path.insert(0, _f)
        

# -- Project information -----------------------------------------------------

project = repo
copyright = u'National Aeronautics and Space Administration'
author = u'NASA Ames CAPE Team'

# The short X.Y version
version = "1.0"
# The full version, including alpha/beta/rc tags
release = "1.0.0"


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx_copybutton',
]

# Things to exclude from copy button
copybutton_exclude = '.linenos, .gp, .go'

# Main title
title = "%s: %s" % (repo, desc)

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
source_suffix = '.rst'

# Encoding of source files
source_encoding = "utf-8-sig"

# The master toctree document.
master_doc = 'index'

# Please don't go around testing every code definition
doctest_test_doctest_blocks = ''

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = [u'_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinxdoc'

# Clean up autodoc tables of contents
toc_object_entries = False

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {
#    "stickysidebar": "false",
#    "sidebarbgcolor": "#000665",
#    "sidebarlinkcolor": "#a0c0ff",
#    "relbarbgcolor": "#000645",
#    "footerbgcolor": "#000665"
#}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Modify title of HTML document
html_title = title

# Short title
html_short_title = "%s" % repo

# Logo for sidebar
html_logo = "NASA_logo.png"

# Favicon for HTML tab
html_favicon = "NASA_logo_icon.ico"

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
# html_sidebars = {}


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % repo


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        '%s.tex' % repo,
        u'%s Documentation' % repo,
        author,
        'howto'),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (
        master_doc,
        ('%s' % repo).lower(),
        u'%s Documentation' % repo,
        [author],
        1)
]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        '%s' % repo,
        u'%s Documentation' % repo,
        author,
        repo,
        desc,
        'Miscellaneous'),
]

# Logo for LaTeX
latex_logo = "NASA_logo.pdf"


# -- Extension configuration -------------------------------------------------
