import re
from fabric.utils import puts

from .colors import grey, green, yellow

__all__ = ['info']


def info(text, *args, **kwargs):
    clr = grey if text.startswith(' ') else green
    with clr.color() as color:
        text = color(text)
        args = [yellow(arg) for arg in args]
        kwargs = {key: yellow(value) for key, value in kwargs.items()}
        text = text.format(*args, **kwargs)

        puts(text)


class _AttributeDict(object):
    """
    Patched version (mixin) of fabric.utils._AttributeDict.
    """

    @staticmethod
    def __setitem__(self, key, value):
        """
        Catch set of key `roles` and apply related definitions into env.
        """
        _AttributeDict.__setitem__.original(self, key, value)

        if key == 'roles' and value:
            from refabric.state import apply_role_definitions
            apply_role_definitions(value[0])


def resolve(dikt, path=None, prefix=None, default=None):
    """
    Dict path lookup helper with deep dot notation, parent fallback and variable expansion.
    """
    try:
        # Prefix path; a.b + c -> a.b.c
        if prefix:
            if path:
                path = '.'.join((prefix, path))
            else:
                path = prefix

        # Crawl path; a.b.c.edge -> env[a][b][c][edge]
        nodes = path.split('.')

        def crawl(container, key):
            if isinstance(container, dict):
                return container[key]
            elif isinstance(container, list):
                return container[int(key)]
            else:
                raise KeyError(key)

        value = reduce(crawl, nodes, dikt)

    except KeyError:
        if len(nodes) == 1:
            # Only non-existing edge left; return default
            value = default
        else:
            # Try edge parent, a.b.c.edge -> a.b.edge
            nodes = tuple(nodes)
            path = '.'.join(nodes[:-2] + nodes[-1:])
            value = resolve(dikt, path, default=default)

    if isinstance(value, basestring):
        # Value is string, expand internal variables if found; $(...)
        if value:
            resolve_var = lambda v, m: v.replace(m.group(0), resolve(dikt, m.group(1), default=default))
            value = reduce(resolve_var, re.finditer('\$\((.+?)\)', value), value)

        if value:
            value = value.strip()

    elif isinstance(value, dict):
        # Value is dict, resolve item values to ensure variable expansion
        for item_key, item_value in value.iteritems():
            item_path = '.'.join((path, item_key))
            value[item_key] = resolve(dikt, item_path)

    elif isinstance(value, list):
        # Value is list, resolve items to ensure variable expansion
        for i, list_value in enumerate(value):
            index_path = '.'.join((path, str(i)))
            value[i] = resolve(dikt, index_path)

    return value
