import re
import asyncio
from typing import Callable, Iterable, Any, Union, Pattern, Dict, List

from aiocqhttp import Event as CQEvent
from aiocqhttp.message import escape, unescape, Message, MessageSegment

from ajenga import Ajenga, get_bot
from ajenga.log import logger

_processors = dict()


def message_processor(name: str) -> Callable:
    """Decorator builder for defining message processor

    Args:
        name (str): processor name, unique

    Returns:
        Callable: decorator
    """
    def deco(func: Callable) -> Any:
        if name in ['message', 'request', 'notice', 'meta_event']:
            logger.error(f"Message Processor can not be named {name}")
        elif name in _processors:
            if get_bot().config.MESSAGE_PROCESSOR_ALLOW_REPLACE:
                logger.warning(f"Message Processor {name} already exists, replacing")
                _processors[name] = func
            else:
                logger.error(f"Message Processor {name} already exists, ignoring")
        else:
            _processors[name] = func
            logger.info(f"Message Processor {name} loaded")
        return func

    return deco


def unsubscribe_processor(name: str):
    """Unsubscribe message processor

    Args:
        name (str): processor name, unique

    Returns:

    """
    if name in _processors:
        del _processors[name]
    else:
        logger.error(f"Processor {name} not exist")


class MessageProcessorSolver:
    """
    Executing all message processors and handling get operation
    """
    _tasks: Dict[str, asyncio.Future]

    def __init__(self, short=False):
        self.short = short
        self._tasks = {}

    async def get(self, processor: str, *args) -> List[Any]:
        if processor in self._tasks:
            if not self._tasks[processor].done():
                if self.short:
                    logger.error(f'Cyclic processor dependencies detected when processing {processor}!')
                    raise ValueError('Cyclic processor dependency detected !')
                elif get_bot().config.MESSAGE_PROCESSOR_CYCLIC_WARNING:
                    logger.warning(f'Possible cyclic processor dependencies detected when processing {processor}!')
        else:
            self._tasks[processor] = asyncio.ensure_future(_processors[processor](*args))
        return await self._tasks[processor]


@message_processor(None)
async def _on_event(bot: Ajenga, event: CQEvent, solver: MessageProcessorSolver):
    return bot, event
