import os
import re
import sys
import pytz
import random
import logging
import asyncio
import warnings
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from typing import Iterable, Optional, Callable, Union, NamedTuple, Set, Dict, Any, List
from aiocqhttp import Event

try:
    import ujson as json
except ImportError:
    import json

import ajenga
from . import Ajenga
from .helpers import normalize_str, join_str, run_async
from .meta_event import *
from .bus import EventBus
from .exceptions import *
from .log import get_logger, logger


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
    SUPERUSER = 990
    BACKEND = 995
    NOBODY = 1000


# service management
_tmp_current_plugin: "Plugin" = None
_loaded_services: Dict[str, "Service"] = {}  # {key: service}
_re_illegal_char = re.compile(r'[\\/:*?"<>|\.]')
_service_config_dir = os.path.expanduser('./service_config/')
os.makedirs(_service_config_dir, exist_ok=True)

# block list
_black_list_group = {}  # Dict[group_id, expr_time]
_black_list_user = {}  # Dict[user_id, expr_time]


def _load_service_config(service_key):
    config_file = os.path.join(_service_config_dir, f'{service_key}.json')
    if not os.path.exists(config_file):
        return {}  # config file not found, return default config.
    try:
        with open(config_file, encoding='utf8') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.exception(e)
        return {}


def _save_service_config(service):
    config_file = os.path.join(_service_config_dir, f'{service.key}.json')
    with open(config_file, 'w', encoding='utf8') as f:
        json.dump({
            "name": service.name,
            "use_priv": service.use_priv,
            "manage_priv": service.manage_priv,
            "enable_on_default": service.enable_on_default,
            "visible": service.visible,
            "enable_group": list(service.enable_group),
            "disable_group": list(service.disable_group),
            'user_privs': list(service.user_privs.items())
        }, f, ensure_ascii=False, indent=2)


