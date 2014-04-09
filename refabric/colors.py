last_color_code = '0'


def _wrap_with(code):

    def inner(text, bold=False):
        c = code
        if bold:
            c = "1;%s" % c

        global last_color_code
        wrapped = "\033[%sm%s\033[%sm" % (c, text, last_color_code)
        return wrapped

    return inner


grey = _wrap_with('0')
red = _wrap_with('31')
green = _wrap_with('32')
yellow = _wrap_with('33')
blue = _wrap_with('34')
magenta = _wrap_with('35')
cyan = _wrap_with('36')
white = _wrap_with('37')
