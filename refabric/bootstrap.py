from functools import partial

__all__ = ['bootstrap']


def bootstrap():
    """
    Add state- and role-tasks, i.e. app@live
    Import blueprint libraries
    """
    import fabric.state
    from fabric.decorators import task

    from .state import load_blueprints, apply_role_definitions
    from .tasks import dispatch, help_task, init_task

    fabric.state.env.update({
        'user': 'ubuntu',
        'sudo_user': 'root',
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

        roledefs = env.get('roledefs')
        if roledefs:
            for role_name in roledefs.keys():
                task_name = '{role}@{env}'.format(role=role_name, env=env_name)
                state_task = partial(dispatch, env_name, role_name)
                docstring = 'switch to configured Fab env "{env}", ' \
                            'and use role "{role}"'.format(env=env_name, role=role_name)
                state_task.__doc__ = docstring
                fabric.state.commands[task_name] = task(state_task)

    # Create global blueprint tasks
    fabric.state.commands['help'] = task(help_task)
    fabric.state.commands['init'] = task(init_task)

    # Apply
    if fabric.state.env.roles:
        apply_role_definitions(*fabric.state.env.roles)

    load_blueprints()
