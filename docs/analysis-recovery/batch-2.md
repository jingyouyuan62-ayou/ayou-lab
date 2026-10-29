# 历史分析恢复批次 2

日期：2026-10-27
范围：从 manifest 第一个未完成项继续，处理 3 条历史分析
方式：只读取历史原文、旧标准化草案和 Archive 数据；未读取图片，未调用视觉模型

## 成功标准化的条目

| 条目 | 原文格式 | 正式结果 | 待确认 |
| --- | --- | --- | --- |
| `Frozen Water` | structured JSON | 13/13 字段写入，`analysisSource` 已加入；2026-10-28 已按所有者确认修订元数据 | 已完成 |
| `Cloud Line` | structured Markdown | 13/13 字段写入，`analysisSource` 已加入 | 无新增待补充项 |
| `Gulls Overhead` | dense prose | 13/13 字段写入，`analysisSource` 已加入 | material 已由原文的天空、羽毛、翼缘、喙和脚映射完成 |

每条均在正式写入前保存了完整条目快照：

- `snapshots/batch-2/frozen-water-before-2026-10-27.json`
- `snapshots/batch-2/cloud-line-before-2026-10-27.json`
- `snapshots/batch-2/gulls-overhead-before-2026-10-27.json`

活跃映射另存于 `finalized/`，旧 `normalized/` 草案保持原样并记录在每条 sample 的
`validationDraft` 中。

## 待补充或需要重新分析

- `Frozen Water`：没有字段需要重新分析；13 个字段均来自历史原文。2026-10-28 项目所有者确认
  “以修改后的为准”，标题、category、note 与 accent 已按历史分析修订，旧状态保存在 revision
  文件和写入前快照中。
- `Cloud Line`：不需要重新分析。地点确认状态与 EXIF 时间疑点已按历史原文和当前 confirmed
  Echo 记录。
- `Gulls Overhead`：不需要重新分析。旧草案的 material 缺口可以从历史原文已有观察完成映射，
  最终文字没有增加新的画面事实。

本批没有因无法访问历史记录而跳过或重新分析的条目。

## 原文信息与判断

- 未发现原文已有信息在标准化过程中丢失。
- `Frozen Water` 初次导入未改变元数据；后续所有者确认后，标题、category、note 与 accent
  已按历史分析修订，修订记录单独保存。
- 未把 `Cloud Line` 的地点候选回退，也没有覆盖当前 confirmed「新疆」。
- 未把 `Gulls Overhead` 的地点或海鸥种类写成已确认信息。
- Visual DNA 保持原文判断；Archive category 继续使用现有顶层值。
- 未新增 confirmed Echoes。

## 数据检查

逐条检查均在写入后和 manifest 标记 `imported` 后运行：

- `Frozen Water`：通过；仅保留“当前没有 echoes”的既有结构提示。
- `Cloud Line`：通过，0 warning。
- `Gulls Overhead`：通过，0 warning。

批末检查：

```text
python3 -B scripts/check_analysis_recovery.py
OK: 8 recovery sample(s), 1 reanalysis record(s), 1 warning(s)

python3 -B scripts/check_archive.py
OK: 22 warning(s)
Checked 83 entries, 83 images, 19 with analysis.
```

恢复检查的唯一 warning 是 `Frozen Water` 没有顶层 Echoes，属于既有条目状态。Archive 的
22 条 warning 均为历史分析字段偏短的深度提示，没有结构错误、重复 id、缺失图片或无效 JSON。

## manifest 实际进度

- 已完成并标记 `imported`：8 / 72 条历史恢复记录。
- 剩余未导入：64 条。
- Archive 总数：83。
- 带 `analysis`：19。
- 仍缺 `analysis`：64。
- `Night Sparks` 的单独重分析仍保持 `applied`。

本轮停在 3 条，等待项目所有者确认后再继续下一批。
