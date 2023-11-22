
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

    *   You're working in computational fluid dynamics (CFD) that requires very
        large inputs and produces even larger outputs, and you'd like to make
        the whole process reproducible without resorting to *ad hoc* scripts.

    *   You're a 21st-century developer using modern programming tools and git
        version control, but your colleagues keep sending you Word and Excel
        files that are the inputs to your process. You can use LFC to track
        those documents in a traceable and reliable way.

    *   You have a process that generates binary output files and you'd like to
        keep track of all the different versions of those files without having
        to store all of them locally.

    *   You have a repo that generates some binary file (which may or may not
        be "large"), for example a picture, every day. You'd like users to be
        able to clone the repo that makes and tracks those pictures but not
        have to download the entire picture-of-the-day archive when they clone
        the repo.

    *   And many others.

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
    api/standardlib
    api/thirdparty

.. only:: html

    Indices and tables
    ==================
    
    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`

