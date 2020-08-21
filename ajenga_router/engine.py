from typing import List, Any, Set, Callable, Dict, Iterator, Iterable, AsyncIterable, final
from .graph import Graph, NonterminalNode, IdentityNode, TerminalNode
from .keystore import KeyStore
from .std import HandlerNode


@final
class GraphImpl(Graph):
    """Graph implementation supports __call__ as decorator

    """
    def __init__(self, graph, **kwargs):
        super().__init__(**kwargs)
        self._graph = graph

    def apply(self, terminal: TerminalNode = None) -> "Graph":
        return super().apply(terminal)

    def __call__(self, func) -> TerminalNode:
        if self.closed:
            raise ValueError("Cannot call on a closed graph!")
        if not isinstance(func, TerminalNode):
            func = HandlerNode(func)
        g = self.apply(func)
        self._graph |= g
        return func

    def copy(self):
        return GraphImpl(graph=self._graph, start=self.start.copy(), closed=self.closed)


class Engine:
    """ A wrapper for decorator based graph applying

    """
    _graph: Graph

    def __init__(self):
        self._graph = Graph().apply()

    @property
    def graph(self) -> Graph:
        return self._graph

    def on(self, graph: Graph) -> Graph:
        return GraphImpl(graph=self._graph) & graph

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
        return self._graph.forward(args, KeyStore(kwargs))

    def clear(self):
        self._graph.clear()
