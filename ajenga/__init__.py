import ajenga.default_config

config = ajenga.default_config


def init_config(config_):
    global config
    config = config_


from . import event
from . import message
from . import models
from . import protocol
from . import router
from . import utils
