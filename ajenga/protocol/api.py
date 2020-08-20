from abc import ABC
from nntplib import GroupInfo
from typing import Optional, Awaitable, Union, Generic, TypeVar, List

from typish import NoneType

from ajenga.models.contact import Friend, Group, GroupMember
from ajenga.models.message import Message_T, Image, MessageIdType

T = TypeVar('T')


class ApiError(Exception):
    pass


class ApiResult(Generic[T]):
    _code: int
    _message: str
    _data: T

    def __init__(self, code: int, message: str, data: T):
        self._code = code
        self._message = message
        self._data = data

    @property
    def code(self) -> int:
        return self._code

    @property
    def message(self) -> str:
        return self._message

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def data(self) -> T:
        return self._data


class MessageSendResult:
    message_id: int

    def __init__(self, message_id: int):
        self.message_id = message_id


class Api(ABC):

    async def send_friend_message(self, qq: int, message: Message_T) -> ApiResult[MessageSendResult]:
        raise NotImplementedError

    async def send_temp_message(self, qq: int, group: int, message: Message_T) -> ApiResult[MessageSendResult]:
        raise NotImplementedError

    async def send_group_message(self, group: int, message: Message_T) -> ApiResult[MessageSendResult]:
        raise NotImplementedError

    async def recall(self, message_id: MessageIdType) -> ApiResult[NoneType]:
        raise NotImplementedError

    async def get_friend_list(self) -> ApiResult[List[Friend]]:
        raise NotImplementedError

    async def get_group_list(self) -> ApiResult[List[Group]]:
        raise NotImplementedError

    async def get_group_member_list(self, group: int) -> ApiResult[List[GroupMember]]:
        raise NotImplementedError

    async def set_group_mute(self, group: int, qq: Optional[int]) -> ApiResult[NoneType]:
        raise NotImplementedError

    async def set_group_unmute(self, group: int, qq: Optional[int]) -> ApiResult[NoneType]:
        raise NotImplementedError

    async def set_group_kick(self, group: int, qq: int) -> ApiResult[NoneType]:
        raise NotImplementedError

    async def set_group_leave(self, group: int) -> ApiResult[NoneType]:
        raise NotImplementedError

    async def get_group_config(self, group: int) -> ApiResult[GroupInfo]:
        raise NotImplementedError

    async def set_group_config(self, group: int, config: dict) -> ApiResult[NoneType]:
        raise NotImplementedError

    async def get_group_member_info(self, group: int, qq: int) -> ApiResult[GroupMember]:
        raise NotImplementedError

    async def set_group_member_info(self, group: int, qq: int, info: dict) -> ApiResult[NoneType]:
        raise NotImplementedError
