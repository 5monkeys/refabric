import os
from fabric.context_managers import quiet
import jinja2
import shutil
import tempfile
from functools import partial

from fabric.colors import magenta
from fabric.operations import put, prompt
from fabric.utils import abort, puts, indent, warn

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
        return iter(FileDescriptor(os.path.join(self, fd))
                    for fd in os.listdir(self))


def upload(source, destination, context=None, user=None, group=None,
           jinja_env=None):
    """
    Will render and upload a local file or folder to a destination file or
    folder.
    Destination is handled as a folder if it ends with a slash,
    otherwise as a file and therefore could be used to rename template on
    upload.

    :param source: Path to local file or folder.
    :param destination: Absolute destination path. Folders always end with a
        slash.
    :param context: Context to render source template.
    :param user: User owner of destination file/folder
    :param group: Group owner of destination file/folder
    :param jinja_env: Jinja2 Environment to load templates from.
    :return: List of updated files
    """
    info('Uploading templates: {}',
         os.path.basename(source.rstrip(os.path.sep)))

    tmp_dir = tempfile.mkdtemp()

    jinja_env.globals.update(get_jinja_helpers())

    try:
        # TODO: Handle None template_loader

        # Filter wanted templates
        source = source.lstrip('./')
        templates = jinja_env.loader.list_templates()
        templates = [template for template in templates
                     if template.startswith(source)]

        if not templates:
            # No templates is found
            puts(indent(magenta('No templates found')))
            return

        for template in templates:
            rel_template_path = template[len(source):]
            if os.path.sep in rel_template_path:
                # Create directories for template
                rel_template_dir = os.path.dirname(rel_template_path)
                template_dir = os.path.join(tmp_dir, rel_template_dir)
                if not os.path.exists(template_dir):
                    os.makedirs(template_dir)
            else:
                # Single template
                rel_template_path = os.path.basename(template)

            # Render template
            context = context or {}
            context['n'] = os.path.splitext(os.path.basename(template))[0]

            abs_destination_file = destination
            if destination.endswith(os.path.sep):
                abs_destination_file = os.path.join(destination,
                                                    rel_template_path)

            # Check md5sum of file present on sure with checksum generated on
            # last upload
            with quiet():
                md5_output = run('md5sum -c --status {file}.md5'
                                 ' || test ! -e {file}.md5'
                                 .format(file=abs_destination_file))
            if md5_output.return_code != 0:
                warn('Template "{}" checksum mismatch. File changed since last'
                     ' upload.'.format(template))
                answer = prompt('Type "yes" to overwrite, or "no" to skip:',
                                default='no', validate='yes|no')
                if answer == 'no':
                    # Skip render and upload of md5 mismatched file
                    continue

            try:
                text = jinja_env.get_template(template).render(**context or {})
                text = text.encode('utf-8')

                # Write rendered template to local temp dir
                rendered_template = os.path.join(tmp_dir, rel_template_path)
                with file(rendered_template, 'w+') as f:
                    f.write(text)
                    f.write(os.linesep)  # Add newline at end removed by jinja

            except UnicodeDecodeError:
                warn('Failed to render template "{}"'.format(template))

        with silent(), abort_on_error():
            # Upload rendered templates to remote temp dir
            remote_tmp_dir = run('mktemp -d').stdout
            run('chmod -R 777 {}'.format(remote_tmp_dir))
            try:
                put(os.path.join(tmp_dir, '*'), remote_tmp_dir, use_sudo=True)

                # Set given permissions on remote before sync
                group = group or user or 'root'
                owner = user or 'root'
                owner = '{}:{}'.format(owner, group) if group else owner
                run('chown -R {} "{}"'.format(owner, remote_tmp_dir))

                # Clean destination
                if len(templates) > 1 or templates[0].endswith(os.path.sep):
                    destination = destination.rstrip(os.path.sep) + os.path.sep

                # Sync templates from remote temp dir to remote destination
                remote_tmp_dir = os.path.join(remote_tmp_dir, '*')
                cmd = 'rsync -rcbiog --out-format="%n" {tmp_dir} {dest}'.format(
                    tmp_dir=remote_tmp_dir,
                    dest=destination)
                updated = run(cmd)

            finally:
                # Remove temp upload dir after sync to final destination
                run('rm -rf {}'.format(remote_tmp_dir))

            updated_files = [line.strip()
                             for line in updated.stdout.split('\n')
                             if line]
            updated_files = [f for f in updated_files
                             if os.path.isfile(os.path.join(tmp_dir, f))]

            if updated_files:
                for updated_file in updated_files:
                    updated_file_path = destination

                    if destination.endswith(os.path.sep):
                        updated_file_path = os.path.join(destination,
                                                         updated_file)
                    else:
                        updated_file = os.path.basename(destination)

                    info(indent('Uploaded: {}'), updated_file)
                    # Create md5 checksum of uploaded file
                    run('md5sum {file} > {file}.md5'
                        .format(file=updated_file_path))
            else:
                puts(indent('(no changes found)'))

            return updated_files

    except jinja2.TemplateNotFound as e:
        abort('Templates not found: "{}"'.format(e))
    finally:
        shutil.rmtree(tmp_dir)


def get_jinja_helpers():
    from ..utils.socket import format_socket
    return locals()