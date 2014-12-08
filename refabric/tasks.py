from fabric.context_managers import settings
from fabric.utils import abort

from .state import blueprints
from .utils import info


def help_task(blueprint_name=None):
    """
    Display blueprint help

    :param blueprint_name: Blueprint name
    """
    if not blueprint_name:
        abort('No blueprint provided, example: $ fab help:python')

    blueprint = blueprints.get(blueprint_name)
    if not blueprint:
        abort('Unknown blueprint "{}", using correct role?'.format(blueprint_name))

    help(blueprint['__module__'])


def init_task(blueprint_name=None):
    """
    Copy template structure from blueprint defaults.

    :param blueprint_name: Blueprint name
    """
    if not blueprint_name:
        abort('No blueprint provided, example: $ fab init:memcached')

    blueprint = blueprints.get(blueprint_name)
    if not blueprint:
        abort('Unknown blueprint "{}", using correct role?'.format(blueprint_name))

    module = blueprint['__module__']
    if hasattr(module, 'blueprint'):
        module.blueprint.inherit_templates()

    if module.__doc__:
        info('Help: {}', module.blueprint.name)
        print module.__doc__


def _execute(task, host, my_env, args, kwargs, jobs, queue, multiprocessing):
    """
    Patched version of fabric.tasks._execute.
    Wraps original with `effective_roles` as `roles` in env to apply definitions.
    """
    with settings(roles=my_env['effective_roles']):
        return _execute.original(task, host, my_env, args, kwargs, jobs, queue, multiprocessing)
