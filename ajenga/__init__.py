import asyncio
import logging
from typing import Any, Optional, Callable, Awaitable, Union, Dict, List

import aiocqhttp
from aiocqhttp import CQHttp, Event

from .log import logger
from .sched import Scheduler


class Ajenga(CQHttp):

    def __init__(self, config_object: Optional[Any] = None):
        if config_object is None:
            from . import default_config as config_object

        config_dict = {
            k: v
            for k, v in config_object.__dict__.items()
            if k.isupper() and not k.startswith('_')
        }
        logger.debug(f'Loaded configurations: {config_dict}')
        super().__init__(message_class=aiocqhttp.message.Message,
                         **{k.lower(): v for k, v in config_dict.items()})

        self.config = config_object
        self.asgi.debug = self.config.DEBUG
        self._origins = dict()

        from .message import handle_message
        from .notice_request import handle_notice_or_request

        @self.on_message
        async def _(event: aiocqhttp.Event):
            asyncio.create_task(handle_message(self, event))

        @self.on_notice
        async def _(event: aiocqhttp.Event):
            asyncio.create_task(handle_notice_or_request(self, event))

        @self.on_request
        async def _(event: aiocqhttp.Event):
            asyncio.create_task(handle_notice_or_request(self, event))

    def run(self,
            host: Optional[str] = None,
            port: Optional[int] = None,
            *args,
            **kwargs) -> None:
        host = host or self.config.HOST
        port = port or self.config.PORT
        if 'debug' not in kwargs:
            kwargs['debug'] = self.config.DEBUG

        logger.info(f'Running on {host}:{port}')
        super().run(host=host, port=port, *args, **kwargs)

    def hook_send(self, origin, func):
        self._origins[origin] = func

    async def send(self, event: Event,
                   message: Union[str, Dict[str, Any], List[Dict[str, Any]]],
                   **kwargs) -> Optional[Dict[str, Any]]:
        origin = event.get('origin')
        if origin and self._origins[origin]:
            return await self._origins[origin](event, message, **kwargs)
        else:
            return await super().send(event, message, **kwargs)


_bot: Optional[Ajenga] = None


def init(config_object: Optional[Any] = None) -> None:
    """
    Initialize Ajenga instance.

    This function must be called at the very beginning of code,
    otherwise the get_bot() function will return None and nothing
    is gonna work properly.

    :param config_object: configuration object
    """
    global _bot
    _bot = Ajenga(config_object)

    if _bot.config.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


def get_bot() -> Ajenga:
    """
    Get the Ajenga instance.

    The result is ensured to be not None, otherwise an exception will
    be raised.

    :raise ValueError: instance not initialized
    """
    if _bot is None:
        raise ValueError('Ajenga instance has not been initialized')
    return _bot


def run(host: Optional[str] = None, port: Optional[int] = None, *args,
        **kwargs) -> None:
    """Run the Ajenga instance."""
    get_bot().run(host=host, port=port, *args, **kwargs)


def on_startup(func: Callable[[], Awaitable[None]]) \
        -> Callable[[], Awaitable[None]]:
    """
    Decorator to register a function as startup callback.
    """
    return get_bot().server_app.before_serving(func)


def on_websocket_connect(func: Callable[[aiocqhttp.Event], Awaitable[None]]) \
        -> Callable[[], Awaitable[None]]:
    """
    Decorator to register a function as websocket connect callback.

    Only work with CQHTTP v4.14+.
    """
    return get_bot().on_meta_event('lifecycle.connect')(func)


from .exceptions import *
from .plugin import (Plugin, load_plugin, load_plugins, reload_plugin,
                     get_loaded_plugins, get_plugin)
from .service import Privilege, Service, get_loaded_services, get_service
from .message import Message, MessageSegment, switch_message, finish_message
from .message.preprocessor import message_preprocessor, unsubscribe_preprocessor, MessagePreprocessorSolver
from .message.processor import message_processor, unsubscribe_processor, MessageProcessorSolver
from .notice_request import NoticeSession, RequestSession
from .helpers import context_id
from .meta_event import *
from .contrib import *

__all__ = [
    'Event',
    'Ajenga',
    'init',
    'get_bot',
    'run',
    'on_startup',
    'on_websocket_connect',
    'CQHttpError',
    'Plugin',
    'load_plugin',
    'load_plugins',
    'reload_plugin',
    'get_loaded_plugins',
    'get_plugin',
    'Privilege',
    'Service',
    'get_loaded_services',
    'get_service',
    'Message',
    'MessageSegment',
    'switch_message',
    'finish_message',
    'message_preprocessor',
    'unsubscribe_preprocessor',
    'MessagePreprocessorSolver',
    'message_processor',
    'unsubscribe_processor',
    'MessageProcessorSolver',
    'NoticeSession',
    'RequestSession',
    'context_id',
]
