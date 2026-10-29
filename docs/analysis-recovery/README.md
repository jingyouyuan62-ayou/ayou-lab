# Ayou-Lab 历史分析恢复

状态：72 条历史恢复记录均已正式写入；其中 14 条在项目所有者授权后读取原图补全历史缺口。
当前 `data/entries.json` 为 83 条，83 条均带 `analysis`；未删除、覆盖或重命名图片。

2026-10-27 更新：项目所有者单独授权重新读取 `Night Sparks` 原图，为该条历史缺失的
`uncertainty` 完成正式完整分析。原历史原文、旧标准化记录和更新前正式分析快照均保留；
重分析来源与结果见
[`reanalysis/night-sparks-validation.md`](./reanalysis/night-sparks-validation.md)。

2026-10-27 批次 2 已从 manifest 第一个未完成项继续，完成 `Frozen Water`、`Cloud Line`、
`Gulls Overhead` 三条历史分析。每条的写入前快照、活跃映射、逐条检查和 manifest 进度见
[`batch-2.md`](./batch-2.md)。

2026-10-28 批次 3 完成 `Glittering Sea`、`Forest Railway`、`Fallen Leaves`、
`White Bells`、`Old Machine`。5 条均从历史原文恢复，未读取图片；过程与检查见
[`batch-3.md`](./batch-3.md)。

2026-10-28 批次 4 完成 `Above Jiufen`、`Green Courtyard`、`Snow Globes`、
`Backlit Reeds`、`Gulls & Water`。过程与检查见 [`batch-4.md`](./batch-4.md)。

2026-10-28 批次 5 完成 `Forest Walk`、`Magnolia`、`Yulan`、`Pasture & Forest`、
`Green Canal`。过程与检查见 [`batch-5.md`](./batch-5.md)。

2026-10-28 批次 6 完成 `Blue House`、`Cut Oranges`、`Osmanthus`。过程与检查见
[`batch-6.md`](./batch-6.md)。

2026-10-28 批次 7–16 继续处理剩余 46 条：32 条正式写入，14 条因历史原文缺少
`uncertainty` 等字段而标记为待重新分析。各批状态记录在 `manifest.json`，完整结论见
[`remaining-recovery.md`](./remaining-recovery.md)。

2026-10-28 重分析批次 1–5 随后补全上述 14 条。处理时每批 2–3 张，一次只读取一张原图；
没有显著疑点的 `uncertainty` 使用规范空值句。逐批记录见
[`reanalysis/batch-1.md`](./reanalysis/batch-1.md)、
[`reanalysis/batch-2.md`](./reanalysis/batch-2.md)、
[`reanalysis/batch-3.md`](./reanalysis/batch-3.md)、
[`reanalysis/batch-4.md`](./reanalysis/batch-4.md) 和
[`reanalysis/batch-5.md`](./reanalysis/batch-5.md)。

## 可访问性结论

- 当前 Archive 共 83 条，11 条已有完整 `analysis`，72 条待恢复。
- 扫描 47 个可访问的 Codex session 文件，包括普通 `.jsonl` 与 `.jsonl.zst` 历史记录。
- 72/72 均找到对应图片的历史用户可见分析，没有整条无法定位的条目。
- 其中 70 条的原文已有逐维字段；2 条（`Gulls Overhead`、`Lantern Tree`）把分析写在整段文字里，
  必须按原句拆分。
- 56MB 以上的大 session 没有一次性送入模型；本次只做本地文本索引与摘录。

主要历史来源批次：

| 时间 | 主要内容 |
| --- | --- |
| 2026-09-14 至 09-18 | 早期 19 条及相邻文件的多轮复核，包含旧 JSON 和逐项 Markdown |
| 2026-09-18 至 09-20 | 约 40 条图片的批量完整分析 |
| 2026-09-23 至 10-08 | `Sunlit Canopy`、`Long Afternoon`、`Lake Road`、`Purple Roses`、`Lilac Hydrangeas` |
| 2026-10-09 至 10-17 | 较新的逐维分析，以及 `Gulls Overhead`、`Lantern Tree` 的散文式报告 |

详细来源会随每条处理写入 `analysisSource`，不会把来源塞进 16 个分析字段。

## 第一轮样本（3 条）

| 条目 | 原始格式 | 标准映射结论 | 状态 |
| --- | --- | --- | --- |
| `Frozen Water` | 旧 JSON：对象、数组和布尔值 | 13 个字段可映射；标题、主类与强调色已按历史分析修订 | 已完成 |
| `Cloud Line` | Markdown 逐项字段 | 13 个字段和当前顶层元数据一致 | 可审阅 |
| `Gulls Overhead` | 整段散文 | `material` 已用原文已有观察完成映射 | 已完成 |

