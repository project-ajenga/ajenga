import zhconv
import unicodedata
import hashlib
import random
import asyncio
from typing import Iterable, Sequence, Callable, Any, Union, Awaitable

from aiocqhttp import Event as CQEvent
from aiocqhttp.message import escape
from aiocqhttp.exceptions import ActionFailed

from . import Ajenga, get_bot
from .exceptions import CQHttpError
from .typing import Message_T, Expression_T
from .log import logger


async def run_async(func: Callable[[Any], Union[Any, Awaitable[Any]]], *args, **kwargs):
    return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)


def context_id(event: CQEvent, *, mode: str = 'default',
               use_hash: bool = False) -> str:
    """
    Calculate a unique id representing the context of the given event.

    mode:
      default: one id for one context
      group: one id for one group or discuss
      user: one id for one user

    :param event: the event object
    :param mode: unique id mode: "default", "group", or "user"
    :param use_hash: use md5 to hash the id or not
    """
    ctx_id = ''
    if mode == 'default':
        if event.group_id:
            ctx_id = f'/group/{event.group_id}'
        elif event.discuss_id:
            ctx_id = f'/discuss/{event.discuss_id}'
        if event.user_id:
            ctx_id += f'/user/{event.user_id}'
    elif mode == 'group':
        if event.group_id:
            ctx_id = f'/group/{event.group_id}'
        elif event.discuss_id:
            ctx_id = f'/discuss/{event.discuss_id}'
        elif event.user_id:
            ctx_id = f'/user/{event.user_id}'
    elif mode == 'user':
        if event.user_id:
            ctx_id = f'/user/{event.user_id}'

    if ctx_id and use_hash:
        ctx_id = hashlib.md5(ctx_id.encode('ascii')).hexdigest()
    return ctx_id


async def send(bot: Ajenga,
               event: CQEvent,
               message: Message_T,
               *,
               ensure_private: bool = False,
               ignore_failure: bool = True,
               **kwargs) -> Any:
    """Send a message ignoring failure by default."""
    try:
        if ensure_private:
            event = event.copy()
            event['message_type'] = 'private'
        return await bot.send(event, message, **kwargs)
    except CQHttpError:
        if not ignore_failure:
            raise
        return None


async def delete_msg(bot, ctx):
    try:
        if bot.config.IS_CQPRO:
            msg_id = ctx['message_id']
            await get_bot().delete_msg(self_id=ctx['self_id'], message_id=msg_id)
    except ActionFailed as e:
        logger.error(f'Delete message failed, ret_code={e.retcode}')
    except Exception as e:
        logger.exception(e)


async def silence(bot, ctx, ban_time, ignore_super_user=False):
    try:
        self_id = ctx['self_id']
        group_id = ctx['group_id']
        user_id = ctx['user_id']
        if ignore_super_user or user_id not in bot.config.SUPERUSERS:
            await bot.set_group_ban(self_id=self_id, group_id=group_id, user_id=user_id, duration=ban_time)
    except ActionFailed as e:
        logger.error(f'Silence user failed, ret_code={e.retcode}')
    except Exception as e:
        logger.exception(e)


def render_expression(expr: Expression_T,
                      *args,
                      escape_args: bool = True,
                      **kwargs) -> str:
    """
    Render an expression to message string.

    :param expr: expression to render
    :param escape_args: should escape arguments or not
    :param args: positional arguments used in str.format()
    :param kwargs: keyword arguments used in str.format()
    :return: the rendered message
    """
    if isinstance(expr, Callable):
        expr = expr(*args, **kwargs)
    elif isinstance(expr, Sequence) and not isinstance(expr, str):
        expr = random.choice(expr)
    if escape_args:
        return expr.format(
            *[escape(s) if isinstance(s, str) else s for s in args], **{
                k: escape(v) if isinstance(v, str) else v
                for k, v in kwargs.items()
            })
    return expr.format(*args, **kwargs)


def normalize_str(string) -> str:
    """
    规范化unicode字符串 并 转为小写 并 转为简体
    """
    string = unicodedata.normalize('NFKC', string)
    string = string.lower()
    string = zhconv.convert(string, 'zh-hans')
    return string


def join_str(strlist: Iterable[str], seperator='.') -> str:
    ret = ''
    for s in strlist:
        if s:
            ret += seperator + s
    return ret[len(seperator):]
