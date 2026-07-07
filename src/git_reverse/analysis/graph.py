"""
In-memory directed dependency graph builder using NetworkX.

Resolves relationships between ParsedSymbols (calls, imports, belongs_to)
and builds a directed graph structure.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from git_reverse.analysis.parsers.base import ParsedSymbol


class KnowledgeGraphBuilder:
    """Constructs directed dependency graph from parsed symbols."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def build(self, symbols: list[ParsedSymbol]) -> nx.DiGraph:
        """
        Build a NetworkX DiGraph from a flat list of parsed symbols.
        
        Nodes represent: modules, classes, functions, structs.
        Edges represent:
          - "contains" (class contains function, module contains class/function).
          - "calls" (function calls another function).
          - "imports" (module imports another module).
          - "inherits" (class inherits from another class).
        """
        # 1. Add all nodes
        symbol_map: dict[str, ParsedSymbol] = {}
        file_modules: dict[str, str] = {}  # file_path -> module symbol id

        for sym in symbols:
            symbol_map[sym.id] = sym
            node_attrs = {
                "type": sym.type,
                "name": sym.name,
                "language": sym.language,
                "file_path": sym.file_path,
                "start_line": sym.start_line,
                "end_line": sym.end_line,
            }
            node_attrs.update(sym.metadata)
            self.graph.add_node(sym.id, **node_attrs)
            
            if sym.type == "module":
                file_modules[sym.file_path] = sym.id

        # 2. Add structural edges (contains)
        # Classify nested functions or classes under their parent modules or classes
        for sym in symbols:
            if sym.type == "module":
                continue
                
            # If function belongs to a class or module, link it
            parent_id = None
            
            # Find class parent if defined in same file and covers the line range
            if sym.type == "function":
                for other in symbols:
                    if other.type == "class" and other.file_path == sym.file_path:
                        if other.start_line <= sym.start_line <= other.end_line:
                            parent_id = other.id
                            break
                            
            # Fall back to containing module
            if not parent_id:
                parent_id = file_modules.get(sym.file_path)

            if parent_id:
                self.graph.add_edge(parent_id, sym.id, relation="contains")

        # 3. Add inheritance edges (inherits)
        class_name_map = {s.name: s.id for s in symbols if s.type in ("class", "struct")}
        for sym in symbols:
            if sym.type in ("class", "struct") and sym.bases:
                for base in sym.bases:
                    if base in class_name_map:
                        self.graph.add_edge(sym.id, class_name_map[base], relation="inherits")

        # 4. Add call edges (calls)
        # Find functions by name
        fn_name_map: dict[str, str] = {}
        for s in symbols:
            if s.type == "function":
                fn_name_map[s.name] = s.id
                # Strip class prefix in Go / C++ / Python methods if stored simply
                if "." in s.name:
                    fn_name_map[s.name.split(".")[-1]] = s.id

        for sym in symbols:
            if sym.type == "function" and sym.calls:
                for call in sym.calls:
                    # Resolve to local function
                    called_id = fn_name_map.get(call)
                    if not called_id and "." in call:
                        called_id = fn_name_map.get(call.split(".")[-1])
                    if called_id:
                        self.graph.add_edge(sym.id, called_id, relation="calls")

        return self.graph
