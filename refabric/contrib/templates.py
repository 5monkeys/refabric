import os
import shutil
import tempfile
from functools import partial
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from fabric.state import env
from fabric.operations import put
from .debian import chown
from ..context_managers import silent, sudo
from fabric.utils import abort
from ..operations import run
from ..utils import info


def blueprint_templates(blueprint_module):
    deploy_root = env['real_fabfile']
    blueprint_name = blueprint_module.rsplit('.')[-1]
    template_root = os.path.join(os.path.dirname(deploy_root), 'templates', blueprint_name)
    return FileDescriptor(template_root)


class FileDescriptor(str):

    def __getattr__(self, item):
        if hasattr(os.path, item):
            return partial(getattr(os.path, item), self)
        else:
            return super(FileDescriptor, self).__getattribute__(item)

    def __getitem__(self, item):
        if not self.isdir():
            raise OSError("Not a directory: '{}'".format(self))

        path = os.path.join(self, item)

        if not self.exists():
            raise OSError("Path does not exist: '{}'".format(path))

        return FileDescriptor(path)

    def __iter__(self):
        return iter(FileDescriptor(os.path.join(self, fd)) for fd in os.listdir(self))


def get_jinja_environment(blueprint):
    # TODO: Add blueprint defaults dir
    return Environment(loader=FileSystemLoader(blueprint))


def _render_templates(source, destination, context=None, jinja_env=None):
    jinja_env = jinja_env or get_jinja_environment(source)
    if os.path.isdir(source):
        if not os.path.exists(destination):
            os.mkdir(destination)

        for filename in os.listdir(source):
            _source = os.path.join(source, filename)
            _destination = os.path.join(destination, filename)
            _render_templates(_source, _destination, context, jinja_env)

    else:
        filename = os.path.basename(source)
        if os.path.isdir(destination):
            destination = os.path.join(destination, filename)
        template_path = os.path.relpath(source, jinja_env.loader.searchpath[0])  # TODO: Handle multiple
        context = context or {}
        context['name'] = os.path.splitext(filename)[0]
        context['hosts'] = env.hosts
        text = jinja_env.get_template(template_path).render(context)
        text = text.encode('utf-8')
        with file(destination, 'w+') as f:
            f.write(text)


def upload(source, destination, context=None, user=None, group=None):
    """

    """
    tmp_dir = tempfile.mkdtemp()
    is_single_file = not os.path.isdir(source)
    try:
        _render_templates(source, tmp_dir, context)
        with silent():
            remote_tmp_dir = run('mktemp -d').stdout
            put(os.path.join(tmp_dir, '*'), remote_tmp_dir, use_sudo=True)
            remote_tmp_dir += os.path.sep
            if is_single_file:
                remote_tmp_dir += os.path.basename(source)
            chown(remote_tmp_dir, owner=user or 'root', group=group or user or 'root',
                  recursive=True)
            cmd = 'rsync -acbi --out-format="%n" {tmp_dir} {dest} && rm -r {tmp_dir}'.format(
                tmp_dir=remote_tmp_dir,
                dest=destination)
            updated = run(cmd)

        updated_files = [line.strip() for line in updated.stdout.split('\n') if line]
        if is_single_file:
            if updated_files:
                # TODO: Print destination filename if not dir
                filename = os.path.basename(destination)
                info('Updated: {}', filename)
        else:
            for updated_file in updated_files:
                info('Updated: {}', updated_file)
        return updated_files
    except TemplateNotFound as e:
        abort('Templates not found: "{}"'.format(source))
    finally:
        shutil.rmtree(tmp_dir)
