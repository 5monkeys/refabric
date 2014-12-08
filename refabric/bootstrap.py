import fabric.tasks

__all__ = ['bootstrap']


def bootstrap():
    """
    Add state- and role-tasks, i.e. app@live
    Import blueprint libraries
    """
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
        'sudo_prefix': "sudo -S -E -p '%(sudo_prompt)s' SSH_AUTH_SOCK=$SSH_AUTH_SOCK",
    })

    # Create global blueprint tasks
    fabric.state.commands['help'] = task(help_task)
    fabric.state.commands['init'] = task(init_task)

    # Load configured blueprints
    load_blueprints()

    # Touch env.roles to trigger apply role definitions (needed for cli options -R, --list etc.)
    fabric.state.env.roles = fabric.state.env.roles


def patch(original_path, patch_path=None, keep=True):
    original_path, _, method = original_path.partition(':')
    original_package, original_func_name = original_path.rsplit('.', 1)
    original_module = __import__(original_package, fromlist=['*'])
    original_func = getattr(original_module, original_func_name)
    if method:
        original_func = getattr(original_func, method)

    if not patch_path:
        patch_path = '.'.join(('refabric', original_path.split('.', 1)[1]))
    patch_package, patch_func_name = patch_path.rsplit('.', 1)
    patch_module = __import__(patch_package, fromlist=['*'])
    patch_func = getattr(patch_module, patch_func_name)

    if keep:
        patch_func.original = original_func
    setattr(original_module, original_func_name, patch_func)


# Monkey patch fabric
patch('fabric.state.switch_env')
patch('fabric.tasks._execute')
patch('fabric.utils._AttributeDict:__setitem__', 'refabric.utils.env_setitem', keep=False)
patch('fabric.operations.run')
patch('fabric.operations.sudo', 'refabric.operations.run')


# Reload fabric's run/sudo import references to patched version
import fabric.api
import fabric.operations
import fabric.contrib.files
import fabric.contrib.project
for m in (fabric.api, fabric.contrib.files, fabric.contrib.project):
    m.run = m.sudo = fabric.operations.run
