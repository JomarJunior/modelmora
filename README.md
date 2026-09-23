# 🧠 ModelMora

The Studio's one place for open-weight model inference: text and image generation on one
GPU, served to Studio callers over a loopback API.

**🧠 ModelMora** is Studio-only. It is **not** part of the Studio Link and never speaks to
the Museum side — it exists so **🎭 SonaVida**, **💬 DescriDiva** and **🧐 CuraGusta** can ask
for a result without knowing how models are loaded or which one is on the GPU right now.

The contract itself — the OpenAPI 3.1 document and its JSON Schema messages — is **not**
kept here. It lives in the hub, as the single source of truth:

- [`specs/002-modelmora-inference/`](https://github.com/JomarJunior/miraveja-ecosystem/tree/main/specs/002-modelmora-inference)
- [`specs/002-modelmora-inference/contracts/modelmora-v1.yaml`](https://github.com/JomarJunior/miraveja-ecosystem/blob/main/specs/002-modelmora-inference/contracts/modelmora-v1.yaml)

## What it does

A caller submits a text or image request, naming at most a model, and gets an
acceptance at once with a position and an estimate. A single generation worker loads
and unloads open-weight models on the one GPU, so exactly one thing runs at a time and
no caller ever sees a memory error. A SQLite registry on the Studio holds every served
model's name, version, license and service dates, retired records included. A test mode
with tiny stand-in models lets every caller be built and tested with no GPU.

## Development

Requires this library checked out inside a `miraveja-ecosystem` hub checkout, at
`components/modelmora/`, so the contract can be read from
`../../specs/002-modelmora-inference/contracts/modelmora-v1.yaml` (override with
`MODELMORA_CONTRACT_PATH`).

```bash
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy
```

Real inference (`transformers`, `diffusers`, `torch`) is an optional extra, installed
only on the Studio machine itself:

```bash
uv sync --all-groups --extra gpu
```

## Usage

```bash
# Run the service with stand-in models, no GPU required:
uv run modelmora serve --test-mode --port 8431
```

See
[`specs/002-modelmora-inference/quickstart.md`](https://github.com/JomarJunior/miraveja-ecosystem/blob/main/specs/002-modelmora-inference/quickstart.md)
in the hub for the full walkthrough. `docs/usage.md` follows once the registry and CLI
land (usage docs for a caller and a team member are tracked as later tasks).

## License

Apache-2.0. See [`LICENSE`](./LICENSE).
