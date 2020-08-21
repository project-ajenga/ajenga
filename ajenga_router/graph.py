from abc import ABC
from collections import deque
from typing import Any
from typing import AsyncIterable
from typing import Dict
from typing import Hashable
from typing import Iterable
from typing import Set
from typing import Tuple
from typing import final

from .exceptions import RouteFilteredException
from .utils import as_completed


class Node(ABC):
    """Abstraction class for Node
    """

    @property
    def __id__(self) -> Hashable:
        """Identity for node

        Used for merging two equal nodes

        :return: Hashable id_
        """
        return type(self).__name__

    def copy(self, **kwargs) -> "Node":
        """Copy of node

        :param kwargs: For internal use
        :return: Copy
        """
        raise NotImplementedError

    @property
    def predecessors(self) -> "Set[Tuple[NonterminalNode, Hashable]]":
        """Predecessors, in_edges

        :return:
        """
        raise NotImplementedError

    @property
    def predecessor_nodes(self) -> "Set[Tuple[NonterminalNode]]":
        """Predecessors, in_nodes

        :return:
        """
        raise NotImplementedError

    def add_predecessor(self, node: "Tuple[NonterminalNode, Hashable]"):
        raise NotImplementedError

    def remove(self):
        raise NotImplementedError

    # def __eq__(self, other):
    #     raise NotImplementedError
    #
    # def __hash__(self):
    #     return hash(self.__id__)

    def debug_fmt(self, indent=1, verbose=False) -> str:
        """Format the debug string

        :param indent: Increment indent for each layer of nodes
        :param verbose: Show object id_
        :return: Formatted string
        """
        raise NotImplementedError


class TerminalNode(Node, ABC):
    """Abstraction class for TerminalNode

    Last layer of nodes, to close a graph
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __id__(self) -> Hashable:
        return id(self)

    async def forward(self, *args, **kwargs) -> Any:
        """Forward input to terminal and invoke

        In particular, to call the handler

        :param args:
        :param kwargs:
        :return:
        """
        raise NotImplementedError

    def debug_fmt(self, indent=1, verbose=False) -> str:
        if verbose:
            return f'{" ":{indent}}<{type(self).__name__} {str(self)}>'
        else:
            return f'{" ":{indent}}<{type(self).__name__}>'


class NonterminalNode(Node, ABC):
    """Abstraction class for NonterminalNode

    Contains a layer of successor nodes
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def route(self, *args, **kwargs) -> AsyncIterable[TerminalNode]:
        """Get terminals routing from the node given arguments

        :param args:
        :param kwargs:
        :return: AsyncIterator of Terminals
        """
        yield
        raise NotImplementedError

    def copy(self, node_map: Dict[Node, Node] = ...) -> "NonterminalNode":
        raise NotImplementedError

    @property
    def empty(self) -> bool:
        """Indicate the node has not added terminals

        :return:
        """
        raise NotImplementedError

    def clear(self):
        """Reinitialize the node, clear all successors

        :return:
        """
        raise NotImplementedError

    @property
    def successors(self) -> Iterable[Node]:
        """Successors

        :return:
        """
        raise NotImplementedError

    # def add_key(self, key):
    #     raise NotImplementedError

    def add_successor(self, node):
        """Add a successor

        :param node: Successor node
        :return:
        """
        raise NotImplementedError

    def remove_successor(self, node):
        """Remove a successor

        :param node:
        :return:
        """
        raise NotImplementedError

    def __ior__(self, other):
        """Merge with other equal node

        :param other: Other node (with same type and id_)
        :return: Self
        """
        raise NotImplementedError

    def debug_fmt(self, indent=1, verbose=False) -> str:
        if verbose:
            return f'{" ":{indent}}<{type(self).__name__} {str(self)}>'
        else:
            return f'{" ":{indent}}<{type(self).__name__}>'


