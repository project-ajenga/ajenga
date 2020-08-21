from abc import ABC
from typing import Optional, Awaitable, Union, Generic, TypeVar, List

from ajenga.models.contact import Friend, Group, GroupMember, GroupConfig
from ajenga.models.message import Message_T, MessageIdType

T = TypeVar('T')


class Code:
    Success = 0
    Unspecified = -1
    Unavailable = -2
    IncorrectArgument = -5
    RequestError = -10
    NetworkError = -20


class ApiResult(Generic[T]):
    _code: int
    _message: str
    _data: T

    def __init__(self, code: int, data: T = None, message: str = None):
        self._code = code
        self._message = message or ''
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

    async def recall(self, message_id: MessageIdType) -> ApiResult[None]:
        raise NotImplementedError

    async def get_friend_list(self) -> ApiResult[List[Friend]]:
        raise NotImplementedError

    async def get_group_list(self) -> ApiResult[List[Group]]:
        raise NotImplementedError

    async def get_group_member_list(self, group: int) -> ApiResult[List[GroupMember]]:
        raise NotImplementedError

    async def set_group_mute(self, group: int, qq: Optional[int]) -> ApiResult[None]:
        raise NotImplementedError

    async def set_group_unmute(self, group: int, qq: Optional[int]) -> ApiResult[None]:
        raise NotImplementedError

    async def set_group_kick(self, group: int, qq: int) -> ApiResult[None]:
        raise NotImplementedError

    async def set_group_leave(self, group: int) -> ApiResult[None]:
        raise NotImplementedError

    async def get_group_config(self, group: int) -> ApiResult[GroupConfig]:
        raise NotImplementedError

    async def set_group_config(self, group: int, config: GroupConfig) -> ApiResult[None]:
        raise NotImplementedError

    async def get_group_member_info(self, group: int, qq: int) -> ApiResult[GroupMember]:
        raise NotImplementedError

    async def set_group_member_info(self, group: int, qq: int, info: dict) -> ApiResult[None]:
        raise NotImplementedError
