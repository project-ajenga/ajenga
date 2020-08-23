from dataclasses import dataclass
from enum import Enum

ContactIdType = int


class GroupPermission(Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    NONE = ""


@dataclass
class Group:
    id: ContactIdType
    name: str
    permission: GroupPermission


@dataclass
class GroupMember:
    id: ContactIdType
    name: str
    permission: GroupPermission


@dataclass
class GroupConfig:
    pass


@dataclass
class Friend:
    id: ContactIdType
    name: str
    remark: str
