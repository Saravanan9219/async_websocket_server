#! /bin/python3

from functools import wraps


def coroutine(func):
    @wraps(func)
    def inner_func(*args, **kwargs):
        generator = func(*args, **kwargs)
        try:
            generator.send(None)
        except StopIteration:
            pass
        return generator
    return inner_func

