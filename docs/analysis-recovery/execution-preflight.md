# 正式标准化试运行执行前检查

检查日期：2026-10-27
本轮对象：`Tomato`、`Night Sparks`、`Ginkgo & Fence`、`Henna Collage`、`Lantern Tree`

## 检查结果

1. **原始分析隔离**：8 份已完成样本各有独立
   `docs/analysis-recovery/original/<id>.txt`；本轮 5 条均已与历史 session 原段逐字 diff。
   标准化结果只写 `normalized/`，没有覆盖原文。
2. **双向追溯**：每条 normalized 草案都保存 `analysisSource`，包括 session ID、message ID、
   时间、分析时标题、原文路径、原文 SHA-256、来源格式和映射版本；同时保存当前图片路径与
   图片 SHA-256。
3. **信息保留**：本轮 5 条已按 uncertainty、Echoes、Visual DNA、标题、颜色、材质、交互等
   逐项对照；“16 项之外的原文信息”保留在原文，映射报告登记其未进入正式字段的原因。
4. **缺失字段**：`Night Sparks` 原文没有 `uncertainty`，草案保留明确待补充状态。没有用
   note、标签或常识补齐。
5. **不调用视觉模型**：本轮只读取本地分析 JSON、Markdown 和历史 session 文本；没有调用
   图片查看器，也没有重新分析图片。
6. **单条事务**：正式写入顺序固定为：写入该条 `analysis` / `analysisSource`（必要时补
   Echoes）→ 运行该条恢复检查 → 运行 Archive 结构检查 → 将该条 `archiveStatus` 改为
   `imported` → 再检查一次。任何一步失败都停止该条。
7. **断点恢复**：`manifest.json` 为每条保存 `archiveStatus`。`pending` 表示未进入正式
   Archive；`imported` 表示已写入并通过检查。恢复时从第一个 `pending` 继续，已 `imported`
   的条目不重复创建或重复写入。

## 当前基线

- `data/entries.json`：83 条。
- 已有 `analysis`：11 条。
- 本轮 5 条：全部为 `archiveStatus: pending`，尚无正式 `analysis`。
- 本轮仍不修改网页设计，不开始 Understanding 功能。

## 单条成功条件

一条记录只有同时满足以下条件，才可标记 `imported`：

- `analysis` 的 13 个键和顺序符合规范，值均为非空 string。
- `analysisSource` 与 normalized 草案完全一致，原文哈希匹配。
- 原图路径存在，图片 SHA-256 匹配。
- 顶层 title、category、accent 与草案记录一致。
- 有 Echoes 的条目与当前值或草案中的明确恢复提案一致。
- `check_analysis_recovery.py --entry <id>` 通过。
- `check_archive.py` 通过，且条目总数、图片数和唯一 id 未异常变化。

失败时只停止当前条目；之前已经标记 `imported` 的条目不回滚。
