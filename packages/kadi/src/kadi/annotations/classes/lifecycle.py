from typing import Callable, Type


class Lifecycle:

    def __init__(self):
        self._store = {}

    def on_open(self):
        def annotation(func: Callable):
            self._store["on_open"] = func
            return func

        return annotation

    def on_close(self):
        def annotation(func: Callable):
            self._store["on_close"] = func
            return func

        return annotation

    def exceptionhandler(self, exception: Type[Exception] = Exception):
        def decorator(func):
            if "on_error" in self._store:
                current_handler = self._store["on_error"]
                self._store["on_error"] = \
                    lambda error: current_handler(error) if isinstance(error, exception) else func(error)
            else:
                self._store["on_error"] = \
                    lambda error: func(error) if isinstance(error) else None

        return decorator
