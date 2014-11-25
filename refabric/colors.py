from contextlib import contextmanager
from functools import partial


def _wrap_with(code):

    def inner(text, bold=False, end=None):
        c = code
        if bold:
            c = "1;%s" % c

        global current
        end_color = end or current or '0'

        wrapped = "\033[%sm%s\033[%sm" % (c, text, end_color)

        return wrapped

    @contextmanager
    def color():
        global current
        previous = current
        current = code
        yield partial(inner, end=previous)
        current = previous

    inner.color = color

    # inner.color = code
    return inner


grey = _wrap_with('0')
red = _wrap_with('31')
green = _wrap_with('32')
yellow = _wrap_with('33')
blue = _wrap_with('34')
magenta = _wrap_with('35')
cyan = _wrap_with('36')
white = _wrap_with('37')

current = '0'
