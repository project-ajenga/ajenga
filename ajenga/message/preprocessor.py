import re
import asyncio
from typing import Callable, Iterable, Any, Union, Pattern, Dict, List

from aiocqhttp import Event as CQEvent
from aiocqhttp.message import escape, unescape, Message, MessageSegment

from ajenga import Ajenga, get_bot
from ajenga.log import logger

_preprocessors = dict()


def message_preprocessor(name: str) -> Callable:
    """Decorator builder for defining message preprocessor

    Args:
        name (str): preprocessor name, unique

    Returns:
        Callable: decorator
    """
    def deco(func: Callable) -> Any:
        if name in _preprocessors:
            if get_bot().config.MESSAGE_PREPROCESSOR_ALLOW_REPLACE:
                logger.warning(f"Message Preprocessor {name} already exists, replacing")
                _preprocessors[name] = func
            else:
                logger.error(f"Message Preprocessor {name} already exists, ignoring")
        else:
            _preprocessors[name] = func
            logger.info(f"Message Preprocessor {name} loaded")
        return func

    return deco


def unsubscribe_preprocessor(name: str):
    """Unsubscribe message preprocessor

    Args:
        name (str): preprocessor name, unique

    Returns:

    """
    if name in _preprocessors:
        del _preprocessors[name]
    else:
        logger.error(f"Preprocessor {name} not exist")


def get_preprocessors() -> Dict[str, Callable]:
    return _preprocessors


class MessagePreprocessorSolver:
    """
    Executing all message preprocessors and handling get operation
    """
    _tasks: Dict[str, asyncio.Future]

    def __init__(self, short=False):
        self.short = short
        self._tasks = {}

    async def get(self, preprocessor: str, *args) -> None:
        if preprocessor in self._tasks:
            if not self._tasks[preprocessor].done():
                if self.short:
                    logger.error(f'Cyclic preprocessor dependencies detected when processing {preprocessor}!')
                    raise ValueError('Cyclic preprocessor dependency detected !')
                elif get_bot().config.MESSAGE_PREPROCESSOR_CYCLIC_WARNING:
                    logger.warning(
                        f'Possible cyclic preprocessor dependencies detected when processing {preprocessor}!')
        else:
            self._tasks[preprocessor] = asyncio.ensure_future(_preprocessors[preprocessor](*args))
        await self._tasks[preprocessor]
