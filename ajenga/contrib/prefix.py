import asyncio
import pygtrie
from typing import List, Callable, Tuple, Union, Iterable, Optional
from aiocqhttp import Event as CQEvent

from ajenga import Ajenga, message_processor, MessageProcessorSolver, Service
from ajenga.exceptions import FailedException, FinishedException, SwitchedException
from ajenga.helpers import join_str, run_async
from ajenga.log import logger


_trie = pygtrie.CharTrie()


@message_processor('prefix')
async def _on_prefix(bot: Ajenga, event: CQEvent, solver: MessageProcessorSolver):
    text = event.message.extract_plain_text().strip()
    pair = _trie.longest_prefix(text)
    logger.debug(f'Parsing prefix : {text}  {pair}')
    if pair:
        coros = list(run_async(func, bot, event) for func in pair.value)
        try:
            ret = await asyncio.gather(*coros)
        except Exception as e:
            logger.exception(e)
            raise FinishedException(False)
        raise FinishedException(any(ret))

    raise FinishedException(False)


def on_prefix(service, prefix: Union[str, Iterable[str]], *, aliases: Iterable[str] = (), **kwargs):
    if isinstance(prefix, str):
        prefix = (prefix, )
    if aliases:
        prefix = (*prefix, *aliases)

    def deco(func: Callable) -> Callable:
        if 'event' in kwargs and not kwargs['event'].startswith('message'):
            kwargs['event'] = join_str(('message', kwargs['event']))

        wrapper = service.make_wrapper(func, trigger_name='prefix', **kwargs)

        for pre in prefix:
            if pre in _trie:
                _trie[pre].append(wrapper)
            else:
                _trie[pre] = [wrapper]

        local_prefix = prefix

        @service.on_unload()
        async def unload():
            for pre in local_prefix:
                _trie[pre].remove(wrapper)

        return func
    return deco


setattr(Service, 'on_prefix', on_prefix)
