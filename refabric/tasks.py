import fabric.state
from fabric.tasks import execute
from fabric.utils import warn

from .state import blueprints, load_blueprints


def dispatch(env_name, role, *args):
    """
    Activate env, set role and dispatch tasks
    """
    # Activate role
    fabric.state.env.roles = [role]

    # Switch env
    # TODO: Don't switch env here, wrap task-loop to ensure roledefs/blueprints per task
    fabric.state.switch_env(env_name)

    # Re-activate role if unintended set when merging env state or role definition
    fabric.state.env.roles = [role]

    # Load (new) blueprints from given env
    load_blueprints()

    # Dispatch task arguments as task forwards; role@env:blueprint.task -> role@env blueprint.task
    for _task in args:
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
