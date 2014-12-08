from contextlib import contextmanager

from fabric.context_managers import settings, hide
from fabric.state import env


@contextmanager
def sudo(user=None):
    with settings(sudo_user=user or env.sudo_user or env.user, use_sudo=True):
        yield


silent = lambda *h: settings(hide('commands', *h), warn_only=True)
hide_prefix = lambda: settings(output_prefix=False)
abort_on_error = lambda: settings(warn_only=False)
