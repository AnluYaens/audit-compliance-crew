# Evaluation Datasets

This directory is the starting point for deterministic evaluation datasets and future model-comparison workflows.

Initial eval assets are intentionally schema-first:

- inputs live in `tests/fixtures/`
- stable expected artifacts live in `evals/golden_outputs/`
- unit tests validate local JSON and metadata without real LLM calls

Future real-model evals should reuse these fixtures, normalize unstable fields, and record model/version metadata outside ordinary unit tests.
