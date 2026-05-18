"""Back-compat shim. The block-rendering engine lives in
`densanon.core.site_builder` now; this module re-exports just the
surface the church-ops admin's loader needs (`render_page` +
`BLOCK_TYPES`).

Importing this module also imports `church_blocks`, which has the
side effect of registering the church-specific block types onto
densanon's shared default_registry.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make sibling densanon-core importable.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DENSANON_CORE = _REPO_ROOT.parent / "densanon-core"
if _DENSANON_CORE.is_dir() and str(_DENSANON_CORE) not in sys.path:
    sys.path.insert(0, str(_DENSANON_CORE))

# Make own scripts/ dir importable so `import church_blocks` works when
# the admin server importlib-loads this file from outside its own dir.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from densanon.core.site_builder import default_blocks  # noqa: F401
from densanon.core.site_builder.block_base import default_registry
from densanon.core.site_builder.renderer import render_page as _render_page

# Side-effect: register church-specific block types.
import church_blocks  # noqa: F401


def render_page(page_name: str, data: dict) -> str:
    """Render a page's blocks list — back-compat wrapper."""
    return _render_page(page_name, data, default_registry)


# The admin's GET /blocks/types endpoint reads `mod.BLOCK_TYPES` as a
# dict of {type_name: {label, default, ...}}. Build it lazily from the
# registry so additions to the registry show up automatically.
def _build_block_types_map() -> dict:
    return {
        bt.name: {
            "renderer": bt.renderer,
            "label": bt.label,
            "default": dict(bt.default),
            "nestable": bt.nestable,
        }
        for bt in default_registry.values()
    }


# Some consumers (the admin's existing loader) attribute-access this at
# import time. Build it once and re-build on each access for freshness.
class _BlockTypesView(dict):
    def __getitem__(self, key):
        # Re-read from registry in case a new block registered after
        # this view was created.
        d = _build_block_types_map()
        if key in d:
            return d[key]
        raise KeyError(key)

    def items(self):
        return _build_block_types_map().items()

    def keys(self):
        return _build_block_types_map().keys()

    def values(self):
        return _build_block_types_map().values()

    def __iter__(self):
        return iter(_build_block_types_map())

    def __contains__(self, key):
        return key in _build_block_types_map()


BLOCK_TYPES = _BlockTypesView()
