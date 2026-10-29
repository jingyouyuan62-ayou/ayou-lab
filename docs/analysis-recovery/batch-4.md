# 历史分析恢复批次 4

日期：2026-10-28
范围：5 条历史分析
来源：session `01a0b4ac-0591-74c3-886d-c68e92c3580e`，
message `855fae5f-8e36-4fdb-bd4c-a0a73bb3ced9`
方式：只读取本地历史原文和 Archive 数据；未读取图片，未调用视觉模型

## 成功标准化的条目

| 条目 | 原文格式 | 正式结果 | 待确认 |
| --- | --- | --- | --- |
| `Above Jiufen` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Green Courtyard` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Snow Globes` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Backlit Reeds` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |
| `Gulls & Water` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无缺失字段 |

每条均先保存独立原文、原文哈希和写入前完整条目快照，再生成 final mapping：

- `original/<id>.txt`
- `snapshots/batch-4/<id>-before-2026-10-28.json`
- `finalized/<id>.json`

## 判断与 Echoes

- 未改变任何标题、Archive category、accent 或原创视觉判断。
- `Above Jiufen` 保留历史 DREAM 分析，同时保留当前顶层 category `memory`；当前 confirmed「九份」未改动。
- `Green Courtyard` 保留当前 confirmed「松山文創園區」。
- `Snow Globes` 保留当前 confirmed「上海外灘源聖誕集市」，历史 AI 候选没有升级。
- `Backlit Reeds` 当前 Echo 为空数组，历史原文也没有需要恢复的候选。
- `Gulls & Water` 保留当前 confirmed「青島」。

## 缺失与重分析

本批不需要重新分析任何图片。历史原文没有整字段缺失，所有不确定性均保留在原文已有的
观察范围内：

- `Above Jiufen`：具体拍摄点和小岛识别仍不能完全确认。
- `Green Courtyard`：场所性质和滤镜造成颜色的程度不可确认。
- `Snow Globes`：地点、商店名和摆件归属不可确认。
- `Backlit Reeds`：植物种类和拍摄地点不可确认。
- `Gulls & Water`：地点以及三只鸟是否属于同一组动作不可确认。

## 数据检查

逐条写入后均运行单条恢复检查和 Archive 检查；只有检查通过后才标记 manifest 为
`imported` 并再次运行单条检查。

批末结果：

```text
python3 -B scripts/check_analysis_recovery.py
OK: 18 recovery sample(s), 1 reanalysis record(s), 1 warning(s)

python3 -B scripts/check_archive.py
OK: 52 warning(s)
Checked 83 entries, 83 images, 29 with analysis.
```

恢复检查的唯一 warning 是 `Frozen Water` 没有顶层 Echoes。Archive 的 warning 都是历史
原文映射字段偏短的结构提示；没有 JSON 错误、重复 id、缺失图片或哈希不一致。

## manifest 实际进度

- 历史恢复已正式写入：18 / 72。
- 仍待恢复：54。
- Archive 总数：83。
- 带 `analysis`：29。
- 仍缺 `analysis`：54。

本批完成 5 条，失败 0 条，需要重分析 0 条。
