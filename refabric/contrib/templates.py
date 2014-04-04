import os
import shutil
import tempfile
from fabric.colors import magenta
from fabric.operations import put
from fabric.utils import abort, puts, indent
from functools import partial
from jinja2 import Environment, TemplateNotFound
from .debian import chown
from ..context_managers import silent, abort_on_error
from ..operations import run
from ..utils import info


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


def upload(source, destination, context=None, user=None, group=None, template_loader=None):
    """

    """
    tmp_dir = tempfile.mkdtemp()
    try:
        # Create jinja environment
        jinja_env = Environment(loader=template_loader)  # TODO: Handle None template_loader

        # Filter wanted templates
        templates = jinja_env.loader.list_templates()
        templates = [template for template in templates if template.startswith(source)]
        # No templates is found
        if not templates:
            puts(indent(magenta('No templates found')))
            return

        for template in templates:
            if source.endswith(os.path.sep):
                # Directory tree of templates
                template_path = template[len(source):]
                if os.path.sep in template_path:
                    template_rel_dir = os.path.dirname(template_path)
                    template_dir = os.path.join(tmp_dir, template_rel_dir)
                    if not os.path.exists(template_dir):
                        os.makedirs(template_dir)
            else:
                # Single template
                template_path = os.path.basename(template)

            # Render template
            context = context or {}
            context['n'] = os.path.splitext(os.path.basename(template))[0]
            text = jinja_env.get_template(template).render(**context or {})
            text = text.encode('utf-8')

            # Write rendered template to local temp dir
            rendered_template = os.path.join(tmp_dir, template_path)
            with file(rendered_template, 'w+') as f:
                f.write(text)
                f.write(os.linesep)  # Add newline at end removed by jinja

        with silent(), abort_on_error():
            # Upload rendered templates to remote temp dir
            remote_tmp_dir = run('mktemp -d').stdout
            put(os.path.join(tmp_dir, '*'), remote_tmp_dir, use_sudo=True)

            # Set given permissions on remote before sync
            chown(remote_tmp_dir, owner=user or 'root', group=group or user or 'root',
                  recursive=True)

            # Clean destination
            destination = destination.rstrip(os.path.sep) + os.path.sep

            # Sync templates from remote temp dir to remote destination
            remote_tmp_dir = os.path.join(remote_tmp_dir, '*')
            cmd = 'rsync -rcbi --out-format="%n" {tmp_dir} {dest} && rm -r {tmp_dir}'.format(
                tmp_dir=remote_tmp_dir,
                dest=destination)
            updated = run(cmd)

            updated_files = [line.strip() for line in updated.stdout.split('\n') if line]
            if updated_files:
                for updated_file in updated_files:
                    info(indent('Uploaded: {}'), updated_file)
            else:
                puts(indent('(no changes found)'))

            return updated_files

    except TemplateNotFound as e:
        abort('Templates not found: "{}"'.format(e))
    finally:
        shutil.rmtree(tmp_dir)
