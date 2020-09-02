from typing import AsyncIterable
from typing import Iterable
from typing import Type
from typing import final

from .graph import Graph
from .graph import TerminalNode
from .keystore import KeyStore
from .std import HandlerNode


@final
class GraphImpl(Graph):
    """Graph implementation supports __call__ as decorator

    """
    _handler_cls: Type[TerminalNode]

    def __init__(self, graph, *, handler_cls: Type[TerminalNode], **kwargs):
        super().__init__(**kwargs)
        self._graph = graph
        self._handler_cls = handler_cls

    def apply(self, terminal: TerminalNode = None) -> "Graph":
        return super().apply(terminal)

    def __call__(self, func) -> TerminalNode:
        if self.closed:
            raise ValueError("Cannot call on a closed graph!")
        if not isinstance(func, TerminalNode):
            func = self._handler_cls(func)
        g = self.apply(func)
        self._graph |= g
        return func

    def copy(self):
        return GraphImpl(graph=self._graph, handler_cls=self._handler_cls, start=self.start.copy(), closed=self.closed)


class Engine:
    """ A wrapper for decorator based graph applying

    """
    _graph: Graph
    _handler_cls: Type[TerminalNode]

    def __init__(self, *, handler_cls: Type[TerminalNode] = HandlerNode):
        self._graph = Graph().apply()
        self._handler_cls = handler_cls

    @property
    def graph(self) -> Graph:
        return self._graph

    @property
    def handler_cls(self) -> Type[TerminalNode]:
        return self._handler_cls

    def on(self, graph: Graph) -> Graph:
        return GraphImpl(graph=self._graph, handler_cls=self._handler_cls) & graph

    def subscribe(self, graph: Graph):
        # TODO: Subscribe does not copy the graph, thus returned frozen graph can change!
        if graph.closed:
            self._graph |= graph
        else:
            raise ValueError("Cannot subscribe an open graph!")

    # def unsubscribe(self, graph: Graph):
    #     if graph.closed:
    #         self._graph.remove_terminals(graph.terminals)
    #     else:
    #         raise ValueError("Cannot unsubscribe an open graph!")

    def unsubscribe_terminals(self, terminals: Iterable[TerminalNode]):
        self._graph.remove_terminals(terminals)

    def forward(self, *args, **kwargs) -> AsyncIterable:
        return self._graph.copy().forward(args, KeyStore(kwargs))

    def clear(self):
        self._graph.clear()
