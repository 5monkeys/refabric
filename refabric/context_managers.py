# coding=utf-8
from contextlib import contextmanager
from fabric.context_managers import settings, hide, prefix
from fabric.state import env

__all__ = ['get_sudo_context', 'sudo', 'only_messages', 'prefix']


@contextmanager
def sudo(user=None):
    with settings(sudo_user=user or env.sudo_user or env.user, use_sudo=True):
        yield


silent = lambda: settings(hide('commands'), warn_only=True)
hide_prefix = lambda: settings(output_prefix=False)
abort_on_error = lambda: settings(warn_only=False)


@contextmanager
def shell_env(**env_vars):
    orig_shell = env['shell']
    env_vars_str = ' '.join('{0}={1}'.format(key, value)
                            for key, value in env_vars.items())
    env['shell'] = '{0} {1}'.format(env_vars_str, orig_shell)
    yield
    env['shell'] = orig_shell
