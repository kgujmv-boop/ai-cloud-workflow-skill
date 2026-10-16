# Usage

This workflow targets AI assistants and tools such as dot, bot, muse, Codex, and Claude when configured with relevant capabilities. Inspect actual browser, file, code-execution, and connector access; do not assume every client supports them all. A dedicated cloud computer is not required. Load the folder using the client's supported skill or file interface. Clients without native skills can read SKILL.md and the relevant references manually. Do not assume identical tools, APIs, or automatic installation.

Example requests:

“Use orchestrate-ai-cloud-work. Inspect existing jobs and free compute, divide this narration task among available GPUs, use CPU for captions and assembly, then verify the deliverable.”

“Recover yesterday's project. Locate validated completed shards before rerunning anything.”

“Study these reference videos, document exactly what you inspected, apply one technique to the next version, and evaluate it when I provide results.”

Clients supporting named invocation may use `$orchestrate-ai-cloud-work`. The optional agents/openai.yaml file supplies Codex UI metadata; other clients can ignore it.

## Configure a project

Copy assets/project-config.json into the project and fill the project path, output contract, and authorized services. Empty values mean unconfigured. Authorization evidence records an existing approval; setting a field cannot create permission. Never store passwords, cookies, or tokens.

Copy assets/task-manifest.json and fill real hashes, dependencies, and shards. Run:

```sh
python scripts/validate_manifest.py /path/to/task-manifest.json
```

An OK result does not establish current resources, effective authorization, or platform job state. Check those before a single dispatcher submits. Template nulls are intentionally unfilled inputs, not runnable job values.

Run tests without cloud access:

```sh
python -m unittest discover -s tests -v
```

This workflow supplies no hardware or subscription. Measure current free allocation; separate existing paid storage/subscriptions from free compute. Recovery relies on saved records and backups, not permanent connectivity or infallible memory.

## First invocation

After loading the skill, give the assistant a task, or ask it to help plan your setup. It should infer known goals and ask only for missing outcome, budget, or resource constraints; then recommend the smallest suitable setup and inspect task-relevant connections and proactively request missing sign-ins without waiting for you to list every website. It must skip working connections and respect declined or postponed setup. If no task is known, ask what work to prepare for before requesting accounts. The skill itself is not a background service. See [connection onboarding](connection-onboarding.md).

## Compare options for a scenario

Ask: “I want to analyze a dataset using free resources. Research suitable options, explain the limits and privacy tradeoffs, and let me choose before setting up new services.”

The agent should research current official sources, return one or more genuinely viable free-first routes, and optionally one or two paid alternatives when consistent with your budget. If you explicitly require free-only, paid options stay out unless you ask for them. Existing explicit provider choices are respected. See [option discovery](option-discovery.md).
