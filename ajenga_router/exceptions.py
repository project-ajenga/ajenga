from typing import Any
from typing import Callable
from typing import Iterable

from typing import TypeVar

from typing import Tuple

T = TypeVar('T')


class RouteException(BaseException):
    pass


class RouteAllFilteredException(RouteException):
    def __init__(self,
                 filter_: Callable[[Iterable[T], Any], Tuple[Iterable[T], bool]] =
                 lambda terminals, args, store: (),
                 priority: int = 0):
        self.filter_ = filter_
        self.priority = priority

    def __call__(self, *args, **kwargs):
        return self.filter_(*args, **kwargs)


class RouteFilteredException(RouteAllFilteredException):
    def __init__(self,
                 filter_: Callable[[T], bool] = lambda _: False,
                 priority: int = 0):
        super().__init__(
            lambda terminals, args, store: (filter(filter_, terminals), True),
            priority
        )
