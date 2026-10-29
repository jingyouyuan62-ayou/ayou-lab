# 历史分析恢复批次 5

日期：2026-10-28
范围：5 条历史分析
来源：session `01a0b4ac-0591-74c3-886d-c68e92c3580e`，
message `ef5362cb-bf65-4a4b-976c-72ec17049607`
方式：只读取本地历史原文和 Archive 数据；未读取图片，未调用视觉模型

## 成功标准化的条目

| 条目 | 原文格式 | 正式结果 | 待确认 |
| --- | --- | --- | --- |
| `Forest Walk` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Magnolia` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Yulan` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Pasture & Forest` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Green Canal` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |

每条均先保存独立原文、原文哈希和写入前完整条目快照，再生成 final mapping：

- `original/<id>.txt`
- `snapshots/batch-5/<id>-before-2026-10-28.json`
- `finalized/<id>.json`

## 判断与 Echoes

- 未改变任何标题、accent 或已确认 Echoes。
- `Forest Walk` 保留当前 confirmed「阿里山」。
- `Magnolia` 的广玉兰品种候选保持 candidate，未升级为 confirmed。
- `Yulan` 的历史 Visual DNA 为 `COLOR`，当前 Archive category 为 `dream`；两者按各自层级保留。
- `Pasture & Forest` 保留当前 confirmed「新疆」。
- `Green Canal` 的历史 Visual DNA 为 `DREAM`，当前 Archive category 为 `memory`；当前 confirmed
  「夏日的水杉」「我很喜歡杉樹」原样保留。

## 缺失与重分析

本批不需要重新分析任何图片。历史原文没有整字段缺失：

- `Forest Walk`：具体地点与真实拍摄时间无法确认。
- `Magnolia`：具体品种与拍摄时间无法确认。
- `Yulan`：具体品种与拍摄时间无法确认。
- `Pasture & Forest`：具体地点无法进一步确认。
- `Green Canal`：地点与树种无法确认。

## 数据检查

逐条写入后均运行单条恢复检查和 Archive 检查；只有检查通过后才标记 manifest 为
`imported` 并再次运行单条检查。

批末结果：

```text
python3 -B scripts/check_analysis_recovery.py
OK: 23 recovery sample(s), 1 reanalysis record(s), 1 warning(s)

python3 -B scripts/check_archive.py
OK: 68 warning(s)
Checked 83 entries, 83 images, 34 with analysis.
```

恢复检查的唯一 warning 是 `Frozen Water` 没有顶层 Echoes。Archive 的 warning 都是历史
原文映射字段偏短的结构提示；没有 JSON 错误、重复 id、缺失图片或哈希不一致。

## manifest 实际进度

- 历史恢复已正式写入：23 / 72。
- 仍待恢复：49。
- Archive 总数：83。
- 带 `analysis`：34。
- 仍缺 `analysis`：49。

本批完成 5 条，失败 0 条，需要重分析 0 条。
