# 剩余历史分析恢复与归档

日期：2026-10-28
范围：manifest 中剩余 46 条历史分析
方式：先恢复历史原文；仅对 14 条原文缺口按项目所有者授权读取原图

## 结果

- 直接由历史原文标准化并正式写入：32 条
- 历史原文可用、但必要字段不完整：14 条
- 后经原图补全并正式写入：14 条
- 失败：0 条
- 无法定位历史原文：0 条
- 仍需重新分析：0 条

历史恢复台账现为 72 条：

- 已正式写入：72 条
- 待重新分析：0 条

Archive 当前为 83 条，83 条均带正式 `analysis`。

## 正式写入的 32 条

`Daisies`、`Cherry Blossoms`、`Moon & Branches`、`Golden Branches`、
`Fishing Harbor`、`Rocks & Surf`、`Flower Field`、`Meadow Cabin`、`Lotus Pond`、
`City Canopy`、`Record Collage`、`Slow Down`、`Dusk Street`、`Hydrangeas`、
`Fallen Tree`、`Pond Grass`、`Lighthouse`、`Embroidered Lilies`、
`Sunlit Canopy`、`Long Afternoon`、`Lake Road`、`Purple Roses`、
`Lilac Hydrangeas`、`Mountain Pavilion`、`Green Tunnel`、`Backlit Thicket`、
`Valley Overlook`、`Purple Swirls`、`Road Mirror`、`Matcha Dessert`、
`Teal Liberty`、`Fujin Street`。

每条均具备：

- 独立保存的历史原文与 SHA-256。
- 标准化前的 Archive 条目快照。
- 可追溯的 session ID、message ID、时间与历史标题。
- 13 个 `analysis` 字符串字段及顶层 `title`、`accent`、`echoes`。
- 写入后通过单条恢复检查。

## 由原图补全的 14 条

这 14 条都有可核验的历史分析，但原文没有可核验的 `uncertainty`，其中部分条目还缺少
其他字段。项目所有者授权后，按每批 2–3 张读取原图；每次只读取一张，未重新分析其他图片。

| 条目 | 历史原文明确缺少的字段 |
| --- | --- |
| `Under the Canopy` | `uncertainty` |
| `Soft Object` | `uncertainty` |
| `Bridge & Sky` | `uncertainty` |
| `Park Bench` | `typography`, `material`, `interaction`, `uncertainty` |
| `Chia Chia Records` | `uncertainty` |
| `Tiaoshi Station` | `uncertainty` |
| `College Gate` | `spatialDepth`, `hierarchy`, `interaction`, `uncertainty` |
| `Literature Corridor` | `typography`, `material`, `interaction`, `uncertainty` |
| `共感 / Entanglements` | `uncertainty` |
| `Tomato Illustration` | `uncertainty` |
| `Kiki's Delivery Service` | `uncertainty` |
| `Jiming Temple` | `typography`, `interaction`, `uncertainty` |
| `Airplane` | `typography`, `material`, `hierarchy`, `interaction`, `uncertainty` |
| `Lantern Light` | `uncertainty` |

对应的原文保存在 `docs/analysis-recovery/original/`，旧映射草案保存在
`docs/analysis-recovery/normalized/`；重分析前快照与新草稿保存在
`docs/analysis-recovery/reanalysis/`。历史文件均未覆盖。

`uncertainty` 只记录原图确实无法确认、且值得保留的事项。画面没有显著疑点时，按规范使用
“本图未发现需特别保留的不确定项”，没有为了填满字段强行推断地点、日期或设备。

## 历史来源

本批使用四份可访问的本地 Codex session：

- `01a09ed2-fcd9-7ba0-a7dd-bc85721df254`
- `01a0b4ac-0591-74c3-886d-c68e92c3580e`
- `01a0cddc-8a20-7452-a8df-ba63bcc59d9b`
- `01a11eef-e71c-7240-bd19-bb7c015e6da3`

逐条 session ID、message ID 与时间不在本文重复，以 `manifest.json` 和条目
`analysisSource` 为准。

## 数据检查

```text
python3 -B scripts/check_analysis_recovery.py
OK: 72 recovery sample(s), 15 reanalysis record(s), 8 warning(s)

python3 -B scripts/check_archive.py
Checked 83 entries, 83 images, 83 with analysis.
OK: 267 warning(s)
```

- Recovery 的 8 个 warning 都是当前条目没有顶层 `echoes`；没有自动补造 Echoes。
- Archive 的 warning 是历史分析字段偏短的结构提示，不是 JSON、路径或类型错误。
- 无重复 id、重复恢复样本、缺失图片或原文/图片哈希不一致。

## Git 状态

本轮未 commit、未 push、未修改网站设计。`data/entries.json` 与恢复文档仍是工作区中的
未提交变更；线上 GitHub Pages 不会反映这些本地更新。

## 下一步

历史分析恢复与补录已全部完成。后续只剩项目所有者的内容审阅，以及是否按项目流程 commit
和 push；本轮没有修改网站设计，也没有开始 Understanding 功能开发。
