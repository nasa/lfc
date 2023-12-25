
.. _story:

------------------------------
The story of ``lfc``
------------------------------

LFC is a small software package that started as one NASA team's solution to
the stubborn problem of what to do with large files in git repositories.
The NASA Ames SLS Computational Fluid Dynamics team uses a lot of repos, and
not just for software development. So although git alone is a perfect tool for
many software development project, we were often left with *ad hoc* methods to
deal with very large files like CFD mesh files or large solution data files.

Actually, the machine learning community was dealing with roughly the same set
of problems and developed a tool called `DVC <https://dvc.org/>`_ . Our team
adopted DVC for some time and found it to be a novel solution to the git
large-file conundrum. However, it was difficult to install and didn't work
reliably with our NASA high-performance computing environment, and as a result
we almost immediately starting thinking about creating our own simpler tool
with some of the same basic design. Then in late 2022 and January 2023, most
government Linux computers were forced to upgrade to RedHat Enterprise Linux
version 8. DVC, which used MD5 hashes, became completely unusable to us
overnight due to strict enforcement of Federal Information Protection
Standards (FIPS). At that point, our team forced to abandon DVC, but a tool
that was largely compatible with DVC was desirable because we already had so
many repos using DVC.

Fortunately, because we already had a plan to develop such a tool, we were
able to recover basic functionality within a few hours of work. We spent a
couple more months refining our tool, calling it LFC and making sure to have as
few dependencies as possible.

That's the story of why a small NASA team decided to create its own tool. We
are grateful to the creators of DVC for their original concept (but happy we
don't have to actually use it). We think this tool will be of interest to a
wider range of users ... at least within the U.S. government where FIPS
enforcement is an important and unavoidable factor.

