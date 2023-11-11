
=================================================
``lfc``: A git extension for large files
=================================================

``lfc``, which stands for "Large File Control," is an add-on for 
`git <https://git-scm.com/>`_ that provides a method of tracking large files in
git repositories. It is inspired by `dvc <https://dvc.org>`_ but is simpler and
has a different feature set.

The way it works is that users declare individual files "large," which means
that when users clone, pull, or fetch from a repo, those files are not
automatically downloaded but instead can be retrieved on-demand. This has two
main advantages:

    * you can clone a repo with large files quickly, but without the large
      files (for example to work on an input file); and
    * in cases where the large file(s) is (are) needed, you only need the most
      recent version instead of the whole history of that file.

In general, LFC is for any project that uses git but also generates large files
or even small files that happen to be binary. Here are some specific example
use cases where LFC might be useful.

    *   You're a 21st-century developer using modern programming tools and git
        version control, but your colleagues keep sending you Word and Excel
        files that are the inputs to your process. You can use LFC to track
        those documents in a traceable and reliable way.

.. toctree::
    :maxdepth: 2
    :numbered:

    examples/getting-started
    story

**lfc Python package:**

.. toctree::
    :maxdepth: 2

    api/lfc
    api/python

.. only:: html

    Indices and tables
    ==================
    
    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`

