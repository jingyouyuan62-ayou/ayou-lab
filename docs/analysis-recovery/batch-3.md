# 历史分析恢复批次 3

日期：2026-10-28
范围：5 条历史分析
来源：同一份可审计的助手报告，session `01a0b4ac-0591-74c3-886d-c68e92c3580e`，
message `7ec740c5-5017-401a-bd95-3bfb516c6426`
方式：只读取本地历史原文和 Archive 数据；未读取图片，未调用视觉模型

## 成功标准化的条目

| 条目 | 原文格式 | 正式结果 | 待确认 |
| --- | --- | --- | --- |
| `Glittering Sea` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Forest Railway` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Fallen Leaves` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `White Bells` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Old Machine` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |

每条均先保存独立原文和写入前完整条目快照，再生成 final mapping：

- `original/glittering-sea.txt`
- `original/forest-railway.txt`
- `original/fallen-leaves.txt`
- `original/white-bells.txt`
- `original/old-machine.txt`
- `snapshots/batch-3/*-before-2026-10-28.json`
- `finalized/<id>.json`

## 判断与 Echoes

- 未改变任何标题、Archive category、accent 或原创视觉判断。
- `Forest Railway` 保留当前 confirmed「阿里山森林鐵道」，没有回退到历史候选阶段。
- `Fallen Leaves` 保留当前 confirmed「梧桐落葉」；树种疑问仍作为历史保留语气写入 uncertainty。
- `White Bells` 的 Yucca 品种候选留在原文中，没有擅自新增到当前 Echo candidates。
- `Old Machine` 保留当前 candidate「暗房放大機／早期攝影器材」与 confirmed「共感 Entanglements 展場的一件展品」。
- 没有把 AI 联想写成已确认 Echo。

## 缺失与重分析

本批不需要重新分析任何图片。历史原文没有整字段缺失；所有不确定性均在原文已有范围内保留：

- `Glittering Sea`：拍摄时间、地点、黑框意图与 source 待确认。
- `Forest Railway`：地点、真实拍摄日期与警示牌文字不可确认。
- `Fallen Leaves`：树种和地点不可确认。
- `White Bells`：品种与花苞状态不可确认。
- `Old Machine`：装置名称、用途与油灯归属不可确认。

## 数据检查

逐条写入后均运行单条恢复检查和 Archive 检查，并只在检查通过后将 manifest 改为
`imported`。标记完成后再次运行单条检查。

批末检查：

```text
python3 -B scripts/check_analysis_recovery.py
OK: 13 recovery sample(s), 1 reanalysis record(s), 1 warning(s)

python3 -B scripts/check_archive.py
OK: 35 warning(s)
Checked 83 entries, 83 images, 24 with analysis.
```

没有 JSON 解析错误、重复 id、缺失图片或来源哈希错误。恢复检查的唯一 warning 是
`Frozen Water` 没有顶层 Echoes。Archive 的 warning 均为历史原文映射字段偏短的结构提示，
没有为了消除 warning 而补写内容。

## manifest 实际进度

- 历史恢复已正式写入：13 / 72。
- 仍待恢复：59。
- Archive 总数：83。
- 带 `analysis`：24。
- 仍缺 `analysis`：59。

本批完成 5 条，失败 0 条，无需重分析条目 0 条。

## Frozen Water 后续确认

项目所有者在本批前确认 `Frozen Water`“以修改后的为准”。因此该条已改为：

- title：`Horse in Snow`
- category：`dream`
- accent：`#9FB6D4`
- note：与雪地中的马一致

历史原文、原写入前快照和修订前状态均保留；修订审计见
[`revisions/frozen-water-2026-10-28.json`](./revisions/frozen-water-2026-10-28.json)。
