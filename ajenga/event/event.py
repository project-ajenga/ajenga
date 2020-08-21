from abc import ABC
from enum import Enum


class EventType(Enum):
    # Meta
    Internal = "Internal"
    Protocol = "Protocol"
    Meta = "Meta"

    # Bot

    # Message
    GroupMessage = "GroupMessage"
    FriendMessage = "FriendMessage"
    TempMessage = "TempMessage"
    DiscussMessage = "DiscussMessage"

    # Event
    GroupRecall = "GroupRecall"

    ImageUpload = "ImageUpload"

    BotLeaveGroup = "BotLeaveGroup"
    BotJoinGroup = "BotJoinGroup"
    BotGroupPermissionChange = "BotGroupPermissionChange"

    GroupMute = "GroupMute"
    GroupUnmute = "GroupUnmute"

    MemberLeaveGroup = "MemberLeaveGroup"
    MemberJoinGroup = "MemberJoinGroup"
    MemberJoinGroupRequest = "MemberJoinGroupRequest"

    BotInvitedJoinGroupRequest = "BotInvitedJoinGroupRequest"

    Unknown = "Unknown"


MessageEventTypes = [
    EventType.FriendMessage,
    EventType.GroupMessage,
    EventType.TempMessage,
    EventType.DiscussMessage,
]


class Event(dict, ABC):
    type: EventType

    def __getattr__(self, item):
        return self.get(item)


class EventProvider(ABC):
    pass
