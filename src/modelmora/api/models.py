"""The `listModels` path (T042): name, version, kind, reads-images and licence per
model, plus the default for each slot (FR-024).

Only servable models appear here -- an incomplete or filter-undisclosable record is
never listed to a caller, the same as it is never resolved (`api/validate.py`,
`registry/registry.py`). The full licence trail, retired models included, is a team
matter and reachable only through `modelmora model list --all` (SC-006), never over
the loopback API.
"""

from __future__ import annotations

from modelmora.api.state import AppState
from modelmora.messages import ModelsList, ServableDefaults, ServableModel


def build_models_list(state: AppState) -> ModelsList:
    models = [
        ServableModel(
            name=m.name,
            version=m.version,
            kind=m.kind,
            readsImages=m.reads_images,
            license=m.license,
        )
        for m in state.registry.list_servable()
    ]
    defaults = state.registry.defaults()
    return ModelsList(
        models=models,
        defaults=ServableDefaults(
            text=defaults["text"].name if defaults["text"] else None,
            textWithImages=(
                defaults["text_with_images"].name if defaults["text_with_images"] else None
            ),
            image=defaults["image"].name if defaults["image"] else None,
        ),
    )
