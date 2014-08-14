from functools import partial

import fabric.state
from fabric.decorators import task

from .state import load_blueprints
from .tasks import dispatch
from .operations import run
from .utils import info

__all__ = ['bootstrap', 'run', 'info']


def bootstrap():
    """
    Add state- and role-tasks, i.e. app@live
    Import blueprint libraries
    """
    fabric.state.env.update({
        'user': 'ubuntu',
        'sudo_user': 'root',
        'linewise': True,
        'colorize_errors': True,
        'skip_unknown_tasks': True,
        'merge_states': True,
        'prompt_hosts': True,
        'forward_agent': True,
        'sudo_prefix': "sudo -S -E -p '%(sudo_prompt)s' SSH_AUTH_SOCK=$SSH_AUTH_SOCK",
    })

    for env_name, env in fabric.state.env.states.items():
        if env_name == 'default':
            continue

        task_name = '@{env}'.format(env=env_name)
        state_task = partial(dispatch, env_name)
        docstring = 'switch to configured Fab env "{env}"'.format(env=env_name)

        state_task.__doc__ = docstring
        fabric.state.commands[task_name] = task(state_task)

        roledefs = env.get('roledefs')
        if roledefs:
            for role_name in roledefs.keys():
                task_name = '{role}@{env}'.format(role=role_name, env=env_name)
                state_task = partial(dispatch, env_name, roles=[role_name])
                docstring = 'switch to configured Fab env "{env}", ' \
                            'and use role "{role}"'.format(env=env_name, role=role_name)
                state_task.__doc__ = docstring
                fabric.state.commands[task_name] = task(state_task)

    load_blueprints()
