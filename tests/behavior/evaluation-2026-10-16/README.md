# 四个情景的有 / 无 Skill 对照

2026-10-16 做了两组实际回答：一组可读取 Skill，另一组不读取。输入相同，都是先前写好的四个虚构情景。这里只比较回答中的处理计划，没有登录平台、提交任务或删除文件。

结果：两组均为 21 项通过、6 项部分满足或未证明、0 项违反。没有显示出哪组更好，也不能据此说 Skill 提高了完成率或节省了算力。

两组都知道：免费额度耗尽不能直接付费；任务状态不明时不能重提；备份哈希不一致时不能删除本地文件。共同的不足是，复用未改动片段前，没有明确检查当前输入和依赖是否仍然兼容。部分评分要求实际记录或文件，这次只要求写计划，因此未获得执行证据分；不能把这些缺项当成真实运行失败。

这个结果提醒我们：熟练的助手本身也可能提出合理方案。Skill 的规则是否在更复杂的实际任务中有用，还需要更多测试。这四个例子不够作普遍结论。

## 查看原始材料

- [输入情景](requests.json)与[预先确定的评分标准](rubric.json)
- [读取 Skill 的回答](with-skill.md) / [未读取 Skill 的回答](without-skill.md)
- [逐项评分](assessment.md) / [机器可读评分](scores.json)
- [实验方法与限制](protocol.md) / [任务提示](prompts.md)
- [文件校验与版本](provenance.json)

## English summary

Both conditions received 21 pass, 6 partial/not-demonstrated, and 0 fail judgments across 27 unweighted criteria. This small plan-only comparison demonstrates no overall winner. It provides no live execution evidence or statistically meaningful improvement estimate.

Both responses handled the key safety decisions sensibly. Both omitted an explicit current-input-and-dependency compatibility gate for reusing A/C. Evidence-only omissions are expected where a plan-only task cannot supply actual artifacts; they must not be presented as observed operational failures.

One response session per condition answered all four cases. The exact model build and sampling settings were unavailable. See the protocol for full limitations. The separately tested CPU demo and manifest checker cover local code behavior, not these agents' real cloud execution.
