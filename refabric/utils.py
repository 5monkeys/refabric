from fabric.utils import warn, abort, puts
from refabric.colors import yellow, green

__all__ = ['warn', 'abort', 'info']


def info(text, *args, **kwargs):
    args = (yellow(arg) for arg in args)
    kwargs = {key: yellow(value) for key, value in kwargs.items()}
    text = text.format(*args, **kwargs)
    if not text.startswith(' '):
        text = green(text)
    puts(text)
