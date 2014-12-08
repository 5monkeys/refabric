from fabric.utils import puts, _AttributeDict

from .colors import green, yellow

__all__ = ['info']


def info(text, *args, **kwargs):
    with green.color() as color:
        if not text.startswith(' '):
            text = color(text)

        args = (yellow(arg) for arg in args)
        kwargs = {key: yellow(value) for key, value in kwargs.items()}
        text = text.format(*args, **kwargs)

        puts(text)


def env_setitem(self, key, value):
    """
    Patched version of fabric.utils._AttributeDict.__setitem__.
    Catch set of `roles` and apply definitions into env.
    """
    super(_AttributeDict, self).__setitem__(key, value)

    if key == 'roles' and value:
        from refabric.state import apply_role_definitions
        apply_role_definitions(value[0])
