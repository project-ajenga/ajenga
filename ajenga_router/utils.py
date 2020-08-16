import inspect
import typing
from functools import wraps
from typing import List, Any, Set, Callable, Dict, Iterator, Iterable, Union, Awaitable, AsyncIterable, final, Hashable
import asyncio

T = typing.TypeVar("T")


def wrap_function(func: Callable):
    _func = func
    _async = asyncio.iscoroutinefunction(func)

    # Generate signature
    sig = inspect.signature(func)
    _args_num = 0
    _args_extra = False
    _kwargs_keys = []
    _kwargs_extra = False

    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            _args_num += 1
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            _args_extra = True
        elif param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            _kwargs_keys.append(param.name)
        elif param.kind == inspect.Parameter.KEYWORD_ONLY:
            _kwargs_keys.append(param.name)
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            _kwargs_extra = True
        else:
            raise TypeError("Invalid parameter declaration for HandlerNode !")

    @wraps(func)
    async def wrapper(args, store):
        if len(args) > _args_num and not _args_extra:
            kwargs_keys = _kwargs_keys[len(args) - _args_num:]
        else:
            kwargs_keys = _kwargs_keys

        if _kwargs_extra:
            kwargs = dict(filter(lambda e: isinstance(e[0], str), store.items()))
        else:
            kwargs = dict(filter(lambda e: e[0] in kwargs_keys, store.items()))

        return await _func(*args, **kwargs) if _async else _func(*args, **kwargs)

    return wrapper


async def run_async(func: Callable[[Any], Union[T, Awaitable[T]]], *args, **kwargs) -> T:
    return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)


def raise_(e: BaseException):
    raise e


async def consume_async_iterator(ait: AsyncIterable[T]) -> List[T]:
    result = []
    async for x in ait:
        result.append(x)
    return result


def max_instances(number):
    def deco(func):
        _sem = asyncio.Semaphore(number)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with _sem:
                return await func(*args, **kwargs)

        return wrapper

    return deco
