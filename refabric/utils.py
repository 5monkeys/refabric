from fabric.utils import puts

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
