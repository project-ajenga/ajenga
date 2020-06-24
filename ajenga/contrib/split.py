import shlex
from typing import List, Callable, Tuple, Union, Iterable, Optional
from functools import wraps
from aiocqhttp import Event as CQEvent

from ajenga import Ajenga, message_processor, MessageProcessorSolver, Service
from ajenga.exceptions import FailedException
from ajenga.log import logger
from ajenga.helpers import join_str, run_async


@message_processor('split')
async def _on_split(bot: Ajenga, event: CQEvent, solver: MessageProcessorSolver):
    cmd_string = event.message.extract_plain_text().strip()
    logger.debug(f'Parsing split: {repr(cmd_string)}')

    if not cmd_string:
        # command is empty
        raise FailedException('Empty command')

    try:
        split_parts = shlex.split(cmd_string)
    except Exception as e:
        raise FailedException(str(e))

    return bot, event, *split_parts


def on_split(service: Service, name, *, aliases: Iterable[str] = (), event: str = 'group', **kwargs) -> Callable:
    def deco(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(bot, ctx, cmd_name, *args):
            ret = False
            if not name or cmd_name == name or cmd_name in aliases:
                try:
                    ret = await run_async(func, bot, ctx, cmd_name, *args)
                    service.logger.info(
                        f'Message {ctx["message_id"]} is handled {ret} by {func.__name__}'
                        f', triggered by {join_str(("split", event))}.')
                except Exception as e:
                    service.logger.exception(e)
                    service.logger.error(
                        f'{type(e)} occurred when {func.__name__} handling message {ctx["message_id"]}.')
            return ret or False

        service.on_message(event, processor='split', _inner=True, **kwargs)(wrapper)
        return func

    return deco


setattr(Service, 'on_split', on_split)
