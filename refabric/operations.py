import fabric.operations
from fabric.state import env

from .context_managers import silent

__all__ = ['run']


def run(command, shell=True, pty=True, combine_stderr=None, use_sudo=False, user=None, **kwargs):
    """
    Patched version of fabric.operations.run & sudo.
    """
    use_sudo = use_sudo or user is not None or env.get('use_sudo')

    if not use_sudo:
        return fabric.operations.run.original(command, shell=shell, pty=pty, combine_stderr=combine_stderr, **kwargs)

    else:
        user = user or env.get('sudo_user', env.user)
        # Make SSH agent socket available to the sudo user
        with silent():
            fabric.operations.sudo.original('chown -R {}: $(dirname $SSH_AUTH_SOCK)'.format(user), user='root',
                                            **kwargs)

        if user == env.user:
            user = None

        return fabric.operations.sudo.original(command, shell=shell, pty=pty, combine_stderr=combine_stderr,
                                               user=user, **kwargs)
