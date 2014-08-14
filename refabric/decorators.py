from functools import wraps
from . import context_managers as ctx


def sudo(func, user=None):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with ctx.sudo(user=user):
            return func(*args, **kwargs)
    return wrapper
