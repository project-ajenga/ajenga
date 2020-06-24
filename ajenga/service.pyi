import os
import re
from typing import Iterable, Optional, Callable, Union, NamedTuple, Set, Dict, Any, List
from aiocqhttp import Event

try:
    import ujson as json
except ImportError:
    import json

import ajenga
from . import Ajenga
from .helpers import normalize_str, join_str
from .meta_event import *
from .bus import EventBus
from .exceptions import *
import logging


class Privilege:
    """The privilege of user described in an `int` number.

    `0` is for Default or NotSet. The other numbers may change in future versions.
    """
    EVERYBODY = -1000
    BLACK = -999
    DEFAULT = 0
    PRIVATE = 20
    GROUP = 20
    PRIVATE_OTHER = 30
    PRIVATE_DISCUSS = 40
    PRIVATE_GROUP = 50
    PRIVATE_FRIEND = 60
    ADMIN = 100
    OWNER = 150
    WHITE = 200
    SUPERUSER = 999
    NOBODY = 1000


def _load_service_config(service_name) -> Dict: ...


def _save_service_config(service): ...


def _deco_maker(type_: str) -> Callable: ...


class Service:
    """Service is the basic model for managing functions

    支持的触发条件:
    `on_message`, `on_keyword`, `on_rex`, `on_command`, `on_natural_language`

    提供接口：
    `scheduled_job`, `broadcast`

    服务的配置文件格式为：
    {
        "name": "ServiceName",
        "use_priv": Privilege.NORMAL,
        "manage_priv": Privilege.ADMIN,
        "enable_on_default": true/false,
        "visible": true/false,
        "enable_group": [],
        "disable_group": []
        "user_privs": [[,]]]
    }

    储存位置：
    `~/.ajenga/service_config/{ServiceName}.json`
    """

    logger: logging.Logger

    def __init__(self, name, use_priv=None, manage_priv=None, enable_on_default=None, visible=None):
        """
        定义一个服务
        配置的优先级别：配置文件 > 程序指定 > 缺省值
        """

        # Initialize config
        config = _load_service_config(name)
        self.name = name
        self.use_priv = config.get('use_priv') or use_priv or Privilege.DEFAULT
        self.manage_priv = config.get('manage_priv') or manage_priv or Privilege.ADMIN
        self.enable_on_default = config.get('enable_on_default')
        if self.enable_on_default is None:
            self.enable_on_default = enable_on_default
        if self.enable_on_default is None:
            self.enable_on_default = True
        self.visible = config.get('visible')
        if self.visible is None:
            self.visible = visible
        if self.visible is None:
            self.visible = True
        self.enable_group = set(config.get('enable_group', []))
        self.disable_group = set(config.get('disable_group', []))
        self.user_privs = dict(config.get('user_privs', []))

        # Initialize trigger utils
        self._bus = EventBus()
        self.registered_processors: Set[Optional[str]] = set()

        # Initialize logger
        self.logger: logging.Logger

        # Initialize scheduler
        self.scheduler: ajenga.Scheduler



    def __str__(self):
        ...

    @property
    def key(self):
        ...

    @property
    def bot(self) -> Ajenga:
        ...

    @property
    def plugin(self) -> "Plugin":
        ...

    async def handle_event(self, event: str, *args, **kwargs) -> bool:
        ...

    async def handle_event_short(self, event: str, *args, **kwargs) -> bool:
        ...

    @staticmethod
    def get_self_ids():
        ...

    @staticmethod
    def set_block_group(group_id: int, time):
        ...

    @staticmethod
    def set_block_user(user_id: int, time):
        ...

    @staticmethod
    def check_block_group(group_id: int):
        ...

    @staticmethod
    def check_block_user(user_id: int):
        ...

    def set_enable(self, group_id: int):
        ...

    def set_disable(self, group_id: int):
        ...

    def check_enabled(self, group_id: int):
        ...

    @staticmethod
    def get_priv_from_event(ctx: Event):
        ...

    async def get_user_priv_in_group(self, uid: int, ctx: Event):
        ...

    def get_user_priv(self, uid_or_ctx: Union[int, Event]) -> int:
        ...

    def set_user_priv(self, uid_or_ctx: Union[int, Event], priv: int):
        ...

    def check_priv(self, ctx: Event, required_priv: Optional[Union[int, Callable[[int], bool]]] = None):
        ...

    async def get_enable_groups(self) -> dict:
        """
        获取所有启用本服务的群
        { group_id: [self_id1, self_id2] }
        """
        ...

    def message_preprocessor(self, name: str) -> Callable:
        ...

    def message_processor(self, name: str) -> Callable:
        ...

    def on_loaded(self) -> Callable:
        ...

    def on_unload(self) -> Callable:
        ...

    def make_wrapper(self, func: Callable, *,
                     event: str = '',
                     trigger_name: Optional[str] = None,
                     priv: Optional[Union[int, Callable[[int], bool]]] = None,
                     filter: Optional[Union[Callable, Iterable[Callable]]] = None,
                     _inner=False) -> Callable:
        ...

    def on(self, event: str, *,
           processor: Optional[str] = None,
           priv: Optional[Union[int, Callable[[int], bool]]] = None,
           filter: Optional[Union[Callable, Iterable[Callable]]] = None,
           _inner=False) -> Callable:
        ...

    def on_message(self, event='group', *, processor: Optional[str] = None, priv: Optional[Union[int, Callable[[int], bool]]] = None, filter: Optional[Union[Callable, Iterable[Callable]]] = None, **kwargs) -> Callable:
        ...

    def on_notice(self, event='group', **kwargs) -> Callable:
        ...

    def on_request(self, event='group', **kwargs) -> Callable:
        ...

    def on_processor(self, event='', *, processor: Optional[str] = None, priv: Optional[Union[int, Callable[[int], bool]]] = None, filter: Optional[Union[Callable, Iterable[Callable]]] = None, **kwargs) -> Callable:
        ...

    def on_keyword(self, keywords: Iterable, *, normalize=True, event='group', priv: Optional[Union[int, Callable[[int], bool]]] = None, filter: Optional[Union[Callable, Iterable[Callable]]] = None, **kwargs) -> Callable:
        ...

    def on_rex(self, rex, *, normalize=True, event='group', priv: Optional[Union[int, Callable[[int], bool]]] = None, filter: Optional[Union[Callable, Iterable[Callable]]] = None, **kwargs) -> Callable:
        ...

    def on_split(self, name, *, aliases: Iterable[str] = (), event: str = 'group', priv: Optional[Union[int, Callable[[int], bool]]] = None, filter: Optional[Union[Callable, Iterable[Callable]]] = None, **kwargs) -> Callable:
        ...

    def on_prefix(self, prefix, *, aliases: Iterable[str] = (), event: str = 'group', priv: Optional[Union[int, Callable[[int], bool]]] = None, filter: Optional[Union[Callable, Iterable[Callable]]] = None, **kwargs) -> Callable:
        ...

    def scheduled_job(self, *args, **kwargs) -> Callable:
        ...

    async def broadcast(self, msgs, tag='', interval_time=0.5, randomiser=None):
        ...


def set_current_plugin(plugin: "Plugin") -> None:
    ...


def get_service(key: str) -> Optional[Service]:
    """Get service object by name

    Args:
        key (str): Service key

    Returns:
        Optional[Service]: Service object
    """
    ...


def remove_service(key: Union[str, Service]) -> bool:
    """Remove a service by service object or name

    ** Warning: This function not remove service actually! **

    Args:
        key (str): Service object or key

    Returns:
        bool: Success or not
    """
    ...


def get_loaded_services() -> Set[Service]:
    ...


async def send_to_services(event, *args, **kwargs):
    ...


__all__ = ('Service', 'Privilege', 'get_loaded_services', 'get_service')
