import fabric.api
from fabric.state import env

from .context_managers import silent


def run(command, shell=True, pty=True, combine_stderr=None, use_sudo=False, user=None):
    use_sudo = use_sudo or user is not None or env.get('use_sudo')

    if not use_sudo:
        return fabric_run(command, shell=shell, pty=pty, combine_stderr=combine_stderr)

    else:
        user = user or env.get('sudo_user', env.user)
        # Make SSH agent socket available to the sudo user
        with silent():
            fabric_sudo('chown -R {}: $(dirname $SSH_AUTH_SOCK)'.format(user), user='root')

        if user == env.user:
            user = None

        return fabric_sudo(command, shell=shell, pty=pty, combine_stderr=combine_stderr, user=user)


### Monkey patch fabric
fabric_run = fabric.api.run
fabric_sudo = fabric.api.sudo
for m in (fabric.api, fabric.operations, fabric.contrib.files, fabric.contrib.project):
    m.run = m.sudo = run
