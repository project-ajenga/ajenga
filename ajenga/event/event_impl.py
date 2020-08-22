from ajenga.event.event import Event
from ajenga.event.event import EventType
from ajenga.message import MessageChain
from ajenga.models import GroupPermission


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