class AbsNode(Node, ABC):
    _predecessors: Set[Tuple[NonterminalNode, Hashable]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._predecessors = set()

    @property
    def predecessors(self) -> "Set[Tuple[NonterminalNode, Hashable]]":
        return self._predecessors.copy()

    @property
    def predecessor_nodes(self) -> "Set[Tuple[NonterminalNode]]":
        return set(map(lambda e: e[0], self._predecessors))

    def add_predecessor(self, node: "Tuple[NonterminalNode, Hashable]"):
        if node in self._predecessors:
            self._predecessors.remove(node)
        self._predecessors.add(node)

    def remove(self):
        pre_nodes = list(map(lambda e: e[0], self._predecessors))
        for pre_node in pre_nodes:
            pre_node.remove_successor(self)
            if not pre_node.successors:
                pre_node.remove()
        self._predecessors.clear()

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.__id__ == other.__id__ and
                self.predecessors == other.predecessors
                )

    def __hash__(self):
        return hash(self.__id__)


@final
class IdentityNode(NonterminalNode, AbsNode):
    _successors: Set[Node]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._successors = set()

    def copy(self, node_map: Dict[Node, Node] = ...) -> "IdentityNode":
        ret = IdentityNode()
        if node_map is ...:
            node_map = {}
        for node in self._successors:
            ret.add_successor(node_map.setdefault(node, node.copy(node_map=node_map)))
        return ret

    @property
    def empty(self) -> bool:
        return not bool(self._successors)

    def clear(self):
        self._successors.clear()

    @property
    def successors(self) -> Iterable[Node]:
        return self._successors.copy()

    def add_successor(self, node):
        for u in self._successors:
            if isinstance(u, NonterminalNode) and u == node:
                u |= node
                break
        else:
            self._successors.add(node)
            node.add_predecessor((self,))

    def remove_successor(self, node):
        if node in self._successors:
            self._successors.remove(node)

    def __ior__(self, other):
        if isinstance(other, IdentityNode):
            for node in other._successors:
                self.add_successor(node)
            return self
        else:
            raise ValueError(f"Cannot apply operator ior between {type(self)} and {type(other)}")

    def debug_fmt(self, indent=1, verbose=False) -> str:
        out_str = ''
        inner_str = '\n'.join(node.debug_fmt(indent=2) for node in self._successors)
        inner_str = '\n'.join(map(lambda x: f'{" ":{indent + 2}}' + x, inner_str.split('\n')))
        out_str += f'{" ":{indent + 2}}[ \n{inner_str} \n{" ":{indent + 2}}]' + '\n'
        if verbose:
            return f'{" ":{indent}}<{type(self).__name__} : \n{out_str}{" ":{indent}}>'
        else:
            return f'{" ":{indent}}<{type(self).__name__} {str(self)}: \n{out_str}{" ":{indent}}>'

    async def route(self, *args, **kwargs) -> AsyncIterable[TerminalNode]:
        for node in self._successors:
            if isinstance(node, TerminalNode):
                yield node
            elif isinstance(node, NonterminalNode):
                async for terminal in node.route(*args, **kwargs):
                    yield terminal


