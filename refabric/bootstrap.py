__all__ = ['bootstrap']


def bootstrap():
    """
    Define global blueprint tasks, load configured blueprints and apply role definitions.
    """
    # Monkey patch fabric
    from .patch import patch
    patch('fabric.operations.run')
    patch('fabric.operations.sudo', 'refabric.operations.run')
    patch('fabric.state.switch_env')
    patch('fabric.tasks._execute')
    patch('fabric.tasks.Task:get_hosts_and_effective_roles')
    patch('fabric.utils._AttributeDict')

    # Reload fabric's run/sudo internal import references to patched version
    import fabric.api
    import fabric.contrib.files
    import fabric.contrib.project
    import fabric.operations
    for m in (fabric.api, fabric.contrib.files, fabric.contrib.project):
        m.run = m.sudo = fabric.operations.run

    import fabric.state
    from fabric.decorators import task

    from .state import load_blueprints
    from .tasks import help_task, init_task

    # Set environment defaults
    fabric.state.env.update({
        'sudo_user': 'root',
        'colorize_errors': True,
        'skip_unknown_tasks': True,
        'merge_states': True,
        'prompt_hosts': True,
        'forward_agent': True,
        'sudo_prefix': "sudo -S -E -H -p '%(sudo_prompt)s' SSH_AUTH_SOCK=$SSH_AUTH_SOCK",
    })

    # Create global blueprint tasks
    fabric.state.commands['help'] = task(help_task)
    fabric.state.commands['init'] = task(init_task)

    # Load configured blueprints
    load_blueprints()

    # Touch env.roles to trigger apply role definitions (needed for cli options -R, --list etc.)
    fabric.state.env.roles = fabric.state.env.roles
