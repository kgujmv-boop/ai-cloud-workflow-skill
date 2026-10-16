---
name: orchestrate-ai-cloud-work
description: Help AI assistants and tools such as dot, bot, muse, Codex, and Claude allocate CPU, cloud GPUs, storage, and authorized AI services on demand. Use for multi-resource jobs, duplicate prevention, checkpoint recovery, reference learning, and verified delivery, with optional video and narration workflows. 按需协调算力、云盘与 AI 工具，支持免费方案比较、登录引导、任务恢复和交付核验。
---

# Orchestrate AI Cloud Work

Complete the user's task using the resources actually available. Keep enough project evidence to resume safely after interruption. Use whichever browser, file, code-execution, or connector capabilities the current assistant actually has; owning a cloud computer is not required. This workflow grants no resources, credentials, or permissions. SKILL.md is the portable entry point; Codex metadata is optional.

## 中文说明

这是给具备相应工具与授权的 AI 助手使用的资源协作流程，可用于编程、资料研究、数据分析、媒体制作等任务。先了解目标、成果形式、预算与已有资源；需要选方案时，查证当前可用的免费方案并比较限制，再按用户选择检查连接、引导必要的登录。执行前核实资源和在跑任务，保存进度，避免重复运行；完成后检查成果和备份，再按有效授权清理。它不会提供硬件、代替授权或在安装后自行启动后台工作。

以下英文部分是完整执行说明。用户可用中文提出需求，助手按用户偏好回复。具体用法见 [中文使用指引](references/usage.md#中文使用指引)。

## Establish the contract

Read the current request, latest changes, output requirements, and effective authorization. Distinguish planning, production, resumption, quota inspection, and pause requests. A quota check does not authorize production. Valid standing permission may cover an action; do not ask again unnecessarily, and do not revive revoked permission.

Inspect available capabilities before planning execution. Do not assume every client includes browser control or code execution; with partial tools, perform only supported actions and identify the missing capability for remaining steps.

Create one project directory with inputs, code, outputs, checks, and recovery records. Do not embed credentials, private account identifiers, or unrelated conversations. Choose general mode by default; read [video and narration](references/video-and-voice.md) only for that work.

## Personalize the setup and connections

On the first active invocation after deployment, establish the user's goal, desired output, budget constraints, and already-owned resources from context; ask only what is missing. When the user asks how to support a scenario or needs alternatives, research current viable free-first options using [option discovery](references/option-discovery.md), compare tradeoffs, and obtain the necessary user choice before consequential setup. Respect an already chosen workflow; do not force a new menu. Then map required services and probe existing connections read-only. Do not assume video production, GPU use, or outside AI is needed. Proactively ask the user to complete only missing relevant sign-ins, explaining service, purpose, and required access. Follow [connection onboarding](references/connection-onboarding.md), verify the resulting account and capability, then resume. Installation alone does not run this check or start background work.

## Decide before dispatch

1. Inspect existing jobs and runtime ownership before connecting or changing anything. Record observation time, CPU/RAM, free disk, each GPU's model/VRAM, quota evidence, and connection state. Unknown is not zero.
2. Keep RAM, VRAM, local disk, and cloud storage separate. Several GPUs do not automatically form one large-memory GPU; different providers may not be available simultaneously. Historical snapshots are not promises.
3. Prefer CPU for documents, transfers, hashes, caption preparation, and suitable rendering. Allocate GPU only for an identified need or measured benefit. Run a small representative sample before committing an expensive batch.
4. Read [scheduling and recovery](references/scheduling.md). Persist a task record before submission. Give each shard one owner and reconcile existing work before retrying. Divide independent inputs, not duplicate batches.
5. If a dependency, permission, quota, or old-job state is unresolved, mark the affected task blocked or unknown. Continue independent authorized work. Do not purchase resources, switch accounts to bypass limits, or expand sharing through this skill.

## Coordinate and learn

Use external AI for bounded alternatives, implementation pieces, or review only when the service and shared material are authorized. The coordinating agent owns integration and correctness. Read [AI collaboration and learning](references/ai-and-learning.md) for task packets, evidence-backed notes, and feedback experiments.

When feedback changes an input, create a new revision and identify affected outputs before rerunning. Reply in the user's preferred language; internal task packets may use clear English. Do not claim saved notes are weight training or permanent memory.

## Finish with evidence

Read [quality and delivery](references/quality-and-delivery.md). Validate the final artifact, not only source code. Identify full checks versus sampling. Report actual progress, blockers, and an evidence-based remaining-time estimate; say when an estimate is not yet reliable.

Upload only to an authorized destination with the intended permissions. Verify recovery by downloading and comparing hashes. Cleanup requires effective authorization and verified recoverability; preserve active dependencies and learning notes. Release idle runtimes created for this work when no GPU task remains; do not stop jobs of unknown ownership.

## Use the bundled resources

See [usage](references/usage.md). Copy the blank [project configuration](assets/project-config.json) and [task manifest](assets/task-manifest.json), then fill actual values.

For a CPU-only recovery exercise, see [the local demo](examples/cpu-recovery/README.md). For dry-run behavior checks, see [scenario rubrics](tests/behavior/README.md). Neither demonstrates live provider integration.

Run `python scripts/validate_manifest.py /path/to/task-manifest.json` for offline checks. It reads JSON only: no network calls, authorization, dispatch, file-content verification, or distributed locking. An OK result confirms only the implemented offline checks, not permission to execute. Use one dispatcher or a real atomic claim mechanism for concurrent work.
