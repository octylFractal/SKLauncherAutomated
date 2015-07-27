__author__ = 'Kenzie Togami'
import log
import sh
from pathlib import Path


class CDContext:
    def __init__(self, directory):
        if not directory:
            raise ValueError('must be a "valid" directory, not {}'.format(directory))
        self.directory = str(directory)
        self._old = ''

    @log.log
    def __enter__(self):
        self._old = str(Path.cwd().absolute())
        sh.cd(self.directory)

    @log.log
    def __exit__(self, exc_type, exc_val, exc_tb):
        sh.cd(self._old)

    def __repr__(self):
        return 'cd({})'.format(self.directory)


def cd(d):
    return CDContext(d)


# nice_tty support
import os
import sys

env = os.environ.copy()
is_term = 'TERM' in env
env.setdefault('TERM', 'xterm')
env['PAGER'] = ''  # no pagin' in this house
out = sys.stdout
err = sys.stderr
if hasattr(out, 'buffer'):
    def write_out(x):
        if not isinstance(x, bytes):
            x = str(x).encode('utf-8')
        out.buffer.write(x)
        out.buffer.flush()
else:
    def write_out(x):
        if isinstance(x, bytes):
            x = x.decode(errors='ignore')
        out.write(x)
        out.flush()
if hasattr(err, 'buffer'):
    def write_err(x):
        if not isinstance(x, bytes):
            x = str(x).encode('utf-8')
        err.buffer.write(x)
        err.buffer.flush()
else:
    def write_err(x):
        if isinstance(x, bytes):
            x = x.decode(errors='ignore')
        err.flush()


def bake_nice_tty(cmd):
    return cmd.bake(_env=env,
                    _out=write_out,
                    _err=write_err,
                    _out_bufsize=0,
                    _err_bufsize=0,
                    _tty_out=is_term,
                    _tty_size=(80, 240))
    # a decent sized terminal, note that this may cause strange behaviour


__all__ = ['cd', 'bake_nice_tty']
