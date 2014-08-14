import fabric.state
from fabric.main import load_tasks_from_module, _task_names
from re import compile


VAR_PATTERN = compile('\$\((.+?)\)')
blueprints = {}


def load_blueprints(packages=None):
    """
    Load blueprints/tasks from fabric env
    """
    callables = {}
    executables = {}

    # Fallback on blueprints from env
    packages = packages or fabric.state.env.get('blueprints') or []

    #with python_path():
    for package in packages:
        # Import blueprint module
        package = str(package)
        blueprint = package.rsplit('.', 1)[-1]
        imported = __import__(package)

        # Load tasks
        _, new_style, classic, _ = load_tasks_from_module(imported)
        tasks = new_style if fabric.state.env.new_style_tasks else classic

        if tasks:
            # Prefix top level imports with module/blueprint name
            if not package:
                tasks = {blueprint: tasks}

            callables.update(tasks)
            executables[blueprint] = dict((name.split('.', 1)[-1], name) for name in _task_names(tasks))

    # Update available tasks for fabric
    fabric.state.commands.update(callables)

    # Update available blueprints
    blueprints.update(executables)
