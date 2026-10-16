# Task-Scoped Connection Onboarding

## Trigger and inputs

Run this check on the first active invocation after deployment, when a new task requires another service, or when a previously working connection actually fails. Skill installation does not execute code or schedule background monitoring. If the task is unknown, first ask what work the user wants to prepare for; do not request a blanket login to all services.

Inputs: current task and authorization, available tools/connectors, browser/environment state, existing connection evidence, and any pending or declined setup requests.

## Personalize before requesting access

Use known context first. Ask a compact question for only missing decisions: the task or outcome, deliverable, budget/free-only constraint, and resources the user already has. Do not interrogate the user about details that do not change the plan. If the task is already clear, proceed without repeating onboarding questions.

For scenario advice or a missing workable route, follow [option discovery](option-discovery.md) before requesting new connections. Recommend a task-specific setup and explain why each component is needed, what minimum access is required, which decisions belong to the user, and what can be done without it. A paid option is a recommendation, not permission to buy it. Prefer existing suitable resources and no new connection when possible.

Examples:
- Literature summary or document editing: use available public sources and CPU document tools. Ask for a cloud-drive connection only if the requested source or delivery requires it. No automatic GPU or external AI.
- Coding or data analysis: use the specified repository/environment and CPU initially; request only the needed repository/data access. Escalate compute after measuring workload or finding a concrete model requirement.
- GPU model inference: inspect model memory requirements and existing jobs; recommend an available authorized GPU provider, then request login if missing. Do not request every provider at once.
- Media production: choose CPU, GPU inference, storage, and other AI independently according to actual needs; a video project is not an automatic reason to use them all.

## Procedure

1. Map each blocked task step to the minimum service capability. Distinguish reading a file, writing a result, running GPU code, and asking another AI. Do not require a provider solely because it appears in an example.
2. Probe an eligible connected tool with a harmless task-related read. Use the cloud browser when needed and identify whose browser it is. A browser session, connector authorization, GPU allocation, storage entitlement, and API subscription are separate facts.
3. If the probe works, record its time and capability and proceed; do not ask the user to sign in again. If it fails, distinguish expired login, missing permission, denied action, quota exhaustion, service failure, and unknown cause. Login does not repair an exhausted GPU quota.
4. For genuinely missing access, proactively ask for the smallest supported next step. Explain the service, task purpose, requested access, and where the user should act. Example: “To run the narration model on free GPU compute, please sign in to Kaggle in my cloud browser. I only need your private notebook for this task.” Name the actual service and scope rather than requesting general access.
5. Open the verified official entry point or supported secure handoff. Let the user enter passwords through the service or secure login flow; never ask for passwords, cookies, tokens, or recovery codes in chat. Do not create persistent credentials, grant OAuth scopes, switch accounts, accept unexpected permissions, or purchase a plan without the required authorization. Follow the host's current approval and login rules.
6. After the user reports completion, perform a read-only check of the selected account and exact needed capability. Confirm account identity privately without storing personal identifiers in public templates. Do not assume login success from a screenshot, the user's message alone, or a loaded landing page. Do not launch a GPU job merely to prove login; allocation tests belong only to an authorized compute check or task.
7. Resume the blocked step only after its prerequisites are verified. Keep independent authorized CPU work moving meanwhile.

## Provider examples

Use only entries needed for the current task; verify the current page and official domain before sending the user through login:
- Kaggle private notebooks / GPU work: https://www.kaggle.com/
- Colab notebooks / GPU work: https://colab.research.google.com/
- Google Drive project storage: https://drive.google.com/
- Gemini web-based AI assistance: https://gemini.google.com/

These are entry points, not guarantees of a particular login flow, model, quota, subscription, or entitlement. Prefer the user's already-authorized suitable service rather than requiring these exact providers.

## Outcomes and stopping conditions

Record service, purpose, observed time, state, and next step; never record credentials. States: ready, awaiting_user, declined, unavailable, unknown. A connection can be ready for reads but not for uploads or GPU execution; record the capability explicitly.

If setup is declined or postponed, do not repeatedly ask or choose an unauthorized account. Offer a suitable signed-out/local alternative, continue independent work, and retain the blocked step. If a request is already pending, do not duplicate it. If the cause is unknown, report that uncertainty rather than inventing a login problem. Respect tool denials instead of using another route to bypass them.

Do not promise permanent login. Expiry or environment reset may require reauthentication. Recheck when needed, not through an unrequested recurring monitor.
