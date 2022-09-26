
"""infopath.py -- filesystem and INFOPATH handling."""

import os
from pathlib import Path, PosixPath

default_infopath = ':'.join((
    '/usr/local/info',
    '/usr/info',
    '/usr/local/lib/info',
    '/usr/lib/info',
    '/usr/local/gnu/info',
    '/usr/local/gnu/lib/info',
    '/usr/gnu/info',
    '/usr/gnu/lib/info',
    '/opt/gnu/info',
    '/usr/share/info',
    '/usr/share/lib/info',
    '/usr/local/share/info',
    '/usr/local/share/lib/info',
    '/usr/gnu/lib/emacs/info',
    '/usr/local/gnu/lib/emacs/info',
    '/usr/loacl/lib/emacs/info',
    '/usr/local/emacs/info',
    '.'
))


# The pathlib module has different implementations depending on the operating
# system, so we can't simply inherit Path. Since Windows users wouldn't use
# this kind of app anyways just use the posix variety.
class IPath(PosixPath):
    """Represents entries in the infopath as well as info files."""

    def __eq__(self, other):
        """Equivalent to samefile."""
        return self.samefile(other)

    def __hash__(self):
        """Compare inode and device."""
        return hash(self.stat().st_ino) ^ hash(self.stat().st_dev)

    def __init__(self, onepath):
        """Special initialization for child.

        You should always read the source of whatever you're subclassing if the
        parent resides in the standard library. This is because class design
        (like everything else in python) is done in runtime while also being
        quite meta; objects can be initialized via the __new__ method and may
        not even have an __init__!

        tl;dr Python throws an error without this.
        """
        super().__new__(PosixPath, onepath)


infodirs: set[IPath] = set()
env = os.getenv('INFOPATH', default_infopath)
env_list = env.split(':')
try:
    env_list.remove('PATH')
except ValueError:
    pass
else:
    suffixes = ['share/info', 'info']
    sys_path = os.getenv('PATH')
    if sys_path is not None:
        IPaths = (IPath(p) for p in sys_path.split(':'))
    for path in IPaths:
        for suffix in suffixes:
            tpath = path.joinpath(suffix)
            if tpath.is_dir():
                infodirs.add(IPath(path))
infodirs |= {IPath(p) for p in env.split(':')}
