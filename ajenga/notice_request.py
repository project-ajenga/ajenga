from functools import update_wrapper
from typing import List, Optional, Callable, Union

from aiocqhttp import Event as CQEvent

from . import Ajenga, Service, get_loaded_services
from .log import logger
from .exceptions import CQHttpError
from .session import BaseSession


class NoticeSession(BaseSession):
    __slots__ = ()

    def __init__(self, bot: Ajenga, event: CQEvent):
        super().__init__(bot, event)


class RequestSession(BaseSession):
    __slots__ = ()

    def __init__(self, bot: Ajenga, event: CQEvent):
        super().__init__(bot, event)

    async def approve(self, remark: str = '') -> None:
        """
        Approve the request.

        :param remark: remark of friend (only works in friend request)
        """
        if self.closed:
            return
        self.closed = True
        try:
            await self.bot.call_action(action='.handle_quick_operation_async',
                                       self_id=self.event.self_id,
                                       context=self.event,
                                       operation={
                                           'approve': True,
                                           'remark': remark
                                       })
        except CQHttpError:
            pass

    async def reject(self, reason: str = '') -> None:
        """
        Reject the request.

        :param reason: reason to reject (only works in group request)
        """
        if self.closed:
            return
        self.closed = True
        try:
            await self.bot.call_action(action='.handle_quick_operation_async',
                                       self_id=self.event.self_id,
                                       context=self.event,
                                       operation={
                                           'approve': False,
                                           'reason': reason
                                       })
        except CQHttpError:
            pass


async def handle_notice_or_request(bot: Ajenga, event: CQEvent) -> None:
    if event.type == 'notice':
        _log_notice(event)
        session = NoticeSession(bot, event)
    else:  # must be 'request'
        _log_request(event)
        session = RequestSession(bot, event)

    ev_name = event.name
    logger.debug(f'Emitting event: {ev_name}')
    try:
        services = get_loaded_services()
        for service in services:
            if service.check_priv(event):
                if await service.handle_event(ev_name, bot, session):
                    break

    except Exception as e:
        logger.error(f'An exception occurred while handling event {ev_name}:')
        logger.exception(e)


def _log_notice(event: CQEvent) -> None:
    logger.info(f'Notice: {event}')


def _log_request(event: CQEvent) -> None:
    logger.info(f'Request: {event}')
