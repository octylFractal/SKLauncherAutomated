__author__ = 'Kenzie Togami'
import sh
from cmd import cd, bake_nice_tty
from collections.abc import Callable
from pathlib import Path


class Gradle(Callable):
    """
    Usage:
        g = Gradle()
        g('build')
        g('clean', 'build')
        g('build', x='potato') # gradle build -x potato
        g = Gradle(wrapper=True) # uses ./gradlew
        g = Gradle(directory='/') # launches commands in /
    """

    def __init__(self, directory=Path.cwd(), wrapper=False):
        if wrapper:
            self._gradle = sh.Command(str((directory / 'gradlew').absolute()))
        else:
            self._gradle = sh.env.gradle
        self._gradle = bake_nice_tty(self._gradle)
        self.dir = directory

    def __call__(self, *args, **kwargs):
        with cd(self.dir):
            return self._gradle(*args, **kwargs)

    def __getattr__(self, item):
        itemlist = [item]

        def override(*args, **kwargs):
            mutated = itemlist + list(args)
            return self(*mutated, **kwargs)

        return override


__all__ = ['Gradle']
