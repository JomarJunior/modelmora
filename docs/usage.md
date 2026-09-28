# Using **🧠 ModelMora**

Two audiences: a Studio component that calls the loopback API (**🎭 SonaVida**,
**💬 DescriDiva**, **🧐 CuraGusta**), and a team member who keeps the registry current
with `modelmora model ...`. The contract itself is
[`specs/002-modelmora-inference/contracts/modelmora-v1.yaml`](https://github.com/JomarJunior/miraveja-ecosystem/blob/main/specs/002-modelmora-inference/contracts/modelmora-v1.yaml)
in the hub; this page is the walkthrough, not the source of truth.

## For a Studio component: submit, poll, withdraw, collect

Every request carries a bearer token that names the caller (R-9) -- an ownership
marker, not a security boundary; loopback is that boundary (FR-027). A caller never
loads, places or manages a model (FR-005): it names at most a model, or none at all
for the default of its kind.

### Ask for text

```bash
curl -s http://127.0.0.1:8431/modelmora/v1/requests \
  -H "Authorization: Bearer $MODELMORA_CALLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "text",
    "instructions": "Write a short artist statement for this piece."
  }'
```

Returns `202` at once with `requestId`, `position`, `estimatedWaitSeconds` and the
`model` that will serve it (FR-010). Name a model explicitly with
`"model": {"name": "...", "version": "..."}`; an unknown name is refused
`unknown_model`, never silently swapped for another (FR-004, FR-007). Include
`"images": [{"mediaType": "image/png", "base64": "..."}]` to ask a question about up to
8 images; **🧠 ModelMora** picks the `text_with_images` default when no model is named,
and refuses `invalid_request` if the chosen or default model cannot read them (FR-003).

### Ask for an image

```bash
curl -s http://127.0.0.1:8431/modelmora/v1/requests \
  -H "Authorization: Bearer $MODELMORA_CALLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "image",
    "description": "A quiet museum gallery at dawn, soft light, no figures.",
    "size": {"width": 512, "height": 512},
    "settings": {"seed": 7, "steps": 30}
  }'
```

A size or setting the chosen model cannot produce is refused before anything is
queued, naming the problem (US2 acceptance scenario 3). Sharing the one GPU with other
work is never the caller's problem: **🧠 ModelMora** evicts what it must to make room,
and the caller sees only a longer wait, never a memory error (FR-009).

### Check on a request

```bash
curl -s "http://127.0.0.1:8431/modelmora/v1/requests/$REQUEST_ID?waitSeconds=30" \
  -H "Authorization: Bearer $MODELMORA_CALLER_TOKEN"
```

`waitSeconds` (0-30) is a long poll: the call holds open until the request reaches a
terminal state (`done`, `failed`, `withdrawn`, `stopped_before_completion`) or the
timeout passes, whichever comes first. A `waiting` request's answer carries its
`position` and an updated, honestly-measured estimate (FR-012, FR-018). A caller sees
only its own requests; asking about someone else's id answers as if it does not exist
(FR-017).

### Withdraw a request

```bash
curl -s -X DELETE "http://127.0.0.1:8431/modelmora/v1/requests/$REQUEST_ID" \
  -H "Authorization: Bearer $MODELMORA_CALLER_TOKEN"
```

Only a request that has not started can be withdrawn; one already running finishes and
is answered normally (FR-013).

### Collect a finished image

```bash
curl -s "http://127.0.0.1:8431/modelmora/v1/requests/$REQUEST_ID/image" \
  -H "Authorization: Bearer $MODELMORA_CALLER_TOKEN" \
  -o result.png
```

Available until `heldUntil` on the request's `result` (default one hour after it
finished), then discarded along with everything else about the request (FR-030,
FR-032).

### Ask what is available

```bash
curl -s http://127.0.0.1:8431/modelmora/v1/availability \
  -H "Authorization: Bearer $MODELMORA_CALLER_TOKEN"
```

Reports `state` (`starting`, `running` or `stopping`), the current length of the line,
and how many models are servable per kind -- nothing about another caller's requests
(FR-017, FR-029). A submission while `starting` or `stopping` is refused with that
reason and a retry time, never accepted and then abandoned.

## For a team member: keep the registry honest

`modelmora model ...` changes the registry without touching code (FR-025); it opens
the same SQLite file `modelmora serve` reads from (`MODELMORA_DB_PATH`, default
`.modelmora/registry.sqlite3`), so a model added here is what `serve` and `listModels`
see next.

### Add a model

**🧠 ModelMora** never downloads a model itself: every model it serves is already on
the Studio's own disk, in whatever collection the team keeps there. `--local-path`
(defaults to `--weights-path`) is where `serve` builds a real runner from
(`runners/build.py`); `--companion ROLE=PATH`, repeatable, names a file a runner needs
beside the main weights (a vision projector, a VAE).

