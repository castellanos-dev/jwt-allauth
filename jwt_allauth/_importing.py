from importlib import import_module


def import_callable(path_or_callable):
    if hasattr(path_or_callable, '__call__'):
        return path_or_callable

    if not isinstance(path_or_callable, str):
        raise TypeError('Expected a callable or dotted import path string')

    package, attr = path_or_callable.rsplit('.', 1)
    return getattr(import_module(package), attr)
