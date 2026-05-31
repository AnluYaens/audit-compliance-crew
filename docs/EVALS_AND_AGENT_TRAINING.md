# Evals and Agent Training

The project should make agents less unpredictable over time through architecture, prompts, schemas, evals, and tests.

We are not fine-tuning first.

Fine-tuning should be considered only after the project has enough validated examples, stable task definitions, and evidence that prompt/schema/eval improvements are not sufficient.

## Reliability Ladder

Improve reliability in this order:

1. strict architecture boundaries
2. strict prompts
3. structured outputs
4. Pydantic validation
5. few-shot examples
6. deterministic fake model tests
7. evaluation datasets
8. golden outputs
9. manual feedback loops
10. real LLM evals
11. fine-tuning only if justified later

## Strict Prompts

Agent prompts should specify:

- role
- allowed actions
- forbidden actions
- required output schema
- citation requirements
- confidence handling
- missing evidence behavior
- contradiction handling
- manual review routing expectations

Prompts should repeat that agents may not decide `CONTINUE`, `MANUAL_REVIEW`, or `REJECT`.

## Structured Outputs

Every pipeline-affecting agent should return structured data, not open-ended prose.

Structured outputs should include:

- extracted facts
- source references
- confidence scores or confidence labels
- missing evidence
- contradictions
- uncertainty notes
- human review requirement

Narrative text belongs in memo drafts or auditor assistance, not in deterministic inputs.

## Pydantic Validation

Pydantic schemas are the gate between agent output and deterministic services.

If an agent response does not validate:

- reject the output as pipeline evidence
- record the validation problem
- route the relevant workflow to `MANUAL_REVIEW`

## Few-Shot Examples

Few-shot examples should cover:

- clean evidence
- missing evidence
- contradictory evidence
- low-confidence extraction
- unsupported claim rejection
- valid memo enhancement
- invalid decision-making attempt by an agent

Examples should teach conservative behavior and evidence citation.

## Evaluation Datasets

Evaluation datasets should include stable fixtures for:

- source discovery
- source scoring
- evidence extraction
- financial statement processing
- memo enhancement
- auditor assistant answers
- quality review findings

Datasets should pair inputs with expected structured outputs and manual review expectations.

## Golden Outputs

Golden outputs should define acceptable outputs for representative cases.

They should be used for:

- regression testing
- prompt comparisons
- model version comparisons
- reviewing agent changes

Golden outputs should avoid unstable values such as timestamps unless normalized.

## Manual Feedback Loops

Auditor feedback should be captured in structured form:

- what was wrong
- expected correction
- evidence used
- whether the issue was prompt-related, schema-related, source-related, or model-related
- whether a new test fixture is needed

Feedback should usually produce a prompt change, schema change, fixture, or test before any training discussion.

## Fake Model Tests

Use fake models first to test guardrails deterministically.

Fake model tests should simulate:

- valid schema output
- malformed output
- unsupported facts
- low confidence
- contradictions
- missing citations
- attempted final decision assignment

This proves the application protects itself even when a model behaves poorly.

## Real LLM Evals Later

Real LLM evals should come after fake model tests and fixture design.

They should track:

- schema validity rate
- citation quality
- unsupported claim rate
- manual review trigger accuracy
- contradiction detection
- prompt regression
- latency and cost when relevant

Real model calls should not be required for ordinary unit tests.

## Fine-Tuning Later

Fine-tuning may be justified only if:

- the task is stable
- there is a high-quality dataset
- prompt and schema improvements are not enough
- evals show a measurable gap
- the tuned behavior can still be validated by schemas and tests

Fine-tuning must not be used to bypass deterministic rules.
