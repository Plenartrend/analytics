import functools
import inspect
import logging

LOGGER = logging.getLogger(__name__)

class Router:
    def __init__(self):
        self._store = {}

    def route(self, event: str):
        def decorator(func):
            LOGGER.log(logging.INFO, f"Adding route for {event}")

            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            if not func.__annotations__ or (
                    'return' in func.__annotations__ and (len(func.__annotations__) - 1) != len(param_names)) or (
                    'return' not in func.__annotations__ and len(func.__annotations__) != len(param_names)):
                self._store[event] = func
                return func

            first_arg_name = next(iter(func.__annotations__))
            datatype_to_cast = func.__annotations__[first_arg_name]

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                casted_arg = datatype_to_cast(**args[0])
                return_value = await func(casted_arg, **kwargs)
                if return_value:
                    return_value()

            self._store[event] = wrapper

            return wrapper

        return decorator
