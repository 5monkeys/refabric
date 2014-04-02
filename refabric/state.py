from functools import partial
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


def resolve(path=None, prefix=None, default=None):
    """
    Fabric env lookup helper with deep dot notation, parent fallback and variable resolving
    """
    try:
        # Prefix path
        if prefix:
            if path:
                path = '.'.join((prefix, path))
            else:
                path = prefix

        # Crawl env with path; a.b.c.edge -> env[a][b][c][edge]
        nodes = path.split('.')
        value = reduce(lambda d, k: d[k], nodes, fabric.state.env)

    except KeyError:
        if len(nodes) == 1:
            # Only non-existing edge left; return default
            value = default
        else:
            # Try edge parent, a.b.c.edge -> a.b.edge
            nodes = tuple(nodes)
            path = '.'.join(nodes[:-2] + nodes[-1:])
            value = resolve(path, default=default)

    if isinstance(value, basestring):
        if value:
            # Resolve internal variables; $(...)
            resolve_var = lambda v, m: v.replace(m.group(0), resolve(m.group(1), default=default))
            value = reduce(resolve_var, VAR_PATTERN.finditer(value), value)

        if value:
            value = value.strip()

    return value


blueprint_settings = lambda module: partial(resolve, prefix='settings.{}'.format(module.rsplit('.')[-1]))
