"""
Core template processing functionality.
"""

from typing import Any, Dict

from . import loader
from .cache import TemplateCache
from .exceptions import TemplateRenderError
from .lexer import Lexer
from .nodes import DEFAULT_SLOT_NAME, BlockNode, ExtendsNode, ParentNode, split_slots
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
        self,
        template: str,
        context: Dict[str, Any],
        template_name: str = None,
        template_path: str = None,
        inherit: bool = True,
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

        # A template renders differently depending on whether the layout it
        # extends is rendered around it, so the two are cached apart. The key is
        # the template itself, marked rather than the context, which is the
        # caller's and is looked up with as it was given.
        cache_key = template if inherit else f"\0own\0{template}"

        # Check cache first
        cached_result = self.cache.get(cache_key, cache_context)
        if cached_result is not None:
            return cached_result

        try:
            tokens = Lexer(template).tokenize()
            nodes = Parser(tokens).parse()

            if inherit:
                # If the template extends another one, render the resulting tree
                # instead, with the slots the template passes to its layout.
                nodes, inherited_context = self._resolve_inheritance(nodes, self.context)
                self.context.update(inherited_context)
            else:
                # Rendering the template for itself: what it extends says what
                # surrounds it, and nothing surrounds it here.
                nodes = self._own_nodes(nodes)

            output = []
            for node in nodes:
                rendered = node.render(self.context)
                if rendered is not None:
                    output.append(str(rendered))

            result = "".join(output)

            # Save cache
            self.cache.set(cache_key, cache_context, result)

            return result

        except Exception as e:
            raise e

    def _own_nodes(self, nodes):
        """The content of a template, without the layout it extends.

        What a template extends says what surrounds it on a page. Rendered for
        itself rather than as a page, as a live component is when it answers an
        action, it is that content alone that is wanted: the layout is already
        on the page, around the very element the answer is morphed into.
        """
        if not any(isinstance(node, ExtendsNode) for node in nodes):
            return nodes

        # The same split inheritance makes, keeping the part that would have
        # become the layout's default slot
        _, slots = self._split_child_nodes(nodes)

        return slots[DEFAULT_SLOT_NAME].nodes

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

        overrides, slots = self._split_child_nodes(nodes)

        layout = loader.load_template(layout_name)
        layout_nodes = Parser(Lexer(layout.content or "").tokenize()).parse()

        try:
            layout_nodes, inherited = self._resolve_inheritance(layout_nodes, context, [*_seen, layout_name])
        except TemplateRenderError as exc:
            if getattr(exc, "template", None) is None:
                setattr(exc, "template", layout)
            raise

        context_updates = dict(inherited)
        context_updates.update(slots)

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

        Returns a tuple (overrides, slots): the blocks the template overrides, and the slots it
        hands over to its layout. The slots are the very same ones a component receives, the
        content left outside of any block making up the default slot.
        """
        overrides = {}
        remaining = []

        for node in nodes:
            if isinstance(node, ExtendsNode):
                continue

            if isinstance(node, BlockNode):
                overrides[node.block_name()] = node.body
            else:
                remaining.append(node)

        return overrides, split_slots(remaining)

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
        name = block.block_name()

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
