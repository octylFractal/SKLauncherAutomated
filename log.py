import functools
import itertools
import sys
import os

__author__ = 'kenzietogami'


def log(f):
    if os.environ.get('SKLA_TRACING', '0') == '0':
        return f

    def log_func(a, k, enter, exit_val=None, error=False):
        print('{} {}({}){}{}'.format(
            'Begin' if enter else 'Finish',
            f.__name__,
            ','.join(itertools.chain(map(str, a), ('{}={}'.format(k, v) for k, v in k.items()))),
            '' if enter else ' -> {}'.format(exit_val),
            '' if not error else '; threw {}({})'.format(*sys.exc_info()[:2])
        ), file=sys.stderr)

    @functools.wraps(f)
    def func(*args, **kwargs):
        log_func(args, kwargs, True)
        v = None
        error = False
        try:
            v = f(*args, **kwargs)
        except:
            error = True
            raise
        finally:
            log_func(args, kwargs, False, v, error=error)
        return v

    return func
