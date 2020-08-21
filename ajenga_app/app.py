import asyncio
from typing import Dict
from typing import Optional

from ajenga.event import Event
from ajenga.event import EventProvider
from ajenga.event import FriendMessageEvent
from ajenga.event import GroupMessageEvent
from ajenga.event import MessageEvent
from ajenga.event import MetaEvent
from ajenga.event import TempMessageEvent
from ajenga.log import logger
from ajenga.message import At
from ajenga.message import MessageChain
from ajenga.message import MessageElement
from ajenga.message import Message_T
from ajenga.protocol import Api
from ajenga_router.engine import Engine


class MetaProvider(EventProvider):

    async def send(self, event: MetaEvent):
        await handle_event(self, event)


meta_provider = MetaProvider()


class BotSession(EventProvider):

    @property
    def qq(self) -> int:
        raise NotImplementedError

    async def handle_event(self, event: Event):
        return await handle_event(self, event)

    def handle_event_nowait(self, event: Event) -> asyncio.Task:
        return asyncio.create_task(handle_event(self, event))

    def __str__(self):
        return f'<{type(self).__name__}: {id(self)}>'

    def __repr__(self):
        return f'<{type(self).__name__}: {id(self)}>'

    @property
    def api(self) -> Api:
        raise NotImplementedError

    async def send(self, event: MessageEvent, message: Message_T, at_sender: bool = False):
        if at_sender and isinstance(event, GroupMessageEvent):
            message = MessageChain(message)
            message.insert(0, At(event.sender.qq))

        return await self._send(event, message)

    async def _send(self, event: MessageEvent, message: Message_T):
        if isinstance(event, GroupMessageEvent):
            return await self.api.send_group_message(group=event.group, message=message)
        elif isinstance(event, FriendMessageEvent):
            return await self.api.send_friend_message(qq=event.sender.qq, message=message)
        elif isinstance(event, TempMessageEvent):
            return await self.api.send_temp_message(qq=event.sender.qq, group=event.group, message=message)

    def wrap_message(self, message: MessageElement) -> MessageElement:
        raise NotImplementedError


_engine = Engine()
_sessions: Dict[int, BotSession] = {}
_sessions_inverse: Dict[int, int] = {}

on = _engine.on


# For collect result easily
async def handle_event(source: EventProvider, event: Event, **kwargs):
    """Handle a event received from protocol

    To avoid blocking awaiting, creating a task to run this

    :param source:
    :param event:
    :return:
    """
    if not isinstance(event, Event):
        logger.error(f'A non-event {event} passed to handle_event!')
        return

    logger.debug(f'Handling {event.type} {event}')

    if isinstance(source, BotSession):
        kwargs['bot'] = source

    res = []

    async for result in _engine.forward(event=event, source=source, **kwargs):
        if isinstance(result, Exception):
            try:
                raise result
            except Exception as e:
                logger.error(f'Error handling event {event} {e}')
                logger.exception(e)
        res.append(result)

    return res


def register_session(session: BotSession, qq: int = None):
    qq = qq or session.qq
    if qq in _sessions:
        logger.warning(f'A session already registered to {qq} !')
    _sessions[qq] = session
    _sessions_inverse[id(session)] = qq


def unregister_session(qq: int) -> bool:
    if qq in _sessions:
        try:
            del _sessions_inverse[id(_sessions[qq])]
            del _sessions[qq]
            return True
        except Exception as e:
            logger.critical(e, exc_info=True)
            return False
    else:
        return False


def get_session(qq: int) -> Optional[BotSession]:
    return _sessions.get(qq)


def get_sessions() -> Dict[int, BotSession]:
    return _sessions.copy()
