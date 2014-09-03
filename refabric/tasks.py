import fabric.state
from fabric.tasks import execute
from fabric.utils import warn, abort

from .state import blueprints, load_blueprints


def dispatch(env_name, *args, **kwargs):
    """
    Activate env, set role(s) and dispatch tasks
    """
    _tasks = args
    _roles = kwargs.pop('roles', None)

    # Switch env
    # TODO: Don't switch env here, wrap task-loop to ensure roledefs/blueprints per task
    fabric.state.switch_env(env_name)

    # Use all roles from roledefs in given env, if not passed as kwarg
    if _roles is None:
        _roles = fabric.state.env.get('roledefs', {}).keys()
    else:
        # Apply role settings
        for _role in _roles:
            definitions = fabric.state.env.roledefs.get(_role, {})

            # Ensure dict style role definitions
            if not isinstance(definitions, dict):
                abort('Roledefs must be dict style objects')

            if fabric.state.env.merge_states:
                fabric.state.env.merge(definitions)
            else:
                fabric.state.env.update(definitions)

    # Activate role(s)
    fabric.state.env.roles = _roles

    # Load (new) blueprints from given env
    load_blueprints()

    # Dispatch task arguments as task forwards; role@env:blueprint.task -> role@env blueprint.task
    for _task in _tasks:
        if '.' in _task:
            # Execute specific task, i.e. :blueprint.task
            execute(_task)
        else:
            # Execute task on all blueprints, i.e. :task -> a.task, b.task, c.task
            for blueprint, executables in blueprints.items():
                executable = executables.get(_task)
                if executable:
                    execute(executable)
                else:
                    warn('Task "{task}" not part of blueprint "{blueprint}"'.format(task=_task,
                                                                                    blueprint=blueprint))
