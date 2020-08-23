from dataclasses import dataclass
from dataclasses import field
from enum import Enum

from ajenga.event import Event
from ajenga.event import EventType


class MetaEventType(Enum):
    ServiceLoaded = "ServiceLoaded"
    ServiceUnload = "ServiceUnload"

    PluginLoaded = "PluginLoaded"
    PluginUnload = "PluginUnload"


@dataclass(init=False)
class MetaEvent(Event):
    type: EventType = field(default=EventType.Meta, init=False)
    _dict: dict = field(default_factory=dict, init=False)

    def __init__(self, meta_type, **kwargs):
        self.type = EventType.Meta
        self._dict = {}
        self._dict.update({
            'meta_type': meta_type,
            **kwargs
        })

    def __getattr__(self, item):
        return self._dict[item]
