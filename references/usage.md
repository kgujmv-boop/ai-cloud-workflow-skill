# Usage / 使用指引

## 中文使用指引

可以直接把仓库链接交给能浏览网页、读写文件的 AI，让它检查内容、下载完整技能并按实际环境配置，遵循所需的软件安装和访问授权。也可以把完整文件夹交给助手，说明目标、交付形式、预算和已有资源。它应先检查实际能力，再规划执行；不必为了使用技能先登录所有网站。

- **选方案：**“我想分析这份公开数据，只用免费资源。请查证当前方案，比较数据容量、隐私、使用限制和操作难度，让我选择。”
- **开始工作：**“使用这个技能完成项目。需要我登录时，先说明哪个网站、为什么需要、需要哪些权限。”
- **恢复工作：**“继续昨天的项目，先核实已有输出和运行中的任务，缺什么再补什么。”
- **学习改进：**“研究这些参考资料，记录实际看过的部分和可借鉴的方法，应用到下一版，再根据反馈评估。”

首次使用时，AI 只补问上下文中没有的必要信息。明确只用免费资源时，不加入付费推荐；已有确定方案时，不强行重新选。登录需通过官方页面或安全交接完成，不在聊天中提交密码、令牌或 Cookie。加载技能不代表授权所有操作，也不会自动启动后台服务。

项目配置和任务清单模板在 assets 中。填入真实数据；空值表示尚未配置，不能直接当作可执行任务。下面的英文说明给出模板和检查命令。任务清单脚本通过只说明 JSON 规则通过。需要判断旧成果能否复用时，让助手运行[本地复用检查](local-reuse.md)：分别读取可信的旧记录与当前计划，重新计算实际文件哈希，检查输入、代码和依赖是否变化。它会新建一份报告，不会改动原文件或自行重跑任务。

## English instructions

This workflow targets AI assistants and tools such as dot, bot, muse, Codex, and Claude when configured with relevant capabilities. Inspect actual browser, file, code-execution, and connector access; do not assume every client supports them all. A dedicated cloud computer is not required. Load the folder using the client's supported skill or file interface. Clients without native skills can read SKILL.md and the relevant references manually. Do not assume identical tools, APIs, or automatic installation.

Example requests:

“Use orchestrate-ai-cloud-work. Inspect existing jobs and free compute, divide this narration task among available GPUs, use CPU for captions and assembly, then verify the deliverable.”

“Recover yesterday's project. Locate validated completed shards before rerunning anything.”

“Study these reference videos, document exactly what you inspected, apply one technique to the next version, and evaluate it when I provide results.”

Clients supporting named invocation may use `$orchestrate-ai-cloud-work`. The optional agents/openai.yaml file supplies Codex UI metadata; other clients can ignore it.

The user can provide the repository URL and ask the assistant to inspect, download, and configure the complete skill using supported tools and required approvals. Do not assume every client can install skills autonomously. The assistant normally fills project templates and runs checks itself. For authorized external-AI collaboration, it sends bounded task materials, retrieves output, and reviews and integrates it; do not require the user to shuttle prompts. Request user participation for needed login, authorization, or decisions.

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

## Inspect existing outputs before reuse

Ask: “Check whether the saved outputs still match my current inputs, code, parameters, model and dependencies. Write a new recovery report before deciding what to rerun.” The assistant prepares the two separate records and runs the [local inspector](local-reuse.md). It must obtain a trusted baseline digest from the earlier completion record, not calculate a digest of an untrusted baseline and call that proof. The report is a local compatibility observation, not authorization or evidence that a remote job ended.
