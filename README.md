# AI 算力与工具协作技能

![让 AI 按任务选择工具和算力](assets/header.png)

[怎么使用](#怎么开始) · [技能说明](SKILL.md) · [使用指引](references/usage.md) · [English](#english-documentation)

你给 AI 一个任务，它可能需要写代码、查资料、跑模型，或把文件存到云盘。这个技能告诉它如何选择合适的资源：先看手头有什么、哪些任务已经在跑，再决定用什么工具，做到哪一步就记下来。

dot、bot、muse、Codex、Claude 等助手，只要能读取这些文件，并具备任务需要的工具和授权，就可以参照执行。编程、研究、数据分析、媒体制作都能用。

## 它会怎样安排工作

![了解需求、比较方案、检查连接、安排任务、检查结果](assets/workflow.png)

| 需要选工具时 | 任务开始后 | 做完以后 |
| :--- | :--- | :--- |
| 查找当前可用的免费方案，说明限制和费用，供你选择。 | 检查已有任务，分配不同工作，保存进度。 | 检查结果和备份，按授权清理文件、释放空闲算力。 |

比如分析一份小数据，它应先考虑 CPU；确实需要跑模型时，再检查 GPU 和剩余额度。多个平台一起用，也要先分清各自负责哪一部分，避免重复提交。

中途断线后，助手应先找回任务记录、检查已完成的文件，再决定从哪里继续。学习参考资料时，也要记清看过哪些内容、试过什么方法，以及实际效果如何。

## 怎么开始

最方便的方式是把这个仓库的链接发给能浏览网页、读写文件的 AI，让它先检查内容，再下载完整技能并按自己的环境配置。模板填写、工具检查和任务安排通常也由它完成。

你可以直接发送：

> 请读取 https://github.com/kgujmv-boop/ai-cloud-workflow-skill ，检查技能内容，在你的工具和授权范围内下载完整 Skill 并配置。使用 orchestrate-ai-cloud-work 帮我完成接下来的任务，需要我登录或确认权限时再告诉我。

如果需要手动安装，将完整文件夹命名为 `orchestrate-ai-cloud-work`，其中直接放置 `SKILL.md`，保留其余文件的相对路径。仓库克隆出来如果叫 `ai-cloud-workflow-skill`，安装前将这份文件夹改名。客户端已管理的安装目录不要自行改名。

支持按名称调用的客户端可以使用 `$orchestrate-ai-cloud-work`；其他助手可以读取 `SKILL.md` 和相关参考文件。各客户端能力不同，是否能自行下载和配置，要由它检查；软件安装、账号访问等仍需遵循相应授权。

可以这样开始：

> 使用 orchestrate-ai-cloud-work。我想分析这份公开数据，只用免费资源。先看看现有工具够不够用；需要其他服务的话，请查找可用方案，说明限制，让我选择。

也可以用来接着做未完成的工作：

> 继续昨天的代码项目。先看看哪些已经完成、哪些还在运行，再安排剩下的部分。

需要登录时，助手应告诉你要登录哪个网站、用来做什么、需要哪些权限，再引导你通过官方页面或安全登录界面操作。已经连接好的服务不用重复登录；暂时不想连接的，可以先跳过，继续做不依赖它的部分。

需要其他 AI 协助时，由 dot 这类助手在授权范围内分配任务、传递必要材料、取回结果，并检查后合并到项目中。你不用来回复制提示词；需要登录、授予权限或做选择时再参与。

更多示例见 [使用指引](references/usage.md#中文使用指引)。

## 目前包含什么

这是一套给 AI 读取的操作说明，附有项目模板和离线检查脚本。仓库没有自动连接 Kaggle、Colab、云盘等平台的适配器；实际登录、上传、运行和下载，需要由助手已有的浏览器、连接器或代码工具完成。

- `SKILL.md`：执行入口，按任务指向需要的参考文件
- `references/`：选方案、登录、分工、恢复、学习和成果检查；视频与配音单独说明
- `assets/`：空白项目模板、任务清单和主页图片
- `scripts/`、`tests/`：任务清单规则检查、实际文件复用检查及 CPU 测试
- `agents/`：可选的客户端信息，其他客户端可以忽略

安装方法和工具能力因客户端而异。加载技能不会自动获得 GPU、云盘或账号权限，也不会启动后台任务。

## 本地试跑

[CPU 恢复示例](examples/cpu-recovery/README.md)使用一份小数据展示分片、保存进度、中断后复用结果，以及备份恢复检查，不需要云账号。另有[行为检查情景](tests/behavior/README.md)，用于检查助手在额度不足、任务状态不明和备份失败时如何处理。情景评分与真实云平台测试是两回事。

[自动测试](.github/workflows/tests.yml)会运行任务清单单测和 CPU 恢复示例。[四情景对照记录](tests/behavior/evaluation-2026-10-16/README.md)保留了有 / 无 Skill 的完整回答和评分；本次两组结果相同，没有证明 Skill 更优。

[本地复用检查](examples/local-reuse/README.md)会重新计算实际文件哈希，并对照旧记录检查当前输入、代码、参数和依赖。它只新建报告，不覆盖文件、不重跑任务。旧记录是否可信仍需先确认。

## 使用前需要知道

免费 GPU 和试用额度随平台、账号和时间变化，要以当前检查结果为准。已有付费订阅、云盘费用以及开源工具的托管成本，应单独列出。多块显卡也不会自动合成一块大显存显卡。

方案建议不等于操作授权。购买、上传、增加账号权限或删除文件，都要遵循你的有效授权。不要把密码、令牌或 Cookie 发到聊天或写进项目记录。登录会话可能失效，不能保证一直保持连接。

任务清单检查脚本只检查 JSON 中已实现的规则，不会联网查询额度、检查实际文件内容或提交任务。检查通过也不代表任务已经完成或可以直接执行。它会检查完成记录是否写了输出位置、哈希和验证标记，依赖是否完成，以及是否重复安排了同样的工作；有理由的重新计算需填写原因。实际文件能否访问、内容是否匹配，仍需助手另行检查。

本项目采用 [MIT 许可证](LICENSE)。引用的第三方项目仍按各自许可证使用。参考项目链接在 [AI 协作与学习](references/ai-and-learning.md)，这里没有打包它们的代码或私人素材。

## English documentation

This skill gives an AI assistant instructions for choosing tools and compute, dividing work, recording progress, and checking results. It can support coding, research, data analysis, and media projects.

Assistants such as dot, bot, muse, Codex, and Claude can follow it when they can read the files and have the tools and authorization needed for the task. A dedicated cloud computer is optional. Browser control and code execution depend on the client.

### What the assistant should do

Check the user's goal, budget, existing resources, and running jobs first. When alternatives are needed, research current free options and explain their limits. Paid alternatives may be useful when the budget allows them; a free-only request excludes them.

Use CPU where it fits. Check GPU availability before assigning GPU work. Give separate inputs to separate workers, record progress, and inspect existing outputs before retrying interrupted work. Document what was actually studied and tested when learning from references. Check final files and recoverable backups before any authorized cleanup.

### Load and use

You can give the repository URL to an AI with browser and file tools and ask it to inspect the contents, download the complete skill, and configure it for its actual environment. This depends on available tools and required software and access approvals.

When another AI service is useful, the coordinating assistant delegates a bounded task, sends authorized materials, retrieves its output, and reviews and integrates the result. The user need not relay prompts; they take part when login, permission, or a choice is needed.

For manual installation, download the full folder and name the folder used for installation `orchestrate-ai-cloud-work`, with `SKILL.md` directly inside it. If a repository clone is named `ai-cloud-workflow-skill`, rename that copy before installation. Do not rename an installation directory already managed by the client. Keep relative file paths intact and use the client's supported skill-loading or file-reading interface.

Clients supporting named invocation may use `$orchestrate-ai-cloud-work`. Other assistants can read `SKILL.md` and the relevant references. `agents/openai.yaml` is optional Codex metadata. There is no guarantee of automatic installation or identical tools and APIs across clients.

Example request:

> Inspect https://github.com/kgujmv-boop/ai-cloud-workflow-skill and configure its complete skill using your supported tools and required approvals. Use orchestrate-ai-cloud-work to help me analyze this public dataset with free resources. Check whether my existing tools are enough. If another service is needed, compare available options and let me choose.

On first use, the assistant should ask only for missing requirements. It should check relevant connections, explain any needed sign-in, and verify access before continuing. A declined connection should not block independent work. Installing the skill does not start a background service.

### Templates and checks

The assistant normally fills the templates, runs checks, and configures supported tools within its authorization. The user supplies goals and constraints and takes part when login, permission, or payment decisions are needed. See [usage](references/usage.md). For manual inspection, copy the project configuration and task manifest from `assets`, fill in actual values, and run:

```sh
python scripts/validate_manifest.py /path/to/task-manifest.json
python -m unittest discover -s tests -v
```

The checker uses Python's standard library. It checks only the implemented JSON rules offline. It does not query quotas, verify actual file contents, submit jobs, or grant authorization. It checks recorded output locations, hashes and verification flags for completed tasks, dependency completion, and equivalent work. An intentional rerun of completed work needs a reason. Actual file access and content checks remain separate.

The separate [local reuse inspector](references/local-reuse.md) reads actual files and compares them with a trusted prior baseline and current plan, including transitive dependencies. It exclusively creates a new report and never changes source files or schedules work. The caller must establish baseline provenance; a digest alone cannot prove its origin.

This repository contains instructions, templates, and these local checkers. It does not include automatic platform adapters for Kaggle, Colab, or cloud storage. The assistant must perform those operations with its existing tools.

See the [CPU recovery demo](examples/cpu-recovery/README.md) for a local exercise and [behavior scenarios](tests/behavior/README.md) for dry-run evaluation rubrics. These are not live cloud integration tests.

[CI](.github/workflows/tests.yml) runs the manifest tests and CPU recovery demo. The [four-case comparison](tests/behavior/evaluation-2026-10-16/README.md) preserves both responses and scoring; the two conditions tied, with no demonstrated advantage.

### Limits and permissions

The skill supplies no hardware, subscription, or persistent login. Free allocation can change, and multiple GPUs do not automatically pool VRAM. Account for existing paid storage, subscriptions, and hosting costs separately.

Uploads, purchases, account permissions, and deletion require effective authorization. Keep passwords, tokens, and cookies out of conversations and project files. Check backups before authorized cleanup and preserve files still needed by other work.

Public reference projects are linked in [AI collaboration and learning](references/ai-and-learning.md); their code and private media are not bundled. This project is licensed under [MIT](LICENSE). Linked third-party projects retain their own licenses.
