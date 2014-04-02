import fabric.api
from fabric.state import env


def run(command, shell=True, pty=True, combine_stderr=None, use_sudo=False, user=None):
    user = getattr(env, 'sudo_user', user)
    use_sudo = user or use_sudo
    if not use_sudo:
        return fabric_run(command, shell=shell, pty=pty, combine_stderr=combine_stderr)

    else:
        if user == env.user:
            user = None
        return fabric_sudo(command, shell=shell, pty=pty, combine_stderr=combine_stderr, user=user)


### Monkey patch fabric
fabric_run = fabric.api.run
fabric_sudo = fabric.api.sudo
for m in (fabric.api, fabric.operations, fabric.contrib.files, fabric.contrib.project):
    m.run = m.sudo = run
