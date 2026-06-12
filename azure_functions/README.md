# Azure Functions Boundary Preparation

This directory documents future Azure Function boundaries for the local-first
BDO Compliance Crew services.

The project is not using Azure Functions yet. These notes are preparation only:

- no Azure SDK dependencies
- no deployment files
- no credentials
- no cloud resources
- no business logic in this directory

## Boundary Principle

Future Azure Function activities should be thin adapters around deterministic
local services:

```text
trigger payload
-> validate request schema
-> call local service
-> validate response schema
-> return serialized response
```

Function wrappers must not make compliance decisions, mutate scoring policy, or
parse agent free-form output. They should only validate, call, serialize, and
surface errors in the service's existing fail-closed contract shape.

## Current Status

The local services remain the source of truth. The boundary documentation in
`function_boundaries.md` identifies the current request and response schemas
that future activities should use.

Local compatibility tests live in `tests/test_function_boundary_contracts.py`.
Those tests serialize payloads, validate outputs, and run without Azure
packages.

