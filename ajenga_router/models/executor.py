from typing import AsyncIterable
from typing import Iterable

from .node import TerminalNode
from ..utils import as_completed

from . import RouteResult_T


class Executor:
    async def __call__(self, __execute_terminals__: Iterable[RouteResult_T], *args, **kwargs) -> AsyncIterable:
        raise NotImplementedError
        yield


class SimpleExecutor(Executor):
    def __init__(self):
        self._num_workers = 20

    async def __call__(self, __execute_terminals__: Iterable[RouteResult_T], *args, **kwargs) -> AsyncIterable:
        coroutines = list(terminal.forward(*args, **kwargs) if isinstance(terminal, TerminalNode) else terminal
                          for terminal in __execute_terminals__)
        async for res in as_completed(*coroutines, num_workers=self._num_workers):
            yield res

