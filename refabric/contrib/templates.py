import difflib
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

IGNORED_FILES = ['.DS_Store']
RAW_EXT = '.__raw__'


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
        if source.startswith('./'):
            source = source[2:]
        templates = jinja_env.loader.list_templates()
        templates = [template for template in templates
                     if template.startswith(source)
                     and os.path.basename(template) not in IGNORED_FILES]

        if not templates:
            # No templates is found
            puts(indent(magenta('No templates found')))
            return

        dotfiles = []
        notdotfiles = False
        for template in templates:
            rel_template_path = template[len(source):]
            is_raw = rel_template_path.endswith(RAW_EXT)
            if is_raw:
                rel_template_path = rel_template_path[:-len(RAW_EXT)]
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

                skip = False
                while True:
                    answer = prompt('Type "yes" to overwrite, "diff" to '
                                    'show diff, or "no" to skip:',
                                    default='no', validate='yes|diff|no')
                    if answer == 'diff':
                        if is_raw:
                            warn('Cannot show diff yet, not implemented '
                                 'for raw files.')
                        else:
                            new = jinja_env.get_template(template).render(
                                **context or {})
                            new = new.encode('utf-8')
                            with quiet():
                                cur = run('cat {file}'.format(
                                    file=abs_destination_file))
                            df = difflib.unified_diff(
                                cur.replace('\r', '').splitlines(True),
                                new.splitlines(True),
                                'current', 'new')
                            warn(''.join(df))

                    else:
                        if answer == 'no':
                            # Skip render and upload of md5 mismatched file
                            skip = True
                        break
                if skip:
                    continue

            try:
                # Write rendered template to local temp dir
                rendered_template = os.path.join(tmp_dir, rel_template_path)

                if is_raw:
                    for tpl_base in jinja_env.loader.searchpath:
                        tpl_path = os.path.join(tpl_base, template)
                        if os.path.exists(tpl_path):
                            shutil.copy(tpl_path, rendered_template)
                            break
                else:
                    text = jinja_env.get_template(template).render(**context or {})
                    text = text.encode('utf-8')

                    with file(rendered_template, 'w+') as f:
                        f.write(text)
                        f.write(os.linesep)  # Add newline at end removed by jinja

                if rel_template_path[0] == '.':
                    dotfiles.append(rendered_template)
                else:
                    notdotfiles = True

            except UnicodeDecodeError:
                warn('Failed to render template "{}"'.format(template))

        with silent(), abort_on_error():
            # Upload rendered templates to remote temp dir
            remote_tmp_dir = run('mktemp -d').stdout
            run('chmod -R 777 {}'.format(remote_tmp_dir))
            try:
                if notdotfiles:
                    put(os.path.join(tmp_dir, '*'), remote_tmp_dir, use_sudo=True)
                for dotfile in dotfiles:
                    put(dotfile, remote_tmp_dir, use_sudo=True)

                # Set given permissions on remote before sync
                group = group or user or 'root'
                owner = user or 'root'
                owner = '{}:{}'.format(owner, group) if group else owner
                run('chown -R {} "{}"'.format(owner, remote_tmp_dir))

                # Clean destination
                if len(templates) > 1 or templates[0].endswith(os.path.sep):
                    destination = destination.rstrip(os.path.sep) + os.path.sep

                # Sync templates from remote temp dir to remote destination
                remote_tmp_dir = os.path.join(remote_tmp_dir,
                                              '' if dotfiles else '*')
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

                    if destination.endswith(os.path.sep) or is_dir(destination):
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


def is_dir(path):
    return run('test -d %s && echo OK ; true' % path).endswith('OK')


def get_jinja_helpers():
    from ..utils.socket import format_socket
    return locals()