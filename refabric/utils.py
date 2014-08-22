from fabric.utils import puts

from .colors import yellow, green

__all__ = ['info']


def info(text, *args, **kwargs):
    args = (yellow(arg) for arg in args)
    kwargs = {key: yellow(value) for key, value in kwargs.items()}
    text = text.format(*args, **kwargs)
    if not text.startswith(' '):
        text = green(text)
    puts(text)
