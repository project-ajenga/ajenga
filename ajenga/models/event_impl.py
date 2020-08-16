from enum import Enum

from ajenga.models.event import Event, EventType, EventProvider
from ajenga.models.message import MessageChain, MessageType


class GroupPermission(Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    NONE = ""


class Sender:
    qq: int
    name: str
    permission: GroupPermission

    def __init__(self, *, qq: int, name: str, permission: GroupPermission = GroupPermission.NONE):
        self.qq = qq
        self.name = name
        self.permission = permission

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return repr(self)


class MessageEvent(Event):
    message: MessageChain
    message_id: int
    sender: Sender


class GroupMessageEvent(MessageEvent):
    type: EventType = EventType.GroupMessage
    group: int


class FriendMessageEvent(MessageEvent):
    type: EventType = EventType.FriendMessage


class TempMessageEvent(MessageEvent):
    type: EventType = EventType.TempMessage
    group: int


class DiscussMessageEvent(MessageEvent):
    type: EventType = EventType.DiscussMessage
    discuss: int


class GroupRecallEvent(Event):
    type: EventType = EventType.GroupRecall
    qq: int
    message_id: int
    operator: int
    group: int


class GroupMuteEvent(Event):
    type: EventType = EventType.GroupMute
    qq: int
    operator: int
    duration: int


class GroupUnmuteEvent(Event):
    type: EventType = EventType.GroupUnmute
    qq: int
    operator: int
