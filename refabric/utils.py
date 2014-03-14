from fabric.utils import warn, abort, puts
from fabric.colors import *

__all__ = ['warn', 'abort', 'info']


def info(text, *args, **kwargs):
    args = (yellow(arg) for arg in args)
    kwargs = {key: yellow(value) for key, value in kwargs.items()}
    puts(green(text.format(*args, **kwargs)))
