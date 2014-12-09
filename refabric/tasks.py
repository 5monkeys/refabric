import fabric.state
from fabric.context_managers import settings
from fabric.operations import prompt
from fabric.tasks import requires_parallel
from fabric.utils import abort

from .colors import green
from .state import blueprints
from .utils import info


class Task(object):

    @staticmethod
    def get_hosts_and_effective_roles(self, arg_hosts, arg_roles, arg_exclude_hosts, env=None):
        all_hosts, effective_roles = Task.get_hosts_and_effective_roles.original(self,
                                                                                 arg_hosts=arg_hosts,
                                                                                 arg_roles=arg_roles,
                                                                                 arg_exclude_hosts=arg_exclude_hosts,
                                                                                 env=env)
        # Prompt hosts if more than 1
        if fabric.state.env.prompt_hosts and len(all_hosts) > 1 and not requires_parallel(self):
            print("0. All")
            for i, host in enumerate(all_hosts, start=1):
                print("{i}. {host}".format(i=i, host=host))
            valid_indices = '[,0-%s]+' % len(all_hosts)
            host_choice = prompt(green('Select host(s)'), default='0', validate=valid_indices)
            indices = map(int, host_choice.split(','))
            if len(indices) > 1 or indices[0] > 0:
                all_hosts = [all_hosts[i-1] for i in indices if i > 0]

        return all_hosts, effective_roles


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
