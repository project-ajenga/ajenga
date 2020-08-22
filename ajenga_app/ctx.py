import asyncio
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from ajenga.log import logger
from ajenga.message import MessageIdType
from ajenga_app import app
from ajenga_app.app import BotSession
from ajenga_router import std
from ajenga_router.exceptions import RouteAllFilteredException
from ajenga_router.graph import AbsNode
from ajenga_router.graph import Graph
from ajenga_router.graph import TerminalNode
from ajenga_router.keyfunc import RawKeyFunctionImpl
from ajenga_router.keystore import KeyStore
from ajenga_router.utils import wrap_function


class ContextHandlerNode(TerminalNode, AbsNode):
    args: Tuple
    kwargs: Dict

    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self._original_func = func
        self._func = wrap_function(func)
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return repr(self._func)

    def copy(self) -> "ContextHandlerNode":
        return ContextHandlerNode(self._original_func, *self.args, **self.kwargs)

    def __call__(self, *args, **kwargs):
        return self._original_func(*args, **kwargs)

    async def forward(self, args, store) -> Any:
        token = _context.set(HandlerContext(node=self,
                                            args=args,
                                            store=store,
                                            last_active_time=time.time(),
                                            ))
        try:
            return await self._func(args, store)
        except Exception as e:
            logger.exception(e)
            raise
        finally:
            _context.reset(token)

    def debug_fmt(self, indent=1, verbose=False) -> str:
        if verbose:
            return f'{" ":{indent}}<Func {str(self)}: {self._func.__name__}>'
        else:
            return f'{" ":{indent}}<Func : {self._func.__name__}>'


@dataclass
class HandlerContext:
    node: TerminalNode
    args: Tuple
    store: KeyStore
    last_active_time: float
    timeout: float = 3600
    allow_other: bool = False,
    allow_other_wakeup: bool = False
    future: Optional[asyncio.Future] = None

    @property
    def waiting(self):
        return bool(self.future) and not self.future.done()


_context: ContextVar[HandlerContext] = ContextVar('_context')


class TimeoutError(Exception):
    pass


class _ContextWrapperMeta(type):

    def __getattr__(cls, item):
        return _context.get().store.get(item)


_CANDIDATES_KEY = '_wakeup_candidates'


def _wakeup_filter_func(terminals: Iterable[TerminalNode], args, store: KeyStore) -> Tuple[
    Iterable[TerminalNode], bool]:
    def _wakeup(content, node):
        if content.waiting:
            content.future.set_result((args, store))
        app.engine.unsubscribe_terminals([node])

    candidates: List[Tuple[HandlerContext, TerminalNode]] = store[_CANDIDATES_KEY]
    candidates.sort(key=lambda e: e[0].last_active_time)

    candidate, dumpy_node = candidates.pop()
    _allow_other = candidate.allow_other
    _allow_other_wakeup = candidate.allow_other_wakeup
    _wakeup(candidate, dumpy_node)

    while _allow_other_wakeup and candidates:
        candidate, dumpy_node = candidates.pop()
        if _allow_other != candidate.allow_other or _allow_other_wakeup != candidate.allow_other_wakeup:
            continue
        _wakeup(candidate, dumpy_node)

    return terminals, _allow_other


_wakeup_filter = RouteAllFilteredException(_wakeup_filter_func, priority=10)


class _ContextWrapper(metaclass=_ContextWrapperMeta):
    @classmethod
    async def wait_until(cls,
                         graph: Graph = std.true,
                         *,
                         timeout: float = 3600,
                         allow_other: bool = False,
                         allow_other_wakeup: bool = False):

        context = _context.get()

        context.timeout = timeout
        context.allow_other = allow_other
        context.allow_other_wakeup = allow_other_wakeup

        async def _add_candidate(_store: KeyStore):
            if _CANDIDATES_KEY not in _store:
                _store['_wakeup_candidates'] = []
            _store['_wakeup_candidates'].append((context, _dumpy_node))
            raise _wakeup_filter

        # TODO: Change this
        #   Cannot remove terminal during routing!!!
        #   Also, Timeout should not only triggered by event
        #   Well, maybe a cron event?

        async def _check_timeout():
            cur_time = time.time()
            if cur_time - context.last_active_time > context.timeout:
                context.future.set_exception(TimeoutError())
                app.engine.unsubscribe_terminals([_dumpy_node])
                return False
            return True

        @app.on(std.if_(_check_timeout) &
                graph &
                std.process(_add_candidate)
                )
        def _dumpy_node():
            pass

        context.future = asyncio.get_event_loop().create_future()
        context.args, context.store = await context.future

    @classmethod
    async def wait_quote(cls, source: BotSession, id_: MessageIdType):
        raise NotImplementedError


this = _ContextWrapper
