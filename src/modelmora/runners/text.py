"""Real text generation via `transformers` (R-2).

Only exercised on the Studio machine with the `gpu` extra installed; CI and the
component's own test suite run against the stand-ins in `runners/standin.py` instead
(FR-033, FR-034). Imports of `torch` and `transformers` are deferred into the methods
that need them so importing this module never requires the GPU extra.
"""

from __future__ import annotations

from typing import Any

from modelmora.runners.base import GeneratedText, Runner


def _build_prompt(instructions: str, conversation: list[dict[str, str]] | None) -> str:
    lines = [f"{turn['speaker']}: {turn['text']}" for turn in conversation or []]
    lines.append(f"caller: {instructions}")
    lines.append("model:")
    return "\n".join(lines)


class TextRunner(Runner):
    """A `transformers` causal language model, loaded and unloaded on demand."""

    kind = "text"

    def __init__(
        self,
        *,
        name: str,
        version: str,
        model_path: str,
        reads_images: bool = False,
        device: str = "cuda",
    ) -> None:
        self.name = name
        self.version = version
        self.reads_images = reads_images
        self._model_path = model_path
        self._device = device
        self._model: Any = None
        self._tokenizer: Any = None
        self._footprint_bytes = 0

    def declared_footprint_bytes(self) -> int:
        return self._footprint_bytes

    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self.is_loaded():
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self._model_path)
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_path, torch_dtype=torch.float16
        ).to(self._device)
        self._model.eval()
        self._footprint_bytes = sum(
            parameter.numel() * parameter.element_size() for parameter in self._model.parameters()
        )

    def unload(self) -> None:
        if not self.is_loaded():
            return
        self._model = None
        self._tokenizer = None
        self._footprint_bytes = 0
        import gc

        import torch

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def generate_text(
        self,
        *,
        instructions: str,
        conversation: list[dict[str, str]] | None = None,
        images: list[bytes] | None = None,
        seed: int | None = None,
        max_length: int | None = None,
        temperature: float | None = None,
    ) -> GeneratedText:
        if images and not self.reads_images:
            raise ValueError(f"{self.name} cannot read images")
        if not self.is_loaded():
            raise RuntimeError(f"{self.name} v{self.version} is not loaded")

        import torch

        if seed is not None:
            torch.manual_seed(seed)

        prompt = _build_prompt(instructions, conversation)
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_length or 512,
                do_sample=bool(temperature),
                temperature=temperature or 1.0,
            )
        generated_ids = output_ids[0][inputs["input_ids"].shape[1] :]
        text = self._tokenizer.decode(generated_ids, skip_special_tokens=True)

        settings_used: dict[str, Any] = {
            "seed": seed,
            "maxLength": max_length,
            "temperature": temperature,
        }
        return GeneratedText(text=text, settings_used=settings_used, filter_note=None)
