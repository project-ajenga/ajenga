from abc import ABC
from enum import Enum
from typing import Optional, List, Dict, Any, Union, Type, TypeVar, Iterable

import hashlib

MessageIdType = int
ImageIdType = str
VoiceIdType = str


class MessageType(Enum):

    Meta = "Meta"
    Plain = "Plain"
    At = "At"
    AtAll = "AtAll"
    Face = "Face"
    Image = "Image"
    Quote = "Quote"

    Voice = "Voice"
    App = "App"
    Json = "Json"

    # Not fully supported yet
    # FlashImage = "FlashImage"
    # Poke = "Poke"
    # Xml = "Xml"
    Unknown = "Unknown"


class MessageElement(ABC):
    type: MessageType

    @property
    def referer(self):
        return self._referer

    @referer.setter
    def referer(self, value):
        self._referer = value

    def __init__(self):
        self._referer = None

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return repr(self)

    def raw(self) -> "MessageElement":
        """Convert bot dependent message into universal raw message

        :return:
        """
        return self

    def to(self, bot, **kwargs) -> "MessageElement":
        """Convert universal message into bot dependent message

        :return:
        """
        return bot.wrap_message(self, **kwargs)

    def content_string(self) -> str:
        return ''


M = TypeVar('M', bound=MessageElement)


class MessageChain(List[MessageElement]):
    def __init__(self, msgs: Union[str, MessageElement, Iterable[MessageElement]] = ...):
        super().__init__()
        if msgs is ...:
            pass
        elif isinstance(msgs, str):
            self.append(Plain(text=msgs, type=MessageType.Plain.value))
        elif isinstance(msgs, MessageChain):
            self.extend(msgs)
        elif isinstance(msgs, MessageElement):
            self.append(msgs)
        elif isinstance(msgs, Iterable):
            self.extend(msgs)
            # for msg in msgs:
            #     if isinstance(msg, MessageElement):
            #         self.append(msg)
            #     else:
            #         raise TypeError(f'{msg} is not a valid MessageElement !')
        else:
            raise ValueError(f'Not a valid MessageChain: {msgs}!')

    def content_string(self) -> str:
        return ''.join(x.content_string() for x in self).strip()

    def get_first(self, msg_type: Type[M] = MessageElement) -> Optional[M]:
        for msg in self:
            if isinstance(msg, msg_type):
                return msg
        else:
            return None

    def get(self, index: int, msg_type: Type[M] = MessageElement) -> Optional[M]:
        _index = 0
        for msg in self:
            if isinstance(msg, msg_type):
                if index == _index:
                    return msg
                _index += 1
        else:
            return None

    def __eq__(self, other):
        if isinstance(other, MessageChain) and len(self) == len(other):
            for a, b in zip(self, other):
                if (not isinstance(a, Meta) or not isinstance(b, Meta)) and a != b:
                    return False
            return True
        else:
            return False

    def copy(self) -> "MessageChain":
        return MessageChain(filter(lambda x: not isinstance(x, Meta), self))

    def raw(self) -> "MessageChain":
        """Convert bot dependent message into universal raw message

        :return:
        """
        return MessageChain(map(lambda x: x.raw(), self))

    def to(self, bot, **kwargs) -> "MessageChain":
        """Convert universal message into bot dependent message

        :return:
        """
        return MessageChain(map(lambda x: x.to(bot, **kwargs), self))


class Meta(MessageElement):
    type: MessageType = MessageType.Meta


class Quote(MessageElement):
    type: MessageType = MessageType.Quote
    id_: MessageIdType
    # senderId: int
    # targetId: int
    # groupId: int
    origin: MessageChain

    def __init__(self, id_: MessageIdType, origin=None, **kwargs):
        super().__init__()
        self.id_ = id_
        self.origin = origin

    def __eq__(self, other):
        return isinstance(other, Quote) and self.id_ == other.id_


class Plain(MessageElement):
    type: MessageType = MessageType.Plain
    text: str

    def __init__(self, text: str = None, **kwargs):
        super().__init__()
        self.text = text

    def content_string(self) -> str:
        return self.text

    def __eq__(self, other):
        return isinstance(other, Plain) and self.text == other.text


class At(MessageElement):
    type: MessageType = MessageType.At
    target: int
    # display: str

    def __init__(self, qq: int = None, **kwargs):
        super().__init__()
        self.target = qq

    def __eq__(self, other):
        return isinstance(other, At) and self.target == other.target


class AtAll(MessageElement):
    type: MessageType = MessageType.AtAll

    def __eq__(self, other):
        return isinstance(other, MessageElement) and self.type == other.type


class Face(MessageElement):
    type: MessageType = MessageType.Face
    id_: int

    def __init__(self, id_: int = None, **kwargs):
        super().__init__()
        self.id_ = id_

    def __eq__(self, other):
        return isinstance(other, Face) and self.id_ == other.id_


class Image(MessageElement):
    type: MessageType = MessageType.Image
    # id_: Optional[ImageIdType]
    hash_: str
    url: Optional[str]
    content: Optional[bytes]

    def __init__(self, *, url: str = None, content: bytes = None, hash_: str = None, **kwargs):
        super().__init__()
        self.url = url
        self.content = content
        self.hash_ = hash_
        if self.content and not self.hash_:
            self.hash_ = hashlib.md5(self.content).hexdigest()

    def __eq__(self, other):
        return isinstance(other, Image) and any((
            self.hash_ and self.hash_ == other.hash_,
            self.url and self.url == other.url,
            self.content and self.content == other.content
        ))

    @staticmethod
    def from_(image: Any) -> "Optional[Image]":
        try:
            import PIL.Image
            if isinstance(image, PIL.Image.Image):
                return Image(content=image.tobytes())
        except ImportError:
            return None


class Voice(MessageElement):
    type: MessageType = MessageType.Voice
    # id_: Optional[VoiceIdType]
    hash_: str
    url: Optional[str]
    content: Optional[bytes]

    def __init__(self, url: str = None, content: bytes = None, hash_: str = None, **kwargs):
        super().__init__()
        self.url = url
        self.content = content
        self.hash_ = hash_

    def __eq__(self, other):
        return isinstance(other, Voice) and any((
            self.hash_ and self.hash_ == other.hash_,
            self.url and self.url == other.url,
            self.content and self.content == other.content
        ))


class App(MessageElement):
    type: MessageType = MessageType.App
    content: dict

    def __init__(self, content: dict = None, **kwargs):
        super().__init__()
        self.content = content


class Unknown(MessageElement):
    type: MessageType = MessageType.Unknown


MessageElement_T = Union[MessageElement, str, Dict[str, Any]]
Message_T = Union[MessageElement_T, List[MessageElement_T]]