class Graph:
    """State Transition Graph

    To inherit this class, should override the following:
        __init__
        copy
        __call__
    """
    _start: IdentityNode
    _closed: bool

    def __init__(self, start=None, closed=False):
        self._start = start or IdentityNode()
        self._closed = closed
        self.num_workers = 20

    @property
    def start(self) -> IdentityNode:
        """Start node

        :return:
        """
        return self._start

    @property
    def closed(self) -> bool:
        """Indicate the graph is close thus cannot concentrate other graph

        :return:
        """
        return self._closed

    @property
    def entries(self) -> Iterable[Node]:
        """First layer nodes, successors of start node

        :return:
        """
        return self.start.successors

    def remove_terminals(self, terminals: Iterable[TerminalNode]):
        """Remove given terminals and eliminate unused nonterminals in path

        :param terminals:
        :return:
        """
        for terminal in terminals:
            terminal.remove()

    def traverse(self) -> Iterable[Node]:
        """Traverse the graph in DFS

        :return:
        """
        queue = deque()
        queue.append(self.start)
        while queue:
            node = queue.popleft()
            if isinstance(node, NonterminalNode):
                for successor in node.successors:
                    queue.append(successor)
            yield node

    @property
    def curve(self) -> Set[NonterminalNode]:
        """Curve nonterminals for open graph

        :return:
        """
        ret = set()
        for node in self.traverse():
            if isinstance(node, NonterminalNode) and node.empty:
                ret.add(node)
        return ret

    @property
    def terminals(self) -> Set[TerminalNode]:
        """Terminals for closed graph

        :return:
        """
        ret = set()
        for node in self.traverse():
            if isinstance(node, TerminalNode):
                ret.add(node)
        return ret

    def verify(self) -> bool:
        for node in self.traverse():
            if isinstance(node, NonterminalNode):
                for nn in node.successors:
                    if node not in nn.predecessor_nodes:
                        print('-------------------Verify-------------------------')
                        print(f'---------Current Node: {node}--------------------')
                        print(f'---------Succ Node:  {nn}----------------')
                        print(f'---------Succ Pred Nodes: {nn.predecessors}-----')
                        return False
        return True

    def add_edge(self, u: NonterminalNode, v: Node):
        """Util function for add an edge

        :param u: node from
        :param v: node to
        :return:
        """
        u.add_successor(v)

    def clear(self):
        """Clear graph

        :return:
        """
        self.start.clear()

    def copy(self):
        """Copy of graph

        :return:
        """
        return type(self)(start=self.start.copy(), closed=self.closed)

    def __copy__(self):
        return self.copy()

    def apply(self, terminal: TerminalNode = None) -> "Graph":
        """Apply graph to function, make the function terminal and create closed graph

        :param terminal:
        :return: Closed graph
        """
        # assert self.verify()

        if self.closed:
            raise ValueError("Cannot apply on a closed graph!")
        g = self.copy()
        if terminal:
            terminal = terminal
            for node in g.curve:
                node.add_successor(terminal)
        g._closed = True
        return g

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def _and(self, other):
        if self.closed:
            raise ValueError("Cannot apply on a closed graph!")
        elif isinstance(other, Graph):
            us = list(self.curve)
            vs = list(other.entries)
            if len(us) > 1 and len(vs) > 1:
                [self.add_edge(u, other.start) for u in us]
            else:
                [self.add_edge(u, v) for u in us for v in vs]

        elif isinstance(other, NonterminalNode):
            for node in self.curve:
                self.add_edge(node, other)
        else:
            raise ValueError(f"Cannot apply operator and between {type(self)} and {type(other)}")

    def __iand__(self, other):
        """Concentrate with graph

        :param other:
        :return:
        """
        self._and(other)
        return self

    def __and__(self, other):
        """Concentrate two graphs

        :param other:
        :return:
        """
        g = self.copy()
        g._and(other)
        return g

    def _or(self, other):
        if isinstance(other, Graph):
            for node in other.entries:
                self.add_edge(self.start, node)
        elif isinstance(other, NonterminalNode):
            self.add_edge(self.start, other)
        else:
            raise ValueError(f"Cannot apply operator or between {type(self)} and {type(other)}")

    def __ior__(self, other):
        """Conjunct with graph

        :param other:
        :return:
        """
        self._or(other)
        return self

    def __or__(self, other):
        """Conjunct two graphs

        :param other:
        :return:
        """
        g = self.copy()
        g._or(other)
        return g

    async def forward(self, *args, **kwargs) -> AsyncIterable[TerminalNode]:
        """Forward input to the graph, asynchronous invoke terminals and yield

        :param args:
        :param kwargs:
        :return:
        """
        if not self.closed:
            raise ValueError("Cannot apply on a open graph!")

        terminals = set()
        filters = set()

        async for terminal in self.start.route(*args, **kwargs):
            if isinstance(terminal, TerminalNode):
                terminals.add(terminal)
            elif isinstance(terminal, RouteFilteredException):
                filters.add(terminal.args[0])
            else:
                raise ValueError(terminal)

        for filter_ in filters:
            terminals = filter(filter_, terminals)

        # print(terminals)
        coroutines = list(map(lambda x: x.forward(*args, **kwargs), terminals))

        async for res in as_completed(*coroutines, num_workers=self.num_workers):
            yield res

    def debug_fmt(self, indent=1) -> str:
        """Format the debug string

        :param indent:
        :return:
        """
        return f'{" ":{indent}}<Graph: \n{self.start.debug_fmt(indent + 2)}>'
