import jinja2
import importlib
import os
from functools import partial

from fabric.contrib import files
from fabric.state import env

from .templates import upload
from ..context_managers import sudo
from ..utils import info

__all__ = ['get']


def get(blueprint):
    return Blueprint(blueprint)


class Blueprint(object):

    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.name = blueprint.rsplit('.')[-1]
        self.settings = partial(env.resolve, prefix='settings.{}'.format(self.name))

    def get(self, setting, default=None):
        return self.settings(setting, default=default)

    def get_template_path(self, relative_path, role=None):
        deploy_root = env['real_fabfile']
        path = [os.path.dirname(deploy_root), 'templates']
        if not role:
            role = env.roles[0] if env.roles else None  # TODO: Is this safe?
            if role:
                path.append(role)
        path.append(self.name)
        path.append(relative_path)
        return os.path.join(*path)

    def get_template_loader(self):
        role = env.roles[0] if env.roles else None  # TODO: Is this safe?
        return BlueprintTemplateLoader(self.blueprint, role=role)

    def get_jinja_env(self):
        return jinja2.Environment(loader=self.get_template_loader())

    def render_template(self, template, context=None):
        text = self.get_jinja_env().get_template(template).render(**context or {})
        text = text.encode('utf-8')
        return text

    def upload(self, template, destination, context=None, user=None, group=None):
        info('Uploading templates: {}', template)
        jinja_env = self.get_jinja_env()
        context = context or {}
        context['hosts'] = env.hosts
        context['env'] = env.shell_env
        with sudo('root'):
            return upload(template, destination, context=context, user=user, group=group,
                          jinja_env=jinja_env)

    def download(self, remote_path, rel_destination_path, role=None):
        """
        Currently only supports downloading single file
        """
        destination_path = self.get_template_path(rel_destination_path)

        # Append filename to destination if missing
        filename = os.path.basename(remote_path)
        if os.path.basename(destination_path) != filename:
            destination_path = os.path.join(destination_path, filename)

        with sudo('root'):
            info('Downloading {} -> {}', remote_path, destination_path)
            files.get(remote_path, destination_path)


class BlueprintTemplateLoader(jinja2.FileSystemLoader):

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
