from copy import copy
from re import compile
from fabric.context_managers import settings

import fabric.state
from fabric.main import load_tasks_from_module, _task_names
from fabric.utils import abort


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

    for package in packages:
        # Import blueprint module
        package = str(package)
        blueprint = package.rsplit('.', 1)[-1]

        if blueprint not in blueprints:
            imported = __import__(package)

            # Load tasks
            _, new_style, classic, _ = load_tasks_from_module(imported)
            tasks = new_style if fabric.state.env.new_style_tasks else classic

            if tasks:
                # Prefix top level imports with module/blueprint name
                if not '.' in package:
                    tasks = {blueprint: tasks}

                callables.update(tasks)
                executables[blueprint] = dict((name.split('.', 1)[-1], name) for name in _task_names(tasks))

            executables[blueprint]['__module__'] = __import__(package, fromlist=[package])

    # Update available tasks for fabric
    fabric.state.commands.update(callables)

    # Update available blueprints
    blueprints.update(executables)


def switch_env(name='default'):
    """
    Patched version of fabric.state.switch_env.
    Switches env as intended, but also applies current role(s) definitions into env.
    """
    from refabric.state import apply_role_definitions
    switch_env.original(name=name)
    if fabric.state.env.roles:
        apply_role_definitions(fabric.state.env.roles[0], force=True)


def apply_role_definitions(role, force=False):
    """
    Merge or update role(s) definitions into env
    """
    # Restore old env state
    if not force and '_current' in fabric.state.env.states:
        current_state = fabric.state.env.states.pop('_current')
        fabric.state.env.clear()
        fabric.state.env.update(current_state)

    definitions = fabric.state.env.roledefs.get(role, {})

    # Ensure dict style role definitions
    if not isinstance(definitions, dict):
        abort('Roledefs must be dict style objects')

    # Remember current env state
    fabric.state.env.states['_current'] = fabric.state.env.copy()

    if fabric.state.env.merge_states:
        fabric.state.env.merge(definitions)
    else:
        fabric.state.env.update(definitions)

    load_blueprints()
