from dataclasses import dataclass
from dataclasses import field

from ajenga.event.event import Event
from ajenga.event.event import EventType
from ajenga.message import MessageChain
from ajenga.message import MessageIdType
from ajenga.models import ContactIdType
from ajenga.models import GroupPermission


@dataclass
class Sender:
    qq: ContactIdType
    name: str
    permission: GroupPermission = field(default=GroupPermission.NONE)


@dataclass
class MessageEvent(Event):
    message: MessageChain
    message_id: MessageIdType
    sender: Sender


@dataclass
class GroupMessageEvent(MessageEvent):
    type: EventType = field(default=EventType.GroupMessage, init=False)
    group: ContactIdType


@dataclass
class FriendMessageEvent(MessageEvent):
    type: EventType = field(default=EventType.FriendMessage, init=False)


@dataclass
class TempMessageEvent(MessageEvent):
    type: EventType = field(default=EventType.TempMessage, init=False)
    group: ContactIdType


@dataclass
class GroupRecallEvent(Event):
    type: EventType = field(default=EventType.GroupRecall, init=False)
    qq: ContactIdType
    message_id: MessageIdType
    operator: ContactIdType
    group: ContactIdType


@dataclass
class GroupMuteEvent(Event):
    type: EventType = field(default=EventType.GroupMute, init=False)
    qq: ContactIdType
    operator: ContactIdType
    duration: int


@dataclass
class GroupUnmuteEvent(Event):
    type: EventType = field(default=EventType.GroupUnmute, init=False)
    qq: ContactIdType
    operator: ContactIdType
