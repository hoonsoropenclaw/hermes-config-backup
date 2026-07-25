# Creative Intent Classification — If→Then Rules
**Created**: Cycle 500, 2026-07-16
**Type**: D3-learn (实作型)
**Validated by**: metacognitive-learner Cycle 500

## 背景

赫米斯在收到创意请求时，识别「这是否是创意请求」的预处理能力未被系统化。
Cycles 490/492/498 处理了创意 pipeline、6-type taxonomy、content moderation，
但从处理过「收到请求时如何判断这是创意任务」的问题。

理论参考：
- TELUS Digital DART：partial intent classification = intent classifier + LLM + RAG
- ScienceDirect (2025)：GPT/BERT/LLaMA/RoBERTa 在 intent classification 上的比较
- Springer Generative AI Survey (2026)：hierarchical taxonomy 用于 multimodal content routing

---

## If→Then 经验

### If 赫米斯收到一个新的用户请求
### Then 先判断「这是否是创意生成任务」，使用以下决策树：

```
用户请求
  │
  ├─ 包含生成关键词（画/生成/创作/设计/作曲/写歌/拍片）
  │    └─ 是创意生成请求 → 进入 6-type taxonomy routing
  │
  ├─ 包含分析/修改/优化关键词（分析/改写/润色/优化）
  │    └─ 是非生成创意任务 → 走 standard LLM pipeline
  │
  ├─ 纯信息查询（什么是/如何/解释）
  │    └─ 非创意任务 → standard RAG/search pipeline
  │
  └─ 其他 → 置信度判断：
       ├─ 置信度 > 0.7 → 按判断处理
       └─ 置信度 ≤ 0.7 → 询问用户确认
```

### 原因
创意生成 vs 非创意任务的处理 pipeline 完全不同：
- 创意生成：6-type taxonomy → mmx pipeline → moderation check
- 非创意：standard LLM pipeline
混淆两者会导致用 LLM 任务处理创意请求（效果差）或用创意 pipeline 处理信息查询（资源浪费）

---

### If 赫米斯判断一个请求是「创意生成请求」
### Then 使用 6-type taxonomy 做 modality routing：

| 关键词 | 类型 | 工具 |
|--------|------|------|
| 图/画/生成图片 | image | mmx image generate |
| 视频/片/生成影片 | video | mmx video generate |
| 歌/音乐/作曲 | music | mmx music generate |
| 语音/配音/TTS | speech | mmx speech generate |
| 文字/文章/写 | text | mmx text generate |
| 音乐封面/COVER | music-cover | mmx music cover |

### 原因
6-type taxonomy 已在 Cycles 487-490 验证完毕，mmx-cli 支持全部 6 种类型。
做 modality routing 可避免用错误工具处理请求（如用 image 工具处理 music 请求）

---

### If 用户的创意请求同时包含多种模态（如「画一首歌」）
### Then 将请求拆解为独立步骤，顺序处理：

1. 先用 text 生成歌词/描述
2. 再用 music 生成旋律
3. 如需要封面 → 再用 image 生成封面

### 原因
多模态请求如果一次性处理容易失败（某一步出错导致全部重做）。
pipeline DAG 已在 `creative-pipeline-dag-20260713.md` 定义，遵循该 SOP 的 fault tolerance 原则。

---

### If 用户请求被判定为「边界情况」（创意 + 非创意混合）
### Then 识别主要意图，询问用户确认次要意图的处理方式：

```
「帮我写一首关于X的歌，然后画一个封面」
→ 主意图：music（占 70%）
→ 次意图：image（占 30%）
→ 回复：「好的，我先帮你生成歌曲。封面要同步生成，还是等歌曲完成后再单独生成？」
```

### 原因
混合意图如果直接并行处理，用户可能只需要主意图而次意图是随口一说。
询问确认避免做无用功，也避免creative pipeline资源浪费。

---

## 核心理解

| 维度 | 说明 |
|------|------|
| 为什么需要预判 | creative pipeline vs standard LLM pipeline 完全不同 |
| 预判的输入 | 用户原始请求文本 + 关键词匹配 |
| 预判的输出 | creative_task=True/False + 主要 modality（6-type） |
| 置信度阈值 | >0.7 直接处理，≤0.7 询问确认 |
| 失败模式 | 创意请求用 LLM pipeline 处理 → 效果差；LLM 请求用 creative pipeline → 资源浪费 |

---

## 关联 SOP

- `creative-pipeline-dag-20260713.md` — 创意 pipeline DAG + fault tolerance
- `image-moderation-reframing-20260709.md` — content moderation 处理
- mmx-cli skill — 6-type taxonomy 工具实现
