from enum import Enum


class GroupPermission(Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    NONE = ""


class Group:
    id_: int
    name: str
    permission: GroupPermission

    def __init__(self, *, id_: int, name: str, permission: GroupPermission = GroupPermission.MEMBER):
        self.id_ = id_
        self.name = name
        self.permission = permission

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return repr(self)


class GroupMember:
    id_: int
    name: str
    permission: GroupPermission

    def __init__(self, *, id_: int, name: str, permission: GroupPermission = GroupPermission.MEMBER):
        self.id_ = id_
        self.name = name
        self.permission = permission

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return repr(self)


class GroupConfig:
    pass


class Friend:
    id_: int
    name: str
    remark: str

    def __init__(self, *, id_: int, name: str, remark: str = ''):
        self.id_ = id_
        self.name = name
        self.remark = remark or name

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return repr(self)
