import time
from typing import List
from typing import Tuple

from ajenga.message import MessageIdType
from ajenga_app import app
from ajenga_app.app import BotSession
from ajenga_router import std
from ajenga_router.keystore import KeyStore
from ajenga_router.models import Graph
from ajenga_router.models import Task
from ajenga_router.models import TerminalNode
from ajenga_router.models.execution import Priority
from ajenga_router.models.execution import _executor_context
from ajenga_router.models.execution import _task_context

_CANDIDATES_KEY = '_wakeup_candidates'
_SUSPEND_OTHER_KEY = 'suspend_other'
_SUSPEND_NEXT_PRIORITY = 'suspend_next_priority'


class _ContextWrapperMeta(type):

    def __getattr__(cls, item):
        return _task_context.get().args[1][item]


class _ContextWrapper(metaclass=_ContextWrapperMeta):
    @classmethod
    async def wait_until(cls,
                         graph: Graph = std.true,
                         *,
                         timeout: float = 3600,
                         suspend_other: bool = False,
                         suspend_next_priority: bool = False,
                         ):

        task = _task_context.get()
        task.state[_SUSPEND_OTHER_KEY] = suspend_other
        task.state[_SUSPEND_NEXT_PRIORITY] = suspend_next_priority

        async def _check_timeout():
            cur_time = time.time()
            if cur_time - task.last_active_time > timeout:
                task.raise_(TimeoutError)
                app.engine.unsubscribe_terminals([_dumpy_node])
                return False
            return True

        async def _set_suspend(_store: KeyStore):
            if _CANDIDATES_KEY not in _store:
                _store[_CANDIDATES_KEY] = []
            _store[_CANDIDATES_KEY].append((task, _dumpy_node))

        @app.on(std.if_(_check_timeout) &
                graph &
                std.process(_set_suspend))
        @std.handler(priority=Priority.Never)
        async def _dumpy_node():
            pass

        await task.pause()

    @classmethod
    async def wait_quote(cls, source: BotSession, id_: MessageIdType):
        raise NotImplementedError

    @classmethod
    def suspend_next_priority(cls):
        _executor_context.get().next_priority = False


@app.on(std.true)
@std.handler(priority=Priority.Wakeup)
async def _check_wait(_store: KeyStore):
    def _wakeup(candi, node):
        candi.priority = _task_context.get().priority
        _executor_context.get().add_task(candi)
        app.engine.unsubscribe_terminals([node])

    candidates: List[Tuple[Task, TerminalNode]] = _store.get(_CANDIDATES_KEY, [])
    candidates.sort(key=lambda e: e[0].last_active_time)

    _suspend_other = False
    _suspend_next_priority = False

    while not _suspend_other and candidates:
        candidate, dumpy_node = candidates.pop()
        _suspend_other = candidate.state[_SUSPEND_OTHER_KEY]
        _suspend_next_priority |= candidate.state[_SUSPEND_NEXT_PRIORITY]
        _wakeup(candidate, dumpy_node)

    if _suspend_next_priority:
        _executor_context.get().next_priority = False


class TimeoutError(Exception):
    pass


this = _ContextWrapper
