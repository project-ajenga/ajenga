from abc import ABC
from typing import Optional, Awaitable, Union

from ajenga.models.message import Message_T, Image


class Api(ABC):

    def send_friend_message(self, qq: int, message: Message_T):
        pass

    def send_temp_message(self, qq: int, group: int, message: Message_T):
        pass

    def send_group_message(self, group: int, message: Message_T):
        pass

    # def upload_image(self, type_, img: bytes) -> Union[Awaitable[Image], Image]:
    #     pass

    def get_friend_list(self):
        pass

    def get_group_list(self):
        pass

    def get_group_member_list(self, group: int):
        pass

    # def set_group_mute_all(self, group: int):
    #     pass

    # def set_group_unmute_all(self, group: int):
    #     pass

    def set_group_mute(self, group: int, qq: Optional[int]):
        pass

    def set_group_unmute(self, group: int, qq: Optional[int]):
        pass

    def set_group_kick(self, group: int, qq: int):
        pass

    def set_group_leave(self, group: int):
        pass

    def get_group_config(self, group: int):
        pass

    def set_group_config(self, group: int, config: dict):
        pass

    def get_group_member_info(self, group: int, qq: int):
        pass

    def set_group_member_info(self, group: int, qq: int, info: dict):
        pass

