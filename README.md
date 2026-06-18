# Proof Surface Report

> Render proof-surface packets and receipts as reviewer-facing Markdown; rejects authority-shaped language on output.

[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![version](https://img.shields.io/badge/version-0.1.0-informational.svg)
[![CI](https://github.com/HarperZ9/proof-surface-report/actions/workflows/ci.yml/badge.svg)](https://github.com/HarperZ9/proof-surface-report/actions/workflows/ci.yml)
[![part of: AI-accountability toolkit](https://img.shields.io/badge/part_of-AI--accountability_toolkit-7a5cff.svg)](https://harperz9.github.io)

`proof-surface-report` is a small Python adapter. Its only runtime dependency
is the shared [`proof-surface`](https://github.com/HarperZ9/proof-surface)
contract package, which it uses to validate artifacts; beyond that it relies
solely on the Python standard library. It validates two neutral artifact shapes
and renders reviewer-facing Markdown:

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

The package uses a `src/` layout. Its single runtime dependency is the
`proof-surface` contract package, which is distributed from git:

```bash
pip install git+https://github.com/HarperZ9/proof-surface.git
pip install .
```

This installs a `proof-surface-report` console script.

For local development without installing, put the package on the path with
`PYTHONPATH=src` (the `proof-surface` package must still be importable).

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

For a step-by-step walkthrough with worked examples and expected output, see
[USAGE.md](USAGE.md).

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
project. It shares no code with that project's reporting core; its only runtime
dependency is the shared `proof-surface` contract package, and otherwise it uses
only the Python standard library.

## License

[MIT](LICENSE)

---
**Zain Dana Harper** — small tools with explicit edges.
[Portfolio](https://harperz9.github.io) · [HarperZ9](https://github.com/HarperZ9)
<sub>Built with Claude Code; reviewed, tested, and owned by me.</sub>