def _deco_maker(type_: str) -> Callable:
    def deco_deco(self, arg: Optional[Union[str, Callable]] = None,
                  *args, **kwargs) -> Callable:
        def deco(func: Callable) -> Callable:
            if isinstance(arg, str):
                return self.on(join_str((type_, arg)), *args, **kwargs)(func)
            else:
                return self.on(type_, *args, **kwargs)(func)

        if isinstance(arg, Callable):
            return deco(arg)
        return deco

    return deco_deco


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

    def __init__(self, name, use_priv=None, manage_priv=None, enable_on_default=None, visible=None):
        """
        定义一个服务
        配置的优先级别：配置文件 > 程序指定 > 缺省值
        """
        assert not _re_illegal_char.search(name), 'Service name cannot contain character in [\\/:*?"<>|.]'

        self.name = name

        # Initialize plugin for service
        self._plugin = _tmp_current_plugin

        # Initialize config
        config = _load_service_config(self.key)
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
        self.logger = get_logger(self.key, self.plugin.name)
        self.logger.setLevel(logging.DEBUG if self.bot.config.DEBUG else logging.INFO)

        # Initialize scheduler
        self.scheduler = ajenga.Scheduler() if ajenga.Scheduler else None

        @self.on_loaded()
        async def _start_scheduler():
            if self.scheduler and not self.scheduler.running and self.scheduler.get_jobs():
                self.scheduler.configure(ajenga.get_bot().config.APSCHEDULER_CONFIG)
                self.scheduler.start()
                self.logger.debug('Scheduler started')

        @self.on_unload()
        async def _stop_scheduler():
            if self.scheduler and self.scheduler.running:
                self.scheduler.remove_all_jobs()
                self.logger.debug('Scheduler stopped')

        # Add to service list
        if self.key in _loaded_services:
            warnings.warn(f"Service {self} already exists")
        _loaded_services[self.key] = self
        self.plugin.add_service(self)

    def __str__(self):
        return self.key

    @property
    def key(self):
        if self.plugin is None:
            self.logger.error('Access key when service initializing!')
        else:
            return join_str((self.plugin.name, self.name))

    @property
    def bot(self) -> Ajenga:
        return ajenga.get_bot()

    @property
    def plugin(self) -> "Plugin":
        return self._plugin

    async def handle_event(self, event: str, *args, **kwargs) -> bool:
        return any(await self._bus.emit(event, *args, **kwargs))

    async def handle_event_short(self, event: str, *args, **kwargs) -> bool:
        return await self._bus.emit_short(event, *args, **kwargs)

    @staticmethod
    def get_self_ids():
        return ajenga.get_bot()._wsr_api_clients.keys()

    @staticmethod
    def set_block_group(group_id: int, time):
        _black_list_group[group_id] = datetime.now() + time

    @staticmethod
    def set_block_user(user_id: int, time):
        if user_id not in ajenga.get_bot().config.SUPERUSERS:
            _black_list_user[user_id] = datetime.now() + time

    @staticmethod
    def check_block_group(group_id: int):
        if group_id in _black_list_group and datetime.now() > _black_list_group[group_id]:
            del _black_list_group[group_id]  # 拉黑时间过期
            return False
        return bool(group_id in _black_list_group)

    @staticmethod
    def check_block_user(user_id: int):
        if user_id in _black_list_user and datetime.now() > _black_list_user[user_id]:
            del _black_list_user[user_id]  # 拉黑时间过期
            return False
        return bool(user_id in _black_list_user)

    def set_enable(self, group_id: int):
        self.enable_group.add(group_id)
        self.disable_group.discard(group_id)
        _save_service_config(self)
        self.logger.info(f'Service {self.name} is enabled at group {group_id}')

    def set_disable(self, group_id: int):
        self.enable_group.discard(group_id)
        self.disable_group.add(group_id)
        _save_service_config(self)
        self.logger.info(f'Service {self.name} is disabled at group {group_id}')

    def check_enabled(self, group_id: int):
        return bool((group_id in self.enable_group) or (self.enable_on_default and group_id not in self.disable_group))

    @staticmethod
    def get_priv_from_event(ctx: Event):
        bot = ajenga.get_bot()
        if ctx.type == 'message':
            uid = ctx.user_id
            if uid in bot.config.SUPERUSERS:
                return Privilege.SUPERUSER
            if Service.check_block_user(uid):
                return Privilege.BLACK
            # TODO: White list
            if ctx.detail_type == 'group':
                if not ctx.anonymous:
                    role = ctx.sender.get('role')
                    if role == 'member':
                        return Privilege.GROUP
                    elif role == 'admin':
                        return Privilege.ADMIN
                    elif role == 'owner':
                        return Privilege.OWNER
                return Privilege.GROUP
            if ctx.detail_type == 'private':
                if ctx.sub_type == 'friend':
                    return Privilege.PRIVATE_FRIEND
                if ctx.sub_type == 'group':
                    return Privilege.PRIVATE_GROUP
                if ctx.sub_type == 'discuss':
                    return Privilege.PRIVATE_DISCUSS
                if ctx.sub_type == 'other':
                    return Privilege.PRIVATE_OTHER
                return Privilege.PRIVATE
        return Privilege.DEFAULT

    async def get_user_priv_in_group(self, uid: int, ctx: Event):
        priv = self.get_user_priv(uid)
        if priv == Privilege.BLACK:
            return priv
        member_info = await self.bot.get_group_member_info(
            self_id=ctx.self_id,
            group_id=ctx.group_id,
            user_id=uid)
        if member_info:
            if member_info['role'] == 'owner':
                return max(priv, Privilege.OWNER)
            elif member_info['role'] == 'admin':
                return max(priv, Privilege.ADMIN)
            else:
                return max(priv, Privilege.GROUP)

    def get_user_priv(self, uid_or_ctx: Union[int, Event]) -> int:
        if isinstance(uid_or_ctx, int):
            return self.user_privs.get(uid_or_ctx, Privilege.DEFAULT)
        elif isinstance(uid_or_ctx, Event):
            uid = uid_or_ctx.user_id
            ev_priv = self.get_priv_from_event(uid_or_ctx)
            sv_priv = self.user_privs.get(uid, Privilege.DEFAULT)
            if ev_priv == Privilege.BLACK or sv_priv == Privilege.BLACK:
                return Privilege.BLACK
            else:
                return max(ev_priv, sv_priv)
        else:
            self.logger.error(f'Unknown uid_or_ctx {uid_or_ctx}')
            return Privilege.DEFAULT

    def set_user_priv(self, uid_or_ctx: Union[int, Event], priv: int):
        print(self.user_privs)
        if isinstance(uid_or_ctx, int):
            self.user_privs[uid_or_ctx] = priv
        elif isinstance(uid_or_ctx, Event):
            self.user_privs[uid_or_ctx.user_id] = priv
        else:
            self.logger.error(f'Unknown uid_or_ctx {uid_or_ctx}')
        _save_service_config(self)

    def check_priv(self, ctx: Event, required_priv: Optional[Union[int, Callable[[int], bool]]] = None):
        required_priv = self.use_priv if required_priv is None else required_priv
        user_priv = self.get_user_priv(ctx)
        # include group notice or request
        if 'group_id' in ctx:
            if not self.check_enabled(ctx.group_id):
                return False
        if ctx.type == 'message':
            if isinstance(required_priv, int):
                return bool(user_priv >= required_priv)
            elif isinstance(required_priv, Callable):
                return required_priv(user_priv)
            else:
                return False
        else:
            # TODO: 处理私聊权限。暂时不允许任何私聊
            return True

    async def get_enable_groups(self) -> dict:
        """
        获取所有启用本服务的群
        { group_id: [self_id1, self_id2] }
        """
        gl = defaultdict(list)
        for sid in self.get_self_ids():
            sgl = set(g['group_id'] for g in await self.bot.get_group_list(self_id=sid))
            if self.enable_on_default:
                sgl = sgl - self.disable_group
            else:
                sgl = sgl & self.enable_group
            for g in sgl:
                gl[g].append(sid)
        return gl

    def message_preprocessor(self, name: str) -> Callable:
        def deco(func: Callable) -> Any:
            return ajenga.message_preprocessor(name)(func)

        @self.on_unload()
        async def unload():
            ajenga.unsubscribe_preprocessor(name)

        return deco

    def message_processor(self, name: str) -> Callable:
        def deco(func: Callable) -> Any:
            return ajenga.message_processor(name)(func)

        @self.on_unload()
        async def unload():
            ajenga.unsubscribe_processor(name)

        return deco

    def on_loaded(self, arg: Any = None) -> Callable:
        def deco(func: Callable) -> Callable:
            self._bus.subscribe(EVENT_SERVICE_LOADED, func)
            return func
        if isinstance(arg, Callable):
            return deco(arg)
        else:
            return deco

    def on_unload(self, arg: Any = None) -> Callable:
        def deco(func: Callable) -> Callable:
            self._bus.subscribe(EVENT_SERVICE_UNLOAD, func)
            return func
        if isinstance(arg, Callable):
            return deco(arg)
        else:
            return deco

    def make_wrapper(self, func: Callable, *,
                     event: str = '',
                     trigger_name: Optional[str] = None,
                     priv: Optional[Union[int, Callable[[int], bool]]] = None,
                     filter: Optional[Union[Callable, Iterable[Callable]]] = None,
                     _inner=False) -> Callable:
        @wraps(func)
        async def wrapper(bot: Ajenga, ctx: Event, *args):
            ret = False
            if ctx.name.startswith(event) and self.check_priv(ctx, priv):
                try:
                    filters = filter
                    if filters:
                        if isinstance(filters, Callable):
                            filters = (filters,)
                        try:
                            for f in filters:
                                bot, ctx, *args = await run_async(f, bot, ctx, *args)
                        except RejectedException:
                            return False

                    ret = await run_async(func, bot, ctx, *args)
                    if not _inner:
                        if ctx.type == 'message':
                            self.logger.log(logging.INFO if ret else logging.DEBUG,
                                            f'Message {ctx["message_id"]} is handled {ret} by {func.__name__}'
                                            f', triggered by {trigger_name}.')
                        else:
                            self.logger.log(logging.INFO if ret else logging.DEBUG,
                                            f'{ctx.name} is handled by {func.__name__}.')
                except FinishedException as e:
                    ret = e.success
                    if not _inner:
                        if ctx.type == 'message':
                            self.logger.log(logging.INFO if ret else logging.DEBUG,
                                            f'Message {ctx["message_id"]} is handled {ret} by {func.__name__}'
                                            f', triggered by {trigger_name}.')
                        else:
                            self.logger.log(logging.INFO if ret else logging.DEBUG,
                                            f'{ctx.name} is handled by {func.__name__}.')
                    raise
                except Exception as e:
                    self.logger.exception(e)
                    if not _inner:
                        if ctx.type == 'message':
                            self.logger.error(
                                f'{type(e)} occurred when {func.__name__} handling message {ctx["message_id"]}.')
                        else:
                            self.logger.error(f'{type(e)} occurred when {func.__name__} handling {ctx.name}.')
            return ret or False
        return wrapper

    def on(self, event: str, *,
           processor: Optional[str] = None,
           priv: Optional[Union[int, Callable[[int], bool]]] = None,
           filter: Optional[Union[Callable, Iterable[Callable]]] = None,
           _inner=False) -> Callable:
        def deco(func: Callable[[Ajenga, Dict, Any], Any]) -> Callable:
            wrapper = self.make_wrapper(func,
                                        priv=priv,
                                        trigger_name=join_str((processor, event)),
                                        filter=filter,
                                        _inner=_inner)

            self.registered_processors.add(processor)
            self._bus.subscribe(join_str((processor, event)), wrapper)
            return func

        return deco

    on_message = _deco_maker('message')

    on_notice = _deco_maker('notice')

    on_request = _deco_maker('request')

    on_processor = _deco_maker('message')

    def on_keyword(self, keywords: Iterable, *, normalize=True, event='group', **kwargs) -> Callable:
        if isinstance(keywords, str):
            keywords = (keywords,)
        if normalize:
            keywords = tuple(normalize_str(kw) for kw in keywords)

        def deco(func: Callable[[Ajenga, Dict], Any]) -> Callable:
            @wraps(func)
            async def wrapper(bot, ctx):
                ret = False
                plain_text = ctx['message'].extract_plain_text()
                if normalize:
                    plain_text = normalize_str(plain_text)
                ctx['plain_text'] = plain_text
                for kw in keywords:
                    if kw in plain_text:
                        try:
                            ret = run_async(func, self.bot, ctx)
                        except FinishedException as e:
                            ret = e.success
                            self.logger.info(
                                f'Message {ctx["message_id"]} is handled {ret} by {func.__name__}, triggered by keyword.')
                            raise
                        except Exception as e:
                            self.logger.exception(e)
                            self.logger.error(
                                f'{type(e)} occurred when {func.__name__} handling message {ctx["message_id"]}.')
                        break
                return ret

            self.on_message(event, _inner=True, **kwargs)(wrapper)
            return func

        return deco

    def on_rex(self, rex, *, normalize=True, event='group', **kwargs) -> Callable:
        if isinstance(rex, str):
            rex = re.compile(rex)

        def deco(func: Callable[[Ajenga, Dict, re.Match, Any], Any]) -> Callable:
            @wraps(func)
            async def wrapper(bot, ctx, *args):
                ret = False
                plain_text = ctx['message'].extract_plain_text().strip()
                if normalize:
                    plain_text = normalize_str(plain_text)
                ctx['plain_text'] = plain_text
                match = rex.search(plain_text)
                if match:
                    try:
                        ret = await run_async(func, bot, ctx, match, *args)
                    except FinishedException as e:
                        ret = e.success
                        self.logger.info(
                            f'Message {ctx["message_id"]} is handled {ret} by {func.__name__}, triggered by rex.')
                        raise
                    except Exception as e:
                        self.logger.exception(e)
                        self.logger.error(
                            f'{type(e)} occurred when {func.__name__} handling message {ctx["message_id"]}.')
                return ret or False

            self.on_message(event, _inner=True, **kwargs)(wrapper)
            return func

        return deco

    def scheduled_job(self, *args, **kwargs) -> Callable:
        kwargs.setdefault('timezone', pytz.timezone('Asia/Shanghai'))
        kwargs.setdefault('misfire_grace_time', 60)
        kwargs.setdefault('coalesce', True)

        def deco(func: Callable[[], Any]) -> Callable:
            @wraps(func)
            async def wrapper():
                try:
                    self.logger.info(f'Scheduled job {func.__name__} start.')
                    await run_async(func)
                    self.logger.info(f'Scheduled job {func.__name__} completed.')
                except Exception as e:
                    self.logger.exception(e)
                    self.logger.error(f'{type(e)} occurred when doing scheduled job {func.__name__}.')

            if self.scheduler:
                self.logger.info(f'Scheduler add job {func.__name__}')
                return self.scheduler.scheduled_job(*args, **kwargs)(wrapper)
            else:
                self.logger.warning(f'Scheduler is not supported in your version!')
                return func

        return deco

    async def broadcast(self, msgs, tag='', interval_time=0.5, randomiser=None):
        bot = self.bot
        if isinstance(msgs, str):
            msgs = (msgs,)
        glist = await self.get_enable_groups()
        for gid, selfids in glist.items():
            try:
                for msg in msgs:
                    await asyncio.sleep(interval_time)
                    msg = randomiser(msg) if randomiser else msg
                    await bot.send_group_msg(self_id=random.choice(selfids), group_id=gid, message=msg)
                count = len(msgs)
                if count:
                    self.logger.info(f"群{gid} 投递{tag}成功 共{count}条消息")
            except Exception as e:
                self.logger.exception(e)
                self.logger.error(f"群{gid} 投递{tag}失败 {type(e)}")


def set_current_plugin(plugin: "Plugin") -> None:
    global _tmp_current_plugin
    _tmp_current_plugin = plugin


def get_service(key: str) -> Optional[Service]:
    """Get service object by name

    Args:
        key (str): Service key

    Returns:
        Optional[Service]: Service object
    """
    return _loaded_services.get(key, None)


def remove_service(key: Union[str, Service]) -> bool:
    """Remove a service by service object or name

    ** Warning: This function not remove service actually! **

    Args:
        key (str): Service object or key

    Returns:
        bool: Success or not
    """
    service = get_service(key) if isinstance(key, str) else key
    if not service:
        warnings.warn(f"Service {key} not exists")
        return False

    del _loaded_services[service.key]
    return True


def get_loaded_services() -> Set[Service]:
    return set(_loaded_services.values())


async def send_to_services(event, *args, **kwargs):
    coros = list(service.handle_event(event, *args, **kwargs) for service in get_loaded_services())
    await asyncio.gather(*coros)


__all__ = ('Service', 'Privilege', 'get_loaded_services', 'get_service')
