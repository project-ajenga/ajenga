from abc import ABC
from dataclasses import dataclass
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

    # Event
    GroupRecall = "GroupRecall"

    # ImageUpload = "ImageUpload"

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
]


@dataclass
class Event(ABC):
    type: EventType


class EventProvider(ABC):
    pass
