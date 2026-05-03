# TokenJitter Skills

词元抖动的 AI 工具箱。

这里是我自己在用的、经过长期打磨的 Skills，现在决定把它们完整地、一字不改地开源出来。

两种东西，一个目的：把我积累的方法论变成可复用的工具。

- **Skills** — 重量级，遵循 [Agent Skills](https://agentskills.io) 开放标准的结构化指令集，安装后 Agent 会自动加载


## Skills

| Skill | 说明 |
|-------|------|
| [**feishu-sheet-reader**](./feishu-sheet-reader/) | 词元抖动 skills，读取飞书电子表格数据的 Skill。根据自然语言指令，自动定位表格、Sheet、列和行，返回目标数据。 |

### Skill 安装方式

**通过 Agent 安装**

在 Claude Code、Codex、OpenClaw 等支持 Skill 的 Agent 中，直接对话：

```
安装这个 skill：https://github.com/zjm533/TokenJitter-skills
```


