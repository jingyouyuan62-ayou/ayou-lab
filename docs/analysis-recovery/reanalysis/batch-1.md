# 原图补全批次 1

日期：2026-10-28
范围：3 条
方式：owner-authorized image reanalysis；一张原图只读取一次

| 条目 | 补全字段 | 结果 |
| --- | --- | --- |
| `Under the Canopy` | `uncertainty` | 通过 |
| `Soft Object` | `uncertainty` | 通过 |
| `Bridge & Sky` | `uncertainty` | 通过 |

保留原有 13 项中的其他判断、标题、category、accent 与 Echoes。新增内容只记录原图真实无法
确认的事项：

- `Under the Canopy`：真实树冠与平面作品翻拍/数字合成之间的媒介差异，以及红色簇、树种、
  地点和日期。
- `Soft Object`：兔形玩偶的身份与来源，以及实物拍摄或数字合成的判断限制。
- `Bridge & Sky`：桥名、地点、尺度、透视造成的夸张、树种和色彩处理。

三条均通过单条 `check_analysis_recovery.py`；原图、历史原文、旧映射、重分析前快照和
重分析草稿均保留。
