
LFC 1.2.0
===============

New features
-----------------

* Several new commands, ``lfc-purge``, ``lfc-publish``, and ``lfc-uncache``
* The ``lfc-publish`` command combines ``lfc-add`` and ``lfc-push``.
* The ``lfc-purge`` command will delete working files and local cache files if
  that file is present in the remote cache.
* The ``lfc-uncache`` command deletes a file from the local cache but keeps the
  working large file; useful for very large file to avoid having to have two
  copies.


LFC 1.1.3
==============

New features
-----------------

* New command-line interface, mostly invisible to user
* CLI will now have an error if the user enters an unrecognized option
* User can also directly call executables such as ``lfc-show``
