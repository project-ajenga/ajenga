import os
import re
import sys
import asyncio
import shlex
import warnings
import importlib
import json
from types import ModuleType
from typing import Any, Set, Dict, Optional, Union, List

from . import get_bot
from .log import logger
from .meta_event import *
from .service import Service, set_current_plugin,\
    get_service, remove_service, \
    send_to_services


class Plugin:
    __slots__ = ('module', 'path', 'name', 'author', 'version', 'usage', 'services')

    name: str
    author: Union[str, List[str]]
    version: str
    usage: str

    module: Optional[ModuleType]
    path: str
    services: Dict[str, Service]

    def __init__(self,
                 info):
        self.name = info['name']
        self.author = info['author']
        self.version = info['version']
        self.usage = info['usage']
        self.module = None
        self.path = ''
        self.services = dict()

    def load(self,
             module: ModuleType):
        self.module = module
        self.path = module.__name__

    def add_service(self, service):
        self.services[service.name] = service
        logger.info(f'Succeeded to load Service "{service.key}" ')

    async def unload(self):
        await unload_plugin(self)

    async def reload(self) -> Optional["Plugin"]:
        return await reload_plugin(self)

    def __str__(self):
        return self.name or self.path


_plugins: Dict[str, Plugin] = {}


def add_plugin(plugin: Plugin) -> None:
    """Register a plugin
    
    Args:
        plugin (Plugin): Plugin object
    """
    if plugin.path in _plugins:
        warnings.warn(f"Plugin {plugin} already exists")
        return

    if plugin.name:
        _plugins[plugin.name] = plugin
    _plugins[plugin.path] = plugin


def get_plugin(key: str) -> Optional[Plugin]:
    """Get plugin object by plugin module path
    
    Args:
        key (str): Plugin module path
    
    Returns:
        Optional[Plugin]: Plugin object
    """
    return _plugins.get(key, None)


def remove_plugin(key: Union[str, Plugin]) -> bool:
    """Remove a plugin by plugin module path
    
    ** Warning: This function not remove plugin actually! **

    Args:
        key (Union[str, Plugin]): Plugin object or module path or name

    Returns:
        bool: Success or not
    """
    plugin = get_plugin(key) if isinstance(key, str) else key
    if not plugin:
        warnings.warn(f"Plugin {key} not exists")
        return False

    if plugin.name in _plugins:
        del _plugins[plugin.name]
    if plugin.path in _plugins:
        del _plugins[plugin.path]
    return True


async def load_plugin(module_path: str, plugin_dir: str = None) -> Optional[Plugin]:
    """Load a module as a plugin
    
    Args:
        module_path (str): path of module to import
        plugin_dir (str): path of module package in file form
    
    Returns:
        Optional[Plugin]: Plugin object loaded
    """
    # Make sure tmp is clean
    set_current_plugin(None)

    if not plugin_dir:
        if module_path.startswith('.'):
            plugin_dir = '.' + module_path.replace('.', '/')
        else:
            plugin_dir = './' + module_path.replace('.', '/')

    try:
        plugin_info_path = os.path.join(os.path.expanduser(plugin_dir), get_bot().config.PLUGIN_INFO_FILE)
        with open(plugin_info_path, encoding='utf-8') as f:
            plugin_info = json.load(f)

        if plugin_info.get('name') and get_plugin(plugin_info['name']):
            logger.error(f'Plugin {plugin_info["name"]} already exists')
            return None
        plugin = Plugin(plugin_info)
        set_current_plugin(plugin)
    except Exception as e:
        logger.exception(e)
        logger.error(f'Failed to load plugin config from {plugin_dir}')
        return None

    try:
        module = importlib.import_module(module_path)
        plugin.load(module)
        add_plugin(plugin)
    except Exception as e:
        logger.exception(e)
        logger.error(f'Failed to load plugin module from {module_path}')
        await unload_plugin(plugin, True)
        return None

    try:
        coros = list(service.handle_event(EVENT_SERVICE_LOADED) for service in plugin.services.values())
        await asyncio.gather(*coros)
    except Exception as e:
        logger.exception(e)
        logger.critical(f'Failed to execute on_loaded from {plugin.name}')
        return plugin

    logger.info(f'Succeeded to load Plugin "{plugin.name}"')

    try:
        await send_to_services(EVENT_PLUGIN_LOADED, plugin)
    except Exception as e:
        logger.exception(e)
        logger.error(f'Error occurred when trigger plugin loaded when importing "{plugin.name}"')

    return plugin


async def unload_plugin(key: Union[str, Plugin], forced: bool = False) -> bool:
    """Unload a plugin
    
    Args:
        key (Union[str, Plugin]): Plugin object or module path or name
        forced (bool): Forced to unload

    Returns:
        bool: Unloaded successful
    """
    plugin = get_plugin(key) if isinstance(key, str) else key
    if not plugin:
        warnings.warn(f"Plugin {key} not exists")
        return False

    plugin_name = plugin.name

    await send_to_services(EVENT_PLUGIN_UNLOAD, plugin)

    for service in plugin.services.values():
        try:
            await service.handle_event(EVENT_SERVICE_UNLOAD)
            remove_service(service)
        except Exception as e:
            logger.exception(e)
            logger.error(f'Failed to unload service "{service}", error: {e}')

    result = remove_plugin(plugin)
    if not result and not forced:
        return False

    for module in list(filter(lambda x: x.startswith(plugin.path), sys.modules.keys())):
        del sys.modules[module]

    logger.info(f'Succeeded to unload Plugin "{plugin_name}"')
    return True


async def reload_plugin(key: Union[str, Plugin]) -> Optional[Plugin]:
    """Reload a plugin

    Args:
        key (Union[str, Plugin]): Plugin object or module path or name

    Returns:
        bool: Success or not
    """
    plugin = get_plugin(key) if isinstance(key, str) else key
    if not plugin:
        warnings.warn(f"Plugin {key} not exists")
        return None

    module_path = plugin.path
    return await load_plugin(module_path) if await unload_plugin(plugin) else None


async def load_plugins(plugin_dir: str, module_prefix: str) -> Set[Plugin]:
    """Find all non-hidden modules or packages in a given directory,
    and import them with the given module prefix.

    Args:
        plugin_dir (str): Plugin directory to search
        module_prefix (str): Module prefix used while importing

    Returns:
        Set[Plugin]: Set of plugin objects successfully loaded
    """

    count = set()
    for name in os.listdir(plugin_dir):
        path = os.path.join(plugin_dir, name)
        if os.path.isfile(path) and \
                (name.startswith('_') or not name.endswith('.py')):
            continue
        if os.path.isdir(path) and \
                (name.startswith('_') or not os.path.exists(
                    os.path.join(path, get_bot().config.PLUGIN_INFO_FILE))):
            continue

        m = re.match(r'([_A-Z0-9a-z]+)(.py)?', name)
        if not m:
            continue

        result = await load_plugin(f'{module_prefix}.{m.group(1)}')
        if result:
            count.add(result)
    return count


def get_loaded_plugins() -> Set[Plugin]:
    """
    Get all plugins loaded.

    :return: a set of Plugin objects
    """
    return set(_plugins.values())
