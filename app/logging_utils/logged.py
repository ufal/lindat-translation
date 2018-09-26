import functools, logging
from pprint import pformat


class LoggedDecorator(object):
    """Logging decorator that allows you to log with a
specific logger.
"""
    # Customize these messages
    ENTRY_MESSAGE = 'Entering {}'
    EXIT_MESSAGE = 'Exiting {}'
    RETURNS_MESSAGES = 'Returns >>{}<<'

    def __init__(self, logger=None):
        self.logger = logger

    def __call__(self, func):
        """Returns a wrapper that wraps func.
The wrapper will log the entry and exit points of the function
with logging.INFO level.
"""
        # set logger if it was not set earlier
        if not self.logger:
            formatter = logging.Formatter('%(asctime)s %(levelno)s %(name)s @ %(message)s')
            self.logger = logging.getLogger(func.__module__)
            self.logger.setLevel(logging.INFO)
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            console.setLevel(logging.INFO)
            self.logger.addHandler(console)

        @functools.wraps(func)
        def wrapper(*args, **kwds):
            self.logger.info(self.ENTRY_MESSAGE.format(func.__name__))
            f_result = func(*args, **kwds)
            self.logger.info(self.RETURNS_MESSAGES.format(pformat(f_result)))
            self.logger.info(self.EXIT_MESSAGE.format(func.__name__))
            return f_result
        return wrapper
