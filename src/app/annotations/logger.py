import logging
from functools import wraps

def log_params(cls):    # noqa
    original_method = getattr(cls, "get_pipeline", None)
    if original_method is None:
        return cls

    @wraps(original_method)
    def wrapped_method(self, *args, **kwargs):
        logger = logging.getLogger(cls.__module__)
        logger.log(logging.INFO, f"Loading data for {self.__class__.__name__} with args: {args}, kwargs: {kwargs}")
        result = original_method(self, *args, **kwargs)
        return result

    setattr(cls, "get_pipeline", wrapped_method)
    return cls

def inject_logger(func):
    logger_name = f"{func.__module__}.{func.__qualname__}"
    logger = logging.getLogger(logger_name)

    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'logger' not in kwargs:
            kwargs['logger'] = logger
        return func(*args, **kwargs)
    return wrapper