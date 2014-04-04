from functools import partial
import importlib
import os
from fabric.state import env
from jinja2 import FileSystemLoader
from .templates import upload
from ..context_managers import sudo
from ..state import resolve
from ..utils import info

__all__ = ['get']


def get(blueprint):
    return Blueprint(blueprint)


class Blueprint(object):

    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.name = blueprint.rsplit('.')[-1]
        self.settings = partial(resolve, prefix='settings.{}'.format(self.name))

    def get(self, setting):
        return self.settings(setting)

    def get_loader(self):
        role = env.roles[0] if env.roles else None  # TODO: Is this safe?
        return BlueprintTemplateLoader(self.blueprint, role=role)

    def upload(self, template, destination, context=None, user=None, group=None):
        info('Uploading templates: {}', template)
        template_loader = self.get_loader()
        context = context or {}
        context['hosts'] = env.hosts
        context['env'] = env.shell_env
        # TODO: Resolve all env values
        with sudo('root'):
            upload(template, destination, context=context, user=user, group=group,
                   template_loader=template_loader)


class BlueprintTemplateLoader(FileSystemLoader):

    def __init__(self, blueprint, role=None):
        blueprint_name = blueprint.rsplit('.')[-1]
        module = importlib.import_module(blueprint)
        blueprint_library_path = os.path.dirname(module.__file__)
        library_templates = os.path.join(blueprint_library_path, 'templates', blueprint_name)

        deploy_root = env['real_fabfile']
        dirs = [os.path.dirname(deploy_root), 'templates']
        if role:
            dirs.append(role)
        dirs.append(blueprint_name)
        user_templates = os.path.join(*dirs)

        super(BlueprintTemplateLoader, self).__init__([user_templates, library_templates])