A `.gguf` text model, read through a managed `llama-server` (`runners/llamacpp.py`),
with a vision projector so it can also answer questions about images:

```bash
modelmora model add \
  --name example-text-model --version Q4_K_M --kind text --reads-images \
  --source "<where the model came from: its page or repository>" \
  --weights-path /path/to/models/example-text-model/model.gguf \
  --companion mmproj=/path/to/models/example-text-model/mmproj.gguf \
  --license Apache-2.0 \
  --license-source "<where the licence terms were read>" \
  --confirm-license
```

A single-file SDXL checkpoint (`from_single_file`, `runners/image.py`), with the
pipeline config it loads with as its `config` companion (see below); `local-path`
defaults to `weights-path`:

```bash
modelmora model add \
  --name example-image-model --version 1.0 --kind image \
  --source "<where the model came from: its page or repository>" \
  --weights-path /path/to/models/example-image-model.safetensors \
  --companion config=/path/to/pipeline-config \
  --license "<licence name>" \
  --license-source "<where the licence terms were read, and any extra permissions noted there>" \
  --confirm-license
```

`--weights-path` is hashed on the spot (streamed, so a multi-gigabyte checkpoint is
never held whole in memory); that digest is what every later load is checked against,
and a mismatch refuses to serve and tells the team rather than silently running
something else (FR-022). `--filter-disclosure disclosed|undisclosable` records a
model with a built-in content filter -- `undisclosable` is recorded but never made
servable (spec Edge Cases, FR-008).

`--confirm-license` is the moment a team member states, as themselves, that the
license is open-weight and allows the museum's use (FR-021, Principle V). Without it
the model is recorded but refused whenever a caller asks for it; nothing is served on
an incomplete record.

The `.gguf` runner needs a `llama-server` binary and its CUDA runtime libraries
somewhere on the Studio -- neither ships with this repository or any pip package.
Point `MODELMORA_LLAMA_SERVER_BIN` at the binary and `MODELMORA_LLAMA_CUDART_LIB_DIR`
at the directory holding its `libcudart`/`libcublas`; the llama.cpp project's own
prebuilt release (its `ubuntu-cuda-*-x64` and matching `cudart-*` assets) is the
fastest way to get both without compiling anything. Each `LlamaCppTextRunner` picks its own free loopback
port unless `MODELMORA_LLAMA_SERVER_PORT` pins one.

A single-file SDXL checkpoint needs a pipeline config and tokenizer from somewhere,
too -- `diffusers` fetches them from the Hub at load time otherwise. Record a local
directory holding them (for example a copy of an already-cached base SDXL pipeline
snapshot's config and tokenizer files, no weights) as the model's `config` companion, at `model add` time (`--companion config=<dir>`) or later:

```bash
modelmora model add-companion --name example-image-model --version 1.0 \
  --companion config=/path/to/pipeline-config
```

It is digested like any other companion, checked before the first load, and read by
`serve` from the registry alone, so no `HF_HOME` or other environment variable is
needed (FR-028). `serve` also forces `HF_HUB_OFFLINE=1` and `local_files_only=True`
regardless, so a checkpoint recorded without one fails its load loudly -- reported
`model_unavailable`, with a WARNING line for the team -- rather than reaching the
network. A companion role already recorded is never replaced: a changed model is a
new version. (`MODELMORA_SDXL_CONFIG_PATH` remains a fallback for a record without a
`config` companion.)

### List, retire, verify, and change a default

```bash
modelmora model list                 # servable models and the default per slot
modelmora model list --all           # every record ever added, retired included, with service dates (SC-006)
modelmora model retire --name example-image-model --version 1.0
modelmora model verify --name example-image-model --version 1.0 --weights-path /path/to/models/example-image-model.safetensors
modelmora model set-default --slot image --name example-image-model --version 1.0
```

Retiring keeps the record and its license, with the dates it was in service, so a
result produced years ago still traces to the license that covered it (FR-023,
SC-005). `verify` is the same digest check `serve` runs before a first load, runnable
by hand; a mismatch exits non-zero and logs one `WARNING` line naming the model,
version and expected digest -- the one channel "telling the team" ever means here
(plan.md).

## Why model names never reach a visitor

A model's name and version are Studio internals, useful to a team member deciding what
to run and to a reviewer tracing a license, and useless -- worse, immersion-breaking --
to a museum visitor (Principle IV: no system internals on a visitor-facing surface).
Carrying that name forward into anything a person sees is the calling component's own
duty, not **🧠 ModelMora**'s (spec Assumptions): **🎭 SonaVida** renders "away from the
studio," never "waiting on `example-text-model` v1 to load."
