# 历史分析恢复批次 6

日期：2026-10-28
范围：3 条历史分析
来源：session `01a0b4ac-0591-74c3-886d-c68e92c3580e`，
message `c4ac2edc-45eb-4bc5-9189-cc4da44c12b0`
方式：只读取本地历史原文和 Archive 数据；未读取图片，未调用视觉模型

## 成功标准化的条目

| 条目 | 原文格式 | 正式结果 | 待确认 |
| --- | --- | --- | --- |
| `Blue House` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Cut Oranges` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Osmanthus` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |

每条均先保存独立原文、原文哈希和写入前完整条目快照，再生成 final mapping：

- `original/<id>.txt`
- `snapshots/batch-6/<id>-before-2026-10-28.json`
- `finalized/<id>.json`

## 判断与 Echoes

- 未改变任何标题、category、accent 或已确认 Echoes。
- `Blue House` 保留 confirmed「青島老城區」；原文的地点候选已在后续被确认。
- `Cut Oranges` 保留 AI 品种 candidate 和 confirmed 电影联想。
- `Osmanthus` 保留 confirmed「桂花」，同时保留历史原文对品种并非 100% 确定的语气。
- 三条原文中的 `typography: 无文字` 和 `interaction: 无` 只映射为规范空值句，
  没有新增交互方案或文字内容。

## 缺失与重分析

本批不需要重新分析任何图片。历史原文没有整字段缺失：

- `Blue House`：具体地点无法从画面确认；拍摄日期未知，Archive 的 `2026-09-18`
  是导出日期。
- `Cut Oranges`：橙、橘、柑的具体品种无法确认；切开果实的原因无法从照片判断。
- `Osmanthus`：历史判断把握较高但并非 100%；具体地点未知。

## 可追溯性检查

三条正式条目均与对应 finalized mapping 的 `analysis` 和 `analysisSource` 完全一致。
历史原文 SHA-256、图片 SHA-256 与记录值一致；写入前快照保留原顶层元数据及 Echoes。

逐条写入后均运行单条恢复检查和 Archive 检查；只有检查通过后才标记 manifest 为
`imported` 并再次运行单条检查。

批末结果：

```text
python3 -B scripts/check_analysis_recovery.py
OK: 26 recovery sample(s), 1 reanalysis record(s), 1 warning(s)

python3 -B scripts/check_archive.py
OK: 79 warning(s)
Checked 83 entries, 83 images, 37 with analysis.
```

恢复检查的唯一 warning 是 `Frozen Water` 没有顶层 Echoes。Archive 的 warning 都是历史
原文映射字段偏短的结构提示；没有 JSON 错误、重复 id、缺失图片或哈希不一致。

## manifest 实际进度

- 历史恢复已正式写入：26 / 72。
- 仍待恢复：46。
- Archive 总数：83。
- 带 `analysis`：37。
- 仍缺 `analysis`：46。

本批完成 3 条，失败 0 条，需要重分析 0 条。
