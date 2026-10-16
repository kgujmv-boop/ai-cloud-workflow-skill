# 检查旧成果还能不能用 / Inspect saved outputs

这个小项目有两个步骤：把文本转成大写，再统计字符数。第二步依赖第一步。输入、代码和已算出的结果都在 workspace 中，baseline.json 是这份示例的旧记录，current.json 是当前计划。

实际工作通常由助手准备记录和执行检查。不要为了让检查通过，把今天的文件重新写成“旧记录”。示例里的 baseline.sha256 随公开文件提供，方便试跑；真实项目应从此前可信的完成记录中取出基线摘要，并先确认来源。

从技能根目录执行（Linux，Python 3.9+）：

```sh
report_dir="$(mktemp -d)"
python scripts/inspect_reuse.py \
  --root examples/local-reuse/workspace \
  --baseline examples/local-reuse/baseline.json \
  --current examples/local-reuse/current.json \
  --baseline-sha256 85681bbc611bb2138c4a7a243314e252d3e34ae3c9094f87132c564a8d99b108 \
  --trust-baseline \
  --report "$report_dir/reuse-report.json"
```

原样检查应得到两个 eligible_for_reuse。它只表示实际文件与这份已接受的旧记录及当前计划相符，不代表科学内容正确、远程任务已结束或获得了执行授权。

要看变化如何传递，请先复制整个 examples/local-reuse 到新的临时目录，只修改副本里的 workspace/inputs/source.txt，再对这份副本运行同样的命令，并选择新的报告路径。两个步骤都应被阻止复用：大写结果的输入变了，字符统计的依赖也随之失效，即使旧的输出文件还在、字节没变。检查器不会替你重新计算。

## English usage

The fixture was generated and checked locally using the two small Python scripts under workspace/code. It is an illustrative baseline, not proof about a user's real project. The supplied digest pins these fixture bytes only. For production work, establish a trustworthy previous completion snapshot and separately retained digest before passing `--trust-baseline`.

Run the command above from the skill root. The report must be a new file outside the inspected workspace; its parent directory must already exist. Baseline and current records must be separate files. No inspected file is modified, and existing reports are never overwritten.

Exit codes:

- `0`: every task is locally eligible for reuse.
- `1`: at least one task is blocked or unknown; inspect the per-task reasons.
- `2`: invalid records, unsupported paths/platform, or an inspection/report error. Do not treat an incomplete or failed report as approval.

Test changes in a temporary copy. Changing source bytes, code, parameters, model revision, shard, or dependency membership blocks reuse. A missing or damaged output also blocks reuse. Changed upstream work invalidates downstream reuse transitively. Omitting the trust acknowledgment produces unknown rather than eligibility; a baseline digest mismatch is an integrity failure and blocks reuse.

Stop relevant writers during inspection. No-follow path handling and file metadata checks are not an atomic filesystem snapshot or protection against all malicious concurrent mutations. Linux is tested; other POSIX systems are not validated here, and unsupported capabilities fail closed. No network, cloud account, GPU, or third-party Python package is used.

Read [the record format and limitations](../../references/local-reuse.md) before applying this to a real project. Task manifest validation and local file inspection are different tools.
