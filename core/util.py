import logging
import traceback

from abc import ABCMeta
from logging import Logger

logger: logging.Logger = logging.getLogger(__name__)


class SingletonMeta(ABCMeta):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def log_error(logger_p: Logger, message: str, ex: Exception) -> None:
    logger_p.error(format_message(message, ex))


def log_warning(logger_p: Logger, message: str, ex: Exception) -> None:
    logger_p.warning(format_message(message, ex))


def format_message(message: str, ex: Exception) -> str:
    return "{} Erro: {}/{},{}".format(message, type(ex).__name__, ex, traceback.format_exception(ex))
