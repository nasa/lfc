
.. _getting-started:

---------------------------
Getting started with LFC
---------------------------

Consider a simple example where we create a git repo:

    .. code-block:: console

        $ mkdir repo
        $ cd repo
        $ echo "A simple file" > something.txt
        $ git init
        $ git add something.txt
        $ git commit -a -m "Initial commit"

Now you have a git repository ``repo/.git`` with one file called
``something.txt``. Let's also create a bare repo to demonstrate push/pull
operations.

    .. code-block:: console

        $ cd ..
        $ git clone repo --bare
        $ cd repo

Now let's create a binary file ``myfile.dat``. In this
example it is not exactly "large" (1 MB), but since it's not text, git doesn't
know much what to do with it.

    .. code-block:: console

        $ python -c "import os; open('myfile.dat', 'wb').write(os.urandom(1024*1024)"

So now we can turn this repo into an LFC repo. We can then add the binary file
using ``lfc`` instead of ``git``

    .. code-block:: console

        $ lfc init
        $ lfc add myfile.dat

Now the git status result from these two ``lfc`` commands is fairly extensive,
and it gives you a pretty good idea how LFC works. The file ``myfile.dat.lfc``
contains metadata about the original file ``myfile.dat``, including a SHA-256
hash of that file's contents. The file ``.gitignore`` shows up because LFC has
told git to ignore ``myfile.dat``. The main configuration for LFC is in
``.lfc/config``, and the actual data cache is in ``.lfc/cache``. The file
``.lfc/.gitignore`` ensures that the cache doesn't get the attention of git.

    .. code-block:: console

        $ git status -s
        A  .gitignore
        A  .lfc/.gitignore
        A  .lfc/config
        A  myfile.dat.lfc

To share the large file, you'll need to create a remote. This is done
separately from git's remotes.

    .. code-block:: console

        $ git remote add hub ../repo.git
        $ lfc remote add -d hub ../repo.git/cache
        $ git commit -a -m "Initialize LFC"

Now you can push the large file to the hub using ``lfc push``

    .. code-block:: console

        $ lfc push
        myfile.dat [local -> hub]
