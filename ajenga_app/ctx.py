import asyncio
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from typing import AsyncIterable
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from ajenga.log import logger
from ajenga.message import MessageIdType
from ajenga_router import std
from ajenga_router.models import AbsNode
from ajenga_router.models import Graph
from ajenga_router.models import Node
from ajenga_router.models import Executor
from ajenga_router.models import TerminalNode
from ajenga_router.keystore import KeyStore
from ajenga_router.utils import as_completed
from ajenga_router.utils import wrap_function


class Priority:
    Wakeup = 100
    Default = 0
    Never = -1


class PriorityExecutor(Executor):
    @dataclass
    class Context:
        next_priority: bool = True

    def __init__(self):
        self._num_workers = 20

    async def __call__(self, __execute_terminals__: Iterable[TerminalNode], *args, **kwargs) -> AsyncIterable:
        terminals = list(__execute_terminals__)
        terminal_pairs = list((x.priority if hasattr(x, 'priority') else 0, x) for x in terminals)
        terminal_pairs.sort(key=lambda x: x[0], reverse=True)
        terminal_groups: List[List[Tuple[int, TerminalNode]]] = []
        for priority, terminal in terminal_pairs:
            if terminal_groups and priority == terminal_groups[-1][0]:
                terminal_groups[-1].append((priority, terminal))
            elif priority < 0:
                break
            else:
                terminal_groups.append([(priority, terminal)])

        for terminal_group in terminal_groups:
            coroutines = list(terminal.forward(*args, **kwargs) for _, terminal in terminal_group)
            context = self.Context()
            token = _executor_context.set(context)
            async for res in as_completed(*coroutines, num_workers=self._num_workers):
                yield res
            _executor_context.reset(token)
            if not context.next_priority:
                break


_executor_context: ContextVar[PriorityExecutor.Context] = ContextVar('_executor_context')


class ContextHandlerNode(TerminalNode, AbsNode):
    args: Tuple
    kwargs: Dict
    priority: int

    def __init__(self, func: Callable, *args, priority: int = Priority.Default, **kwargs):
        super().__init__()
        self._original_func = func
        self._func = wrap_function(func)
        self.priority = priority
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return repr(self._func)

    def copy(self, node_map: Dict[Node, Node] = ...) -> "ContextHandlerNode":
        return ContextHandlerNode(self._original_func, *self.args, priority=self.priority, **self.kwargs)

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


def ContextHandler(*args, **kwargs):
    def deco(func: Callable):
        return ContextHandlerNode(func, *args, **kwargs)
    return deco


@dataclass
class HandlerContext:
    node: TerminalNode
    args: Tuple
    store: KeyStore
    last_active_time: float
    # timeout: float = 3600
    suspend_other: bool = False,
    suspend_next_priority: bool = False,
    future: Optional[asyncio.Future] = None

    @property
    def waiting(self):
        return bool(self.future) and not self.future.done()


_context: ContextVar[HandlerContext] = ContextVar('_context')


from ajenga_app import app
from ajenga_app.app import BotSession

_CANDIDATES_KEY = '_wakeup_candidates'


class _ContextWrapperMeta(type):

    def __getattr__(cls, item):
        return _context.get().store.get(item)


class _ContextWrapper(metaclass=_ContextWrapperMeta):
    @classmethod
    async def wait_until(cls,
                         graph: Graph = std.true,
                         *,
                         timeout: float = 3600,
                         suspend_other: bool = False,
                         suspend_next_priority: bool = False,
                         ):

        context = _context.get()
        context.future = asyncio.get_event_loop().create_future()
        context.suspend_other = suspend_other
        context.suspend_next_priority = suspend_next_priority

        async def _check_timeout():
            cur_time = time.time()
            if cur_time - context.last_active_time > timeout:
                context.future.set_exception(TimeoutError())
                app.engine.unsubscribe_terminals([_dumpy_node])
                return False
            return True

        async def _set_suspend(_store: KeyStore):
            if _CANDIDATES_KEY not in _store:
                _store[_CANDIDATES_KEY] = []
            _store[_CANDIDATES_KEY].append((context, _dumpy_node))

        @app.on(std.if_(_check_timeout) &
                graph &
                std.process(_set_suspend))
        @ContextHandler(priority=Priority.Never)
        async def _dumpy_node():
            pass

        context.args, context.store = await context.future

    @classmethod
    async def wait_quote(cls, source: BotSession, id_: MessageIdType):
        raise NotImplementedError


@app.on(std.true)
@ContextHandler(priority=Priority.Wakeup)
async def _check_wait(*args, _store: KeyStore):
    def _wakeup(content, node):
        if content.waiting:
            content.future.set_result((args, _store))
        app.engine.unsubscribe_terminals([node])

    candidates: List[Tuple[HandlerContext, TerminalNode]] = _store.get(_CANDIDATES_KEY, [])
    candidates.sort(key=lambda e: e[0].last_active_time)

    _suspend_other = False
    _suspend_next_priority = False

    while not _suspend_other and candidates:
        candidate, dumpy_node = candidates.pop()
        _suspend_other = candidate.suspend_other
        _suspend_next_priority |= candidate.suspend_next_priority
        _wakeup(candidate, dumpy_node)

    if _suspend_next_priority:
        _executor_context.get().next_priority = False


class TimeoutError(Exception):
    pass


this = _ContextWrapper
