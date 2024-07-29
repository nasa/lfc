
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

    *   You have a repo that generates some binary files (which may or may not
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
    cli/index

**lfc Python package:**

.. toctree::
    :maxdepth: 2

    api/lfc
    api/argread/index
    api/kwparse
    api/gitutils/index
    api/shellutils
    api/python
    api/standardlib
    api/thirdparty

.. only:: html

    Indices and tables
    ==================
    
    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`

**Notices**

Copyright © 2024 United States Government as represented by the Administrator
of the National Aeronautics and Space Administration. All Rights Reserved.

**Disclaimers**

No Warranty: THE SUBJECT SOFTWARE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY OF
ANY KIND, EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED
TO, ANY WARRANTY THAT THE SUBJECT SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY
IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR
FREEDOM FROM INFRINGEMENT, ANY WARRANTY THAT THE SUBJECT SOFTWARE WILL BE ERROR
FREE, OR ANY WARRANTY THAT DOCUMENTATION, IF PROVIDED, WILL CONFORM TO THE
SUBJECT SOFTWARE. THIS AGREEMENT DOES NOT, IN ANY MANNER, CONSTITUTE AN
ENDORSEMENT BY GOVERNMENT AGENCY OR ANY PRIOR RECIPIENT OF ANY RESULTS,
RESULTING DESIGNS, HARDWARE, SOFTWARE PRODUCTS OR ANY OTHER APPLICATIONS
RESULTING FROM USE OF THE SUBJECT SOFTWARE. FURTHER, GOVERNMENT AGENCY
DISCLAIMS ALL WARRANTIES AND LIABILITIES REGARDING THIRD-PARTY SOFTWARE, IF
PRESENT IN THE ORIGINAL SOFTWARE, AND DISTRIBUTES IT "AS IS."

Waiver and Indemnity: RECIPIENT AGREES TO WAIVE ANY AND ALL CLAIMS AGAINST THE
UNITED STATES GOVERNMENT, ITS CONTRACTORS AND SUBCONTRACTORS, AS WELL AS ANY
PRIOR RECIPIENT. IF RECIPIENT'S USE OF THE SUBJECT SOFTWARE RESULTS IN ANY
LIABILITIES, DEMANDS, DAMAGES, EXPENSES OR LOSSES ARISING FROM SUCH USE,
INCLUDING ANY DAMAGES FROM PRODUCTS BASED ON, OR RESULTING FROM, RECIPIENT'S
USE OF THE SUBJECT SOFTWARE, RECIPIENT SHALL INDEMNIFY AND HOLD HARMLESS THE
UNITED STATES GOVERNMENT, ITS CONTRACTORS AND SUBCONTRACTORS, AS WELL AS ANY
PRIOR RECIPIENT, TO THE EXTENT PERMITTED BY LAW. RECIPIENT'S SOLE REMEDY FOR
ANY SUCH MATTER SHALL BE THE IMMEDIATE, UNILATERAL TERMINATION OF THIS
AGREEMENT.

.. toctree::

    LICENSE