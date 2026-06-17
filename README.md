# proof-surface-report

Render proof-surface JSON artifacts as a concise Markdown reviewer handoff.

`proof-surface-report` is a small, self-contained, **stdlib-only** Python
adapter. It validates two neutral artifact shapes and renders reviewer-facing
Markdown:

- a **proof-surface packet** (`proof_surface_version: "0.1"`): a surface, a
  status, factual claims with evidence, tool checks, and action items.
- an **EMET witness receipt**: a verdict plus witness facts (implementation,
  spec version, self-hash, check), subjects with digests, and run evidence.

The output is an **evidence handoff**, not a certification, trust verdict,
safety decision, or compliance finding. To keep it that way, the renderer
rejects authority-shaped wording (for example "certified", "approved",
"safe to release", "compliant") anywhere it appears in artifact text or in the
report title, and it rejects unknown fields and ungoverned receipt verdicts.

It is part of the EMET suite. EMET is the umbrella brand; this leaf is named
descriptively for what it does.

## Install

The package uses a `src/` layout and has no runtime dependencies.

```bash
pip install .
```

This installs a `proof-surface-report` console script.

For local development without installing, put the package on the path with
`PYTHONPATH=src`.

## Usage

As a console script:

```bash
proof-surface-report examples/public-surface.packet.json examples/provenance.packet.json examples/emet.receipt.json
```

As a module (development checkout):

```bash
PYTHONPATH=src python -m proof_surface_report examples/public-surface.packet.json examples/emet.receipt.json
```

Override the report title (still language-checked):

```bash
proof-surface-report --title "Release Surface Handoff" examples/public-surface.packet.json
```

The report is written to stdout. On validation or IO error the tool prints an
`error:` line to stderr and exits non-zero.

## Examples

The `examples/` directory contains synthetic, public artifacts:

- `public-surface.packet.json` — a public-release surface packet.
- `provenance.packet.json` — a model-provenance packet.
- `emet.receipt.json` — an EMET witness receipt.

Keep claims factual and evidence-backed. Do not phrase them as approval,
certification, compliance, or release safety; such phrasing is rejected before
rendering.

## Development

```bash
PYTHONPATH=src python -m pytest -q
```

## Provenance

This adapter was extracted as a standalone tool from an internal reporting
project. It is self-contained and shares no code with that project's reporting
core; it depends only on the Python standard library.

## License

[MIT](LICENSE)
