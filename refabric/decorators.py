from functools import wraps
from . import context_managers as ctx


def sudo(func, user=None):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with ctx.sudo(user=user):
            return func(*args, **kwargs)
        # set_sudo_context()
        # if not 'use_sudo' in kwargs:
        #     from .api import env
        #     kwargs['use_sudo'] = env.sudo_forced
        # result = func(*args, **kwargs)
        # restore_sudo_context()
        # return result
    return wrapper
