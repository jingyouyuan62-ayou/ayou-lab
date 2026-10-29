# 第一次正式标准化试运行

执行日期：2026-10-27
范围：5 条已验证的历史分析
结果：5 条写入，0 条失败

## 单条结果

| 条目 | 字段 | 来源校验 | 图片校验 | 检查结果 |
| --- | --- | --- | --- | --- |
| `Tomato` | 13/13 | 原文哈希与消息来源匹配 | 路径与 SHA-256 匹配 | 通过 |
| `Night Sparks` | 13/13，含 1 个明确待补充 | 原文哈希与消息来源匹配 | 路径与 SHA-256 匹配 | 通过 |
| `Ginkgo & Fence` | 13/13 | 原文标题 `Maple & Fence` 已单独记录 | 路径与 SHA-256 匹配 | 通过 |
| `Henna Collage` | 13/13 | 原文与后续确认分层记录 | 路径与 SHA-256 匹配 | 通过 |
| `Lantern Tree` | 13/13 | 散文原文与消息来源匹配 | 路径与 SHA-256 匹配 | 通过 |

## 数据变化

- 正式条目总数保持 83。
- 带 `analysis` 的条目从 11 增至 16。
- 缺失 `analysis` 的条目从 72 减至 67，其中 5 条为本次完成。
- 本轮只修改 5 个目标条目的分析与来源字段；`Ginkgo & Fence` 另外补入原文已有的两条
  Echo candidates，`confirmed` 仍为空。

## 校验结果

- `check_analysis_recovery.py --entry <id>`：5 条逐条通过。
- `check_analysis_recovery.py`：8 条已登记草案全部通过；另有 2 条预期提示，表示尚未写入的
  `Frozen Water`、`Gulls Overhead` 没有当前 Echoes。
- `check_archive.py`：83 条、83 张图片、16 条带分析，无结构错误。
- `check_archive.py` 的 21 条 warning 均为历史原文某些字段较短，未为了消除 warning 而补写内容。
- `--strict-analysis` 仍会因其余 67 条未补录而失败，这是预期状态。

## 追溯与恢复

- `manifest.json` 中本轮 5 条均为 `archiveStatus: imported`。
- 第一轮 3 条仍为 `archiveStatus: pending`，未被本轮改动。
- 已保存的原始分析文件没有被覆盖。
- 若后续中断，可依据 `archiveStatus` 从第一个 `pending` 条目继续；`imported` 条目不重写。

## 结论

未发现原文信息丢失、重复条目、无效图片路径或跨条目回滚。正式结构验证通过。本轮停在 5 条，
等待项目所有者确认后再处理剩余记录。
