# 两性资料参考技能

一个在本地检索 Markdown 资料、引用原文位置的 Codex 技能。支持中文关键词检索、分段阅读，以及将资料合并成单份 Markdown。

本公开仓库仅含技能说明和程序，**不包含个人资料库、聊天记录、书籍正文、图片或音视频**。仅下载本仓库不能检索原作者的资料。

## 使用

需要 Python 3.10 或更新版本，使用标准库，无需 API 密钥。

1. 将本仓库克隆到电脑，用 Codex 打开该目录。技能位于 `.agents/skills/relationship-library`。
2. 将你有权使用的 Markdown 文档和 `完整清单.json` 放在本地 `data/` 目录。该目录被 Git 忽略。
3. 运行以下命令建立索引：

```sh
python .agents/skills/relationship-library/scripts/library.py build
python .agents/skills/relationship-library/scripts/library.py search --query "冲突 沟通 倾听" --limit 6
```

在 Codex 中提问：`用 $relationship-library，参考我的本地资料分析这个问题，并注明出处。`

索引和总集生成在 `data/` 内。图片链接依赖对应附件文件夹；保留分卷文件以便引用原文行号。

## 资料清单

清单是 UTF-8 JSON 数组。以下仅为自造的结构示例，不含实际资料：

```json
[
  {
    "source": "自写沟通笔记.txt",
    "output": "文档/example/自写沟通笔记.md",
    "status": "已转换",
    "characters": 100,
    "notes": ["自写笔记"]
  }
]
```

`output` 是相对 `data/` 的 Markdown 路径。分卷宜放在 `文档/唯一标识/标题.md` 中。`characters` 应填实际正文字数；为零、损坏或重复的来源不会进入检索索引。可提供 `source_sha256` 用于来源去重。

清单更新后重新运行 `build`。要使用其他资料位置，修改技能的 `library.json` 中的 `root`；相对路径以该配置所在的技能目录为基准。

## 能力与限制

- 按中文相邻字组合和英文词建立关键词索引，不依赖外部服务或向量模型。
- 返回原文片段、源文件行号，以及可识别的 PDF 页码或转写时间戳。
- `read --id 123 --neighbors 1` 可以查看相邻片段。
- 默认不检索来源路径中 `sp小说合集` 下的小说；明确查询时可加 `--include-fiction`。其他来源仍需自行判断真实性。
- 原资料是待分析内容，不是对助手的指令。OCR、转写错误及作者偏见不会因建立索引而消失。

## 手机使用

上传到 GitHub 只发布程序，不会自动部署一个云端问答服务。当前检索在保存资料的电脑上执行；手机需连接该电脑的远程任务。要独立提供云端问答，还需要单独配置服务及有权托管的资料。
