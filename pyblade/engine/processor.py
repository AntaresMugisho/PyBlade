"""
Core template processing functionality.
"""

from typing import Any, Dict

from . import loader
from .cache import TemplateCache
from .contexts import SlotContent
from .exceptions import TemplateRenderError
from .lexer import Lexer
from .nodes import BlockNode, ExtendsNode, ParentNode, SlotNode, TextNode
from .parser import Parser


class TemplateProcessor:
    """
    Main template processing class that coordinates parsing, caching,
    and rendering of templates.
    """

    # Attributes under which nodes store a list of child nodes.
    _node_list_attrs = ("body", "else_body", "empty_body", "default_body", "plural_body")

    # Attributes under which nodes store (expression, child nodes) pairs.
    _node_pair_list_attrs = ("elif_blocks", "cases")

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600, debug: bool = None, framework: str = None):
        self.cache = TemplateCache(max_size=cache_size, ttl=cache_ttl)
        self.context = {}

    def render(
        self, template: str, context: Dict[str, Any], template_name: str = None, template_path: str = None
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template: The template string to render
            context: The context dictionary
            template_name: Optional name of the template file

        Returns:
            The rendered template

        Raises:
            TemplateRenderError: If there's an error during rendering
        """

        self.context = context.copy() if context else {}

        # The context the cache key is built from, kept aside as rendering may
        # add entries to the context (slots, variables set by directives...).
        cache_context = self.context.copy()

        # Check cache first
        cached_result = self.cache.get(template, cache_context)
        if cached_result is not None:
            return cached_result

        try:
            tokens = Lexer(template).tokenize()
            nodes = Parser(tokens).parse()

            # If the template extends another one, render the resulting tree
            # instead, with the slots the template passes to its layout.
            nodes, inherited_context = self._resolve_inheritance(nodes, self.context)
            self.context.update(inherited_context)

            output = []
            for node in nodes:
                rendered = node.render(self.context)
                if rendered is not None:
                    output.append(str(rendered))

            result = "".join(output)

            # Save cache
            self.cache.set(template, cache_context, result)

            return result

        except Exception as e:
            raise e

    # TEMPLATE INHERITANCE
    # ------------------------------------------------------------------------------------------------------------

    def _resolve_inheritance(self, nodes, context=None, _seen=None):
        """
        Resolve the @extends directive of a parsed template, if any.

        A template that starts with `@extends('layout')` does not render on its own: its @block
        definitions override the blocks of the layout it extends, and everything it declares outside
        of a block becomes the layout's default `slot`.

        Inheritance is resolved on the nodes, before rendering:

        1. the template's top level is split into block overrides, named slots and the leftover
           content (the default slot);
        2. the layout is loaded, parsed and resolved the same way, which makes multi-level
           inheritance (page -> layout -> base layout) fall out naturally;
        3. the template's blocks are merged into the layout's nodes, @parent being replaced by the
           block content it overrides.

        The result is a single node tree rendered with the original context, so every other feature
        of the engine (components, includes, expressions, custom directives...) keeps working
        exactly as it does in a standalone template.

        Args:
            nodes: The parsed nodes of the template
            context: The rendering context, used to evaluate the layout name
            _seen: Internal, the layout names already visited, to detect cycles

        Returns:
            A tuple (nodes, context_updates) where nodes is the node tree to render and
            context_updates holds the slot and the named slots the template passes to its layout.
            Templates without @extends are returned untouched, along with an empty dictionary.
        """

        extends = next((node for node in nodes if isinstance(node, ExtendsNode)), None)
        if extends is None:
            return nodes, {}

        context = context or {}
        layout_name = self._layout_name(extends, context)

        _seen = _seen or []
        if layout_name in _seen:
            raise TemplateRenderError(
                f"Circular template inheritance detected: '{layout_name}' extends itself.",
                line=extends.line,
                column=extends.column,
                help="Make sure the templates in the @extends chain do not extend each other.",
            )

        overrides, named_slots, slot_nodes = self._split_child_nodes(nodes)

        layout = loader.load_template(layout_name)
        layout_nodes = Parser(Lexer(layout.content or "").tokenize()).parse()

        try:
            layout_nodes, inherited = self._resolve_inheritance(layout_nodes, context, [*_seen, layout_name])
        except TemplateRenderError as exc:
            if getattr(exc, "template", None) is None:
                setattr(exc, "template", layout)
            raise

        context_updates = dict(inherited)
        context_updates.update(named_slots)
        context_updates["slot"] = SlotContent(self._trim(slot_nodes))

        return self._apply_overrides(layout_nodes, overrides), context_updates

    def _layout_name(self, extends, context):
        """Evaluate the name of the layout an @extends directive points to."""
        help_message = "The @extends directive expects a template name, e.g. @extends('layouts.base')."

        try:
            layout_name = extends.layout_name(context)
        except Exception as exc:
            raise TemplateRenderError(
                f"Could not resolve the template name in @extends({extends.layout}): {exc}",
                line=extends.line,
                column=extends.column,
                help=help_message,
            )

        if not isinstance(layout_name, str) or not layout_name:
            raise TemplateRenderError(
                f"@extends expects a template name but got {layout_name!r}.",
                line=extends.line,
                column=extends.column,
                help=help_message,
            )

        return layout_name

    def _split_child_nodes(self, nodes):
        """
        Split the top level of an extending template.

        Returns a tuple (overrides, named_slots, slot_nodes): the blocks it overrides, the named
        slots it defines and the nodes making up its default slot.
        """
        overrides = {}
        named_slots = {}
        slot_nodes = []

        for node in nodes:
            if isinstance(node, ExtendsNode):
                continue

            if isinstance(node, BlockNode):
                overrides[self._name_of(node)] = node.body
            elif isinstance(node, SlotNode):
                named_slots[self._name_of(node)] = SlotContent(self._trim(node.body))
            else:
                slot_nodes.append(node)

        return overrides, named_slots, slot_nodes

    def _name_of(self, node):
        """
        The name a block or a slot is matched on.

        Names are usually literals, but an expression that cannot be evaluated without a context
        still matches its counterpart in the other template, as both are written the same way.
        """
        try:
            return node.eval(node.name, {})
        except Exception:
            return node.name

    def _apply_overrides(self, nodes, overrides):
        """Replace, in the given nodes, the body of every block the child template overrides."""
        resolved = []

        for node in nodes:
            if isinstance(node, BlockNode):
                resolved.append(self._override_block(node, overrides))
            else:
                self._transform_children(node, lambda body: self._apply_overrides(body, overrides))
                resolved.append(node)

        return resolved

    def _override_block(self, block, overrides):
        """Return the block with its content replaced by the child's, if it defines one."""
        name = self._name_of(block)

        if name not in overrides:
            block.body = self._apply_overrides(block.body, overrides)
            return block

        # Blocks nested in the overridden one may be overridden too, but this one is already
        # being replaced, hence the exclusion.
        inherited_body = self._apply_overrides(block.body, {k: v for k, v in overrides.items() if k != name})

        return BlockNode(
            block.name,
            self._expand_parent(overrides[name], inherited_body),
            line=block.line,
            column=block.column,
        )

    def _expand_parent(self, nodes, inherited_body):
        """Replace every @parent placeholder in the given nodes by the inherited content."""
        expanded = []

        for node in nodes:
            if isinstance(node, ParentNode):
                expanded.extend(inherited_body)
            else:
                self._transform_children(node, lambda body: self._expand_parent(body, inherited_body))
                expanded.append(node)

        return expanded

    def _transform_children(self, node, transform):
        """Apply the given transformation to every list of child nodes held by a node."""
        for attr in self._node_list_attrs:
            children = getattr(node, attr, None)
            if isinstance(children, list):
                setattr(node, attr, transform(children))

        for attr in self._node_pair_list_attrs:
            pairs = getattr(node, attr, None)
            if isinstance(pairs, list):
                setattr(node, attr, [(expression, transform(children)) for expression, children in pairs])

    def _trim(self, nodes):
        """
        Drop the blank text surrounding a slot's content.

        Removing directives from the child's top level leaves the whitespace that used to separate
        them behind, which would otherwise end up in the slot.
        """
        nodes = list(nodes)

        while nodes and self._is_blank(nodes[0]):
            nodes.pop(0)

        while nodes and self._is_blank(nodes[-1]):
            nodes.pop()

        if nodes and isinstance(nodes[0], TextNode):
            nodes[0] = TextNode(nodes[0].content.lstrip(), line=nodes[0].line, column=nodes[0].column)

        if nodes and isinstance(nodes[-1], TextNode):
            nodes[-1] = TextNode(nodes[-1].content.rstrip(), line=nodes[-1].line, column=nodes[-1].column)

        return nodes

    def _is_blank(self, node):
        """Whether a node is plain text made of whitespace only."""
        return isinstance(node, TextNode) and not node.content.strip()

    # CACHING
    # ------------------------------------------------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self.cache.clear()

    def invalidate_template(self, template: str, context: Dict[str, Any]) -> None:
        """
        Invalidate a specific template in the cache.

        Args:
            template: The template string
            context: The context dictionary
        """
        self.cache.invalidate(template, context)
