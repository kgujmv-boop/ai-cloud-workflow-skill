# Discover and Compare Resource Options

## Route

Scenario → requirements → current research → viable free-first options → tradeoff comparison → user selection where needed → minimum connection setup → authorized execution.

Run this when the user asks how to accomplish a scenario, needs a personalized setup, or a chosen route is unavailable. Do not force a menu when the user has already chosen a suitable workflow. A routine small task with an obvious low-risk authorized route does not require unnecessary shopping research.

## Requirements before search

Infer known goals and constraints; ask only for missing decisions that change the plan. Capture output/quality requirements, workload and memory needs, turnaround, data sensitivity, region/account constraints, already-owned services, and budget/free-only preference. Do not assume a video task or GPU dependency.

## Research live evidence

Search beyond example providers. Prefer current official pricing, quota, documentation, licensing, and availability pages. Record source URL and access date for every consequential comparison. Distinguish documented provider terms from actual account eligibility or runtime allocation; do not promise the latter without checking it.

Classify each offer accurately:
- Free tier: recurring no-charge allowance, with limits and possible feature restrictions.
- Trial or promotional credits: temporary or eligibility-dependent; record expiry, card requirements, renewal, and conversion terms when stated.
- Open-source software: software licensing is separate from hosting, hardware, storage, and operation costs.
- Existing owned resource: may add no new cost but was not necessarily free to obtain.

Compare task fit and expected output quality, resource/usage limits, setup effort, data privacy and retention, current availability, pricing units/currency, mandatory costs, trial expiry, and cancellation/renewal terms where relevant. Mark unknowns explicitly. Do not infer a fixed GPU quota, price, or reset date from old examples or search snippets. Check acceptable-use restrictions as part of fit, not only nominal hardware specifications.

## Present a short useful choice

Offer one or more viable free routes, not filler. Name a recommended route and explain the reason in task terms. If only one free option meets the requirements, say why. If none can be verified, say so; consider a smaller workload, CPU/local approach, waiting, or a permitted change in requirements without pretending these are equivalent.

When budget permits and comparison would help, optionally include one or two paid alternatives. Exclude them for an explicit free-only request unless the user asks to see them. Do not call a paid subscription or an expiring credit permanent free capacity. No specific provider is required by this skill.

For each option show: what it can do for this task; key limitation; effort/access required; privacy implications; known cost terms; dated official source; and what remains unverified. Avoid unsupported performance rankings. If a benchmark is needed, propose or run only an authorized small representative test.

## Choice and execution boundary

Ask the user to choose when alternatives materially differ in cost, privacy, service access, or output. A recommendation does not authorize signup, data upload, OAuth grants, subscription, or payment. Obtain required permission before consequential setup. If the user already chose a route, proceed within that scope; explain only material new blockers. For an obvious reversible low-risk route under an execution request, recommend the default and continue independent authorized work rather than forcing a redundant choice.

Once selected, follow [connection onboarding](connection-onboarding.md), verify access and capability, then use [scheduling](scheduling.md). Record the selection and evidence in the project so resumed work does not repeatedly re-open the same decision.

## Checks and examples

- Public-source literature PDF, free-only: consider existing browser/CPU document tools first. No GPU or new cloud account is implied.
- Model does not fit the available free hardware: do not combine unrelated GPU memory or invent another free allocation. Compare verified smaller/quantized models only if output requirements allow; otherwise report the gap.
- Budgeted inference comparison: verify current price units and expected workload before giving a cost estimate; do not buy because the user asked for options.
- User already selected a private notebook provider: use that route if viable, not a compulsory alternative-provider menu.
- Provider quota exhausted: distinguish waiting for uncertain capacity from a verified alternative. Do not switch accounts to bypass limits.

Public research is evidence gathering, not a promise of future availability. Recheck material terms before the user commits.
