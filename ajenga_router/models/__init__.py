from typing import Union

from .node import *
from ..exceptions import RouteException

RouteResult_T = Union[TerminalNode, RouteException]

from .executor import Executor
from .graph import Graph
