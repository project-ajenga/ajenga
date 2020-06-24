import os
from PIL import Image
import base64
from urllib.request import pathname2url
from urllib.parse import urljoin
from io import BytesIO
from matplotlib import pyplot as plt
from typing import Optional
from ajenga import get_bot, get_plugin, Service, Plugin
from ajenga import MessageSegment

from ajenga.log import logger


def pic2b64(pic: Image) -> str:
    buf = BytesIO()
    pic.save(buf, format='PNG')
    base64_str = base64.b64encode(buf.getvalue()).decode()  # , encoding='utf8')
    return 'base64://' + base64_str


def fig2b64(plt: plt) -> str:
    buf = BytesIO()
    plt.savefig(buf, format='PNG', dpi=100)
    base64_str = base64.b64encode(buf.getvalue()).decode()
    return 'base64://' + base64_str


def concat_pic(pics, border=5):
    num = len(pics)
    w, h = pics[0].size
    des = Image.new('RGBA', (w, num * h + (num - 1) * border), (255, 255, 255, 255))
    for i, pic in enumerate(pics):
        des.paste(pic, (0, i * (h + border)), pic)
    return des


class DirectoryType:
    MODULE = 0
    DATA = 1
    RESOURCE = 2
    TEMP = 3


def get_plugin_dir(pl, dtype) -> Optional[str]:
    if isinstance(pl, Service):
        plugin = pl.plugin
    elif isinstance(pl, Plugin):
        plugin = pl
    else:
        plugin = get_plugin(pl)
    if not plugin:
        logger.error(f'Failed to get dir: plugin {pl} not found')
        return None

    if dtype == DirectoryType.MODULE:
        return os.path.dirname(plugin.module.__file__)
    elif dtype == DirectoryType.RESOURCE:
        directory = os.path.expanduser(get_bot().config.RESOURCE_DIR)
        directory = os.path.normpath(os.path.join(directory, plugin.name))
        os.makedirs(directory, exist_ok=True)
        return directory
    elif dtype == DirectoryType.DATA:
        directory = os.path.expanduser(get_bot().config.DATA_DIR)
        directory = os.path.normpath(os.path.join(directory, plugin.name))
        os.makedirs(directory, exist_ok=True)
        return directory
    elif dtype == DirectoryType.TEMP:
        directory = os.path.expanduser(get_bot().config.TEMP_DIR)
        directory = os.path.normpath(os.path.join(directory, plugin.name))
        os.makedirs(directory, exist_ok=True)
        return directory
    else:
        logger.error(f'Failed to get {dtype} dir for plugin {plugin}')
        return None


def ensure_file_path(pl, dtype, path, *paths) -> Optional[str]:
    root_path = get_plugin_dir(pl, dtype)
    file_path = os.path.join(root_path, path, *paths)
    file_path = os.path.normpath(file_path)
    dir_path = os.path.dirname(file_path)
    if os.path.normcase(file_path).startswith(os.path.normcase(root_path)):
        os.makedirs(dir_path, exist_ok=True)
        return file_path
    else:
        logger.error(f'Could not access outside plugin files! {pl} {file_path}')
        return None


class R:

    @staticmethod
    def get(pl, path, *paths):
        return ResObj(pl, os.path.join(path, *paths))

    @staticmethod
    def img(pl, path, *paths):
        return ResImg(pl, os.path.join(path, *paths))

    @staticmethod
    def abspath(pl, path, *paths):
        return os.path.join(get_plugin_dir(pl, DirectoryType.RESOURCE), path, *paths)


class ResObj:

    def __init__(self, pl, res_path):
        self._path = os.path.normpath(res_path)
        self._pl = pl

    @property
    def path(self):
        return ensure_file_path(self._pl, DirectoryType.RESOURCE, self._path)

    @property
    def exist(self):
        return os.path.exists(self.path)


class ResImg(ResObj):

    @property
    def cqcode(self, url=False) -> MessageSegment:
        if url:
            return MessageSegment.image(f'file:///{os.path.abspath(self.path)}')
        else:
            try:
                return MessageSegment.image(pic2b64(self.open()))
            except Exception as e:
                logger.exception(e)
                return MessageSegment.text('[图片]')

    def open(self) -> Image:
        try:
            return Image.open(self.path)
        except Exception as e:
            logger.exception(e)
