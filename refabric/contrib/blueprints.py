import shutil
import jinja2
import importlib
import os
from functools import partial

from fabric.api import local
from fabric.contrib import files
from fabric.state import env
from fabric.utils import warn

from .templates import upload
from ..context_managers import sudo, silent, hide_prefix
from ..utils import info, resolve

__all__ = ['get']


def get(blueprint):
    return Blueprint(blueprint)


class Blueprint(object):

    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.name = blueprint.rsplit('.')[-1]
        self.settings = partial(resolve, env,
                                prefix='settings.{}'.format(self.name))

    def __contains__(self, item):
        return bool(self.settings(item))

    def get(self, setting, default=None):
        return self.settings(setting, default=default)

    def fetch(self, *settings):
        return {setting: self.get('setting') for setting in settings}

    def get_user_template_path(self, relative_path='', role=None):
        deploy_root = env['real_fabfile']
        path = [os.path.dirname(deploy_root), 'templates']
        if not role:
            role = env.roles[0] if env.roles else None  # TODO: Is this safe?
            if role:
                path.append(role)
        path.append(self.name)
        path.append(relative_path)
        return os.path.join(*path)

    def get_default_template_root(self):
        module = importlib.import_module(self.blueprint)
        blueprint_library_path = os.path.dirname(module.__file__)
        return os.path.join(blueprint_library_path, 'templates', self.name, '')

    def get_template_loader(self):
        role = env.roles[0] if env.roles else None  # TODO: Is this safe?
        return BlueprintTemplateLoader(self, role=role)

    def get_jinja_env(self):
        return jinja2.Environment(loader=self.get_template_loader())

    def render_template(self, template, context=None):
        text = self.get_jinja_env()\
            .get_template(template)\
            .render(**context or {})
        text = text.encode('utf-8')
        return text

    def upload(self, template, destination, context=None, user=None,
               group=None):
        jinja_env = self.get_jinja_env()
        context = context or {}
        context.setdefault('host', env.host_string)
        context['hosts'] = env.hosts
        context['env'] = env.shell_env
        context['state'] = env.state
        context['settings'] = self.get(None)
        with sudo('root'):
            return upload(template, destination, context=context, user=user,
                          group=group,
                          jinja_env=jinja_env)

    def download(self, remote_path, rel_destination_path, role=None):
        """
        Currently only supports downloading single file
        """
        destination_path = self.get_user_template_path(rel_destination_path,
                                                       role=role)

        # Append filename to destination if missing
        filename = os.path.basename(remote_path)
        if os.path.basename(destination_path) != filename:
            destination_path = os.path.join(destination_path, filename)

        with sudo('root'):
            info('Downloading {} -> {}', remote_path, destination_path)
            files.get(remote_path, destination_path)

    def inherit_templates(self, role=None):
        """
        Copy blueprint default templates to local working directory.
        If active role is present, a local top-level role directory will be
        created.

        Already existing templates that differs with default template will be
        skipped and a diff will be printed.

        :param role: Optional local role directory to output templates to.
        """
        source = self.get_default_template_root()
        destination = self.get_user_template_path(role=role)

        info('Inheriting blueprint templates...')
        for directory, _, templates in os.walk(source):
            rel_dir = directory[len(source):]
            for template in templates:
                origin = os.path.join(directory, template)
                template = os.path.join(rel_dir, template)
                clone = os.path.join(destination, template)
                if os.path.exists(clone):
                    with silent('warnings'):
                        diff = local('diff -uN {} {}'.format(clone, origin),
                                     capture=True)
                    if diff.failed:
                        warn('DIFF > Skipping template: {}'.format(template))
                        with hide_prefix():
                            info(diff)
                else:
                    clone_destination = os.path.join(destination, rel_dir)
                    if not os.path.exists(clone_destination):
                        os.makedirs(clone_destination)
                    shutil.copyfile(origin, clone)


class BlueprintTemplateLoader(jinja2.FileSystemLoader):

    def __init__(self, blueprint, role=None):
        # Blueprint default templates
        library_templates = blueprint.get_default_template_root()

        # Local user templates
        deploy_root = env['real_fabfile']
        dirs = [os.path.dirname(deploy_root), 'templates']
        if role:
            dirs.append(role)
        dirs.append(blueprint.name)
        user_templates = os.path.join(*dirs)

        # Optional extra templates
        env_templates = env.get('template_dirs', '')

        templates = [user_templates, library_templates]
        templates.extend(env_templates)

        super(BlueprintTemplateLoader, self).__init__(templates)
