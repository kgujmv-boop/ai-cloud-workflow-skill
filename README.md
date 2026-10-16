# Orchestrate AI Cloud Work

A reusable workflow for AI assistants and tools such as dot, bot, muse, Codex, and Claude. Allocate CPU, cloud GPUs, storage, and authorized AI tools according to the task; save progress and avoid duplicate work and wasted compute.

The package uses a standard SKILL.md layout. Use it with whatever browser, file, code-execution, or connector capabilities the current environment provides. A dedicated cloud computer is not required, and browser control is not assumed to exist in every client.

## Capabilities

- Research current free-first options for the user's scenario, compare tradeoffs, and let the user choose where needed.
- On first use, check task-relevant connections and proactively request missing sign-ins.
- Inspect actual resources, quotas, and running jobs before allocation.
- Divide independent inputs across workers without submitting the same batch twice.
- Recover from disconnections using task records, hashes, and checkpoints.
- Turn reference study into documented experiments and reusable lessons.
- Verify final outputs and recoverable backups before authorized cleanup.
- Apply optional video and narration guidance when relevant.

## Load and use

Give the entire folder to an assistant through its supported skill-loading or file-reading interface. Preserve relative paths. An assistant must be able to read the instructions, have suitable tools for each action, and hold the required authorization. With only some capabilities available, complete supported work and identify the remaining blockers. Clients differ: automatic installation, API compatibility, and access to services are not guaranteed.

Example request:

> Use orchestrate-ai-cloud-work. Help me prepare for my project: ask only for missing goals and constraints, recommend the resources I actually need, check existing connections, and guide me through any necessary login.

Clients supporting named skill invocation can use `$orchestrate-ai-cloud-work`. Other agents can read SKILL.md and the relevant reference files directly. `agents/openai.yaml` is optional Codex metadata and may be ignored by other clients.

See [usage](references/usage.md). Copy the configuration and task templates under assets, fill real values, and run:

```sh
python scripts/validate_manifest.py /path/to/task-manifest.json
python -m unittest discover -s tests -v
```

The checker uses Python's standard library and performs offline checks only. It does not contact providers, verify actual quota or file content, submit jobs, or authorize actions.

## Layout

- SKILL.md: entry point and conditional reference routing
- references/: scheduling, AI collaboration, learning, quality, video/narration, usage
- assets/: blank project/task templates and an optional UI icon
- scripts/: read-only manifest checker
- tests/: reproducible CPU-only tests
- agents/: optional client metadata

## Limits

This package supplies no GPU, storage, subscription, or persistent login. Free allocation can change. Multiple GPUs do not automatically pool VRAM. Existing paid storage and subscriptions must be accounted for separately. Uploading, payment, account changes, and deletion remain subject to effective authorization.

Public reference projects are linked in [AI collaboration and learning](references/ai-and-learning.md); their source code and private media are not bundled. No open-source license has been selected. Public visibility alone does not grant additional usage rights.

## First-use connections

On first active use, the assistant learns the task and missing constraints, proposes a suitable setup, then checks which services are actually needed and whether they are already connected. It asks you to sign in only where access is missing, explains why, then verifies access before continuing. Installing this skill does not independently launch a background process. See [connection onboarding](references/connection-onboarding.md).
