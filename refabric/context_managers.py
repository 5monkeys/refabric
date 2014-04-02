# coding=utf-8
from contextlib import contextmanager
from functools import wraps
from fabric.context_managers import cd as ctx_cd, settings, hide, show, prefix
from fabric.state import env

__all__ = ['get_sudo_context', 'sudo', 'only_messages', 'prefix']


@contextmanager
def sudo(user=None):
    pre_sudo_user = env.get('sudo_user')
    env.sudo_user = user or pre_sudo_user or env.user
    yield
    env.sudo_user = pre_sudo_user


silent = lambda: settings(hide('commands'), warn_only=True)

@contextmanager
def only_messages(warn_only=True):
    with settings(hide('everything'), show('user'), warn_only=warn_only):
        yield


@contextmanager
def cd_sudo(path):
    with settings(hide('everything')):
        perm = remote.permissions(path)
    with remote_user(perm['owner'], cd=path):
        yield


@contextmanager
def remote_user(name, cd=None, cd_join=None):
    if not name:
        raise Exception(u"No name")
    with settings(hide('everything')):
        home_dir = run('echo ~' + name).strip()
    with sudo(name), shell_env(HOME=home_dir):
        if cd:
            # if type(cd) is list:
            #     cd = path.join(cd)
            with ctx_cd(cd):
                yield
        else:
            yield


@contextmanager
def shell_env(**env_vars):
    orig_shell = env['shell']
    env_vars_str = ' '.join('{0}={1}'.format(key, value)
                            for key, value in env_vars.items())
    env['shell'] = '{0} {1}'.format(env_vars_str, orig_shell)
    yield
    env['shell'] = orig_shell
