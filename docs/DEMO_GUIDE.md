# Demo Guide

This guide explains how to run and present the local Audit Compliance Crew MVP.
The demo uses synthetic data and deterministic code only.

## Prerequisites

- a POSIX-style shell from the repository root
- Python 3 available through `.venv/bin/python`
- Pydantic 2 installed from `requirements.txt`
- pytest available in the virtual environment for the validation command

The runtime demo needs no environment variables, credentials, network access,
model provider, virtual machine, Docker runtime, or Azure resource. The exact
commands below assume the local virtual environment is named `.venv`.

If the prepared environment is missing the runtime dependency, install it with:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

## Run the Clean Demo

```bash
.venv/bin/python -m app.run_two_agent_demo
```

The clean scenario should report these high-level results:

```text
Scenario: clean
Normalization: COMPLETE
Sandbox verification: success
Safe Hint Bridge: complete
Public research: complete
Evidence reconciliation: aligned
Human review required: no
```

The CLI adds item counts in parentheses. Those counts show what each stage
processed; they are not audit conclusions.

## Run the Review Demo

```bash
.venv/bin/python -m app.run_two_agent_demo --scenario review
```

The review scenario should report these high-level results:

```text
Scenario: review
Normalization: COMPLETE
Sandbox verification: review_required
Safe Hint Bridge: no_approved_hints
Public research: review_required
Evidence reconciliation: contradictory_evidence
Human review required: yes
```

Here, `no_approved_hints` means the bridge ran successfully but released no
hints because the sandbox result already required review.

## What the Results Mean

| Scenario | Evidence interpretation                                                                      | Compliance interpretation                                       |
| -------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `clean`  | The deterministic mock evidence aligns and no reconciliation issue is present.               | This is not a `CONTINUE` decision.                              |
| `review` | A contradiction is preserved, no hints enter the public lane, and human review is signalled. | This is not independently assigned `MANUAL_REVIEW` or `REJECT`. |

The demo stops at evidence reconciliation. Separate deterministic services in
the wider project own final compliance outcomes.

Additional supported scenarios are:

- `sandbox-contradiction`
- `sandbox-missing-evidence`
- `public-weak`
- `public-stale`
- `public-error`

Use the same command with a different `--scenario` value, for example:

```bash
.venv/bin/python -m app.run_two_agent_demo --scenario public-stale
```

## Short Presenter Script

> Audit Compliance Crew demonstrates a deterministic-first evidence workflow.
> The rule is “Python decides; agents assist.” The input is synthetic. A local
> normalizer structures it, a deterministic mock verifier inspects the internal
> artifact, and the Safe Hint Bridge removes local provenance before anything
> enters the mock public-research lane. Python then reconciles the two evidence
> views. The clean run aligns; the review run preserves a contradiction and
> signals human review. These are evidence-quality results, not autonomous audit
> or compliance decisions. There is no internet search, LLM, VM isolation, or
> Azure deployment in this MVP.

A concise live presentation is:

1. Run the clean command and point out `aligned` and
   `Human review required: no`.
2. Run the review command and point out `no_approved_hints`,
   `contradictory_evidence`, and `Human review required: yes`.
3. Emphasize that Python produced both status paths deterministically and that
   neither run assigned a final compliance outcome.

## Stage-by-Stage Explanation

1. **Synthetic input** — By default, the CLI creates a temporary one-row CSV.
   An optional synthetic CSV or JSON path may be supplied instead.
2. **Normalization** — Python parses supported CSV/JSON content into strict
   Pydantic models, retaining local source metadata, provenance, warnings,
   confidence, and quality status.
3. **Mock sandbox verification** — A deterministic local wrapper emits a
   schema-valid verifier result for the selected scenario. It simulates the
   verifier contract; it is not a real sandbox or isolated VM.
4. **Safe Hint Bridge** — Deterministic Python accepts hints only from a
   successful, non-review verifier result and enforces type, sensitivity,
   confidence, review, and unsafe-marker rules. Approved copies have
   `provenance=None`.
5. **Mock public research** — A deterministic fixed provider returns
   schema-valid public-style sources and evidence. It does not browse the
   internet.
6. **Evidence reconciliation** — Python compares internal findings with public
   evidence and records alignment, missing evidence, contradictions, weak or
   stale support, and source errors.
7. **CLI summary** — The command prints stage statuses and counts without raw
   confidential values, local provenance, or a final compliance decision.

## Confidentiality Boundary

```text
Local/internal lane
  synthetic raw values + local provenance
          |
          v
Deterministic Safe Hint Bridge
  safety checks + provenance removal
          |
          v
Mock public lane
  approved public-safe hint text only
```

The local lane may hold confidential-classified synthetic values. The public
lane receives only bridge-approved hint copies. Raw values, local filenames,
source identifiers, and provenance remain on the local side. Review-required
sandbox results produce an empty approved-hint list.

This boundary is demonstrated through deterministic code and tests. It is not a
claim of production isolation, data-loss prevention, or sandbox hardening.

## What Is Mocked and What Is Deterministic

Every current stage executes deterministically. “Mocked” identifies stages that
simulate an external or agent capability.

| Stage                   | Deterministic | Mocked or limited                                 |
| ----------------------- | ------------- | ------------------------------------------------- |
| CSV/JSON normalization  | Yes           | Limited to supported synthetic CSV/JSON artifacts |
| Offline verifier        | Yes           | Mock scenario provider; no VM isolation or model  |
| Safe Hint Bridge        | Yes           | Demo policy, not a production DLP system          |
| Public research         | Yes           | Fixed provider; no browsing or network            |
| Evidence reconciliation | Yes           | MVP evidence comparison rules                     |
| CLI summary             | Yes           | Presentation only; no final decision              |

There is no LLM runtime, real agent framework, real public search, OCR, PDF or
Excel parser, Azure deployment, or real client data.

## Troubleshooting

### `.venv/bin/python` is missing

Create or obtain the expected local virtual environment, then install the
runtime dependency from `requirements.txt`. Keep the environment outside
version control.

### `ModuleNotFoundError: pydantic`

Run:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

### `No module named pytest`

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

### `No module named app`

Run the command from the repository root, not from inside `app/` or `docs/`.

### A custom artifact is rejected or recommends review

Use synthetic UTF-8 CSV or JSON only. PDF, Excel, OCR, and arbitrary text parsing
are outside the MVP scope. Malformed or incomplete supported input is expected
to fail closed to review.

### The review scenario has zero hints or zero public sources

That is expected. A review-required sandbox result is not allowed to pass hints
through the bridge, so the mock public lane reports missing support.

### No output file appears

That is expected for `app.run_two_agent_demo`. It prints a concise summary and
uses a temporary synthetic input; it does not generate tracked evidence or memo
files.