## 第二轮结构差异样本（5 条）

| 条目 | 原始格式与差异 | 关键验证点 | 状态 |
| --- | --- | --- | --- |
| `Tomato` | 旧 JSON；对象、数组、布尔值混排；原文没有 Echoes | 嵌套类型展开、`visualHierarchy` 映射、当前已确认 Echo 保留 | 已写入 |
| `Night Sparks` | Markdown；字段顺序不同；`content` 无字段名；缺 `uncertainty` | 缺失字段待补充、原候选与后续 confirmed 分层 | 已写入，1 项待补充 |
| `Ginkgo & Fence` | Markdown；原文标题仍为 `Maple & Fence`；树种判断不确定 | `sourceTitle` 追溯、后续确认保留、原文候选恢复 | 已写入 |
| `Henna Collage` | Markdown；Visual DNA 为主 strange / 次 color；个人 Echo 后续确认 | 保留确认前的视觉疑问，同时不把原 AI 候选冒充个人记忆 | 已写入 |
| `Lantern Tree` | 整段散文；13 维压缩在一个段落 | 按原句拆分、不得新增材质或地点判断 | 已写入 |

这 5 条已在正式试运行中写入；逐条成功条件和结果见
[`formal-trial-1.md`](./formal-trial-1.md)。

每个样本都有：

- `original/<id>.txt`：未经改写的当次助手分析。
- `normalized/<id>.json`：只做字段映射的候选补丁、来源信息和待确认项。
- `manifest.json`：消息来源、格式、状态和原文哈希的索引。

第二轮 5 条的逐项核对结论见
[`validation-round-2.md`](./validation-round-2.md)。
正式试运行前的七项条件与单条成功条件见
[`execution-preflight.md`](./execution-preflight.md)。

## 固定映射规则

1. `title`、`accent`、`echoes` 使用条目顶层现有值。
2. `content` 到 `uncertainty` 的 13 项写入 `analysis`，全部为 string。
3. 旧对象、数组、布尔值只在映射层展开为等价文字，原文保留旧类型。
4. `category` 仍只存一个主类；`analysis.dna` 可以保留主类、次类和置信度。
5. 原文没有覆盖的维度使用统一“待补充”句，不以 `note`、tags 或常识补写。
6. 历史冲突不自动修复；写入 `pending` / `mappingNotes`，等待所有者决定。
7. 每次只处理 1 条，原文落盘、映射、校验都通过后才追加到正式 JSON。
8. `analysisSource.sourceTitle` 保存分析当时的标题；条目后来改名时用它建立追溯。
9. 当前条目没有 `echoes`、但原文有 AI 候选时，候选只进
   `proposedPatch.echoes.candidates`；`confirmed` 必须保持空数组。

## 样本中的未决问题

- `Frozen Water`：项目所有者已确认按历史分析修订。当前正式条目为 `Horse in Snow` /
  `dream` / `#9FB6D4`，修订前状态与原写入前快照均保留。
- `Gulls Overhead`：原文没有独立材质判断。样本只把 `material` 标记为待补充。
- `Cloud Line`：当次原文把新疆写成候选，后续条目的 `echoes.confirmed` 已有“新疆”。
  规范化保留当前确认状态，不回退历史阶段。
- `Night Sparks`：原文没有 `uncertainty`，草案保留明确的待补充状态；原文的“跨年烟花”
  候选已在后续确认中被排除，不恢复。该历史状态保留；2026-10-27 已按项目所有者单独授权完成
  原图重分析并补入基于真实画面限制的 `uncertainty`。
- `Ginkgo & Fence`：原文标题是 `Maple & Fence`，且树种判断仍带保留语气。来源记录保留旧标题，
  当前标题使用后续确认的 `Ginkgo & Fence`，不把当次推测写成已确认事实。
- `Henna Collage`：原文对海娜位置有疑问，后续使用者已确认当前位置；草案同时保留历史疑问和
  当前 confirmed，不把两者混为同一时间层的判断。

## 用户确认后的批次方案

1. 以当前两轮共 8 条样本验收规则；如需要修正，只改映射规则和样本，不碰正式资料库。
2. 验收后每批 3–5 条；先重新做标题、历史别名和原文件对应检查，再从剩余记录中选合适的一组。
3. 每条先保存原文和哈希，再生成 normalized 草案；脚本和人工核对都通过后才写一条。
4. 每批结束运行 `python3 scripts/check_analysis_recovery.py` 与
   `python3 scripts/check_archive.py --strict-analysis`，再报告进度。
5. 任何 413、工具输出缺失或无法核对来源的情况立即停批，保留已完成文件，不连续重试。
