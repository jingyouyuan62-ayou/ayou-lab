# Night Sparks 原图重分析验证

日期：2026-10-27
条目：`fireworks-night` / `Night Sparks`
依据：项目所有者明确授权重新读取原图，并按照 `docs/IMAGE_ANALYSIS_SPEC.md` v2.1 完成完整分析。

## 保留的历史记录

- 原图：`images/fireworks-night.jpg`
- 原图 SHA-256：`6cf54733eeab0ae35167ff242bf8b9f1ada65f57297109dadab3e3a1415f241d`
- 历史原文：`docs/analysis-recovery/original/night-sparks.txt`
- 历史原文 SHA-256：`ef4a1146293d52b1019ab8530329159c48efdda88050085b8438d6d69bfc55a8`
- 旧标准化记录：`docs/analysis-recovery/normalized/night-sparks.json`
- 旧标准化记录 SHA-256：`a6fa086f5afc356ff548749c4a0364276892d1f45707d0332fb4f1346b611d6f`
- 更新前正式分析快照：
  `docs/analysis-recovery/reanalysis/night-sparks-before-2026-10-27.json`
- 新重分析记录：
  `docs/analysis-recovery/reanalysis/night-sparks-2026-10-27.json`

这些历史文件均未删除或覆盖。`analysisSource` 继续指向当次历史对话与历史原文；
原图重分析另由 `manifest.json` 的 `reanalyses` 记录追溯。

## 与历史分析的主要差异

- 核心视觉判断保持不变：夜景烟花、暖白主光、低处粉紫点缀、树冠暗框，以及主类
  `DREAM`、次类 `COLOR`。
- 保留了顶层标题 `Night Sparks`、`category: dream`、`accent: #201B21` 和使用者确认的
  Echo「大稻埕夏日烟花祭」。
- 将原来的简短构图描述展开为 16:9 双重点、负空间、树冠遮挡与视线路径。
- 将颜色从简单色名展开为主色、暖白高光和粉紫/蓝光辅助层，并保留原图实测色。
- 将“主体 → 爆点 → 树影”展开为带亮度、面积和位置依据的四步注意力顺序。
- 补足近景树冠、中景碎光、远景主烟花与暗天的空间分层，以及近远纹理差异。
- 未新增任何 AI Echo candidate，也未改变或扩大当前 confirmed Echo。

## uncertainty 最终内容

> 画面本身无法核实具体拍摄地点、真实拍摄日期、机位与设备；大稻埕夏日烟花祭来自使用者已
> 确认记录，不是图像本身的标识。多组烟花是在同一瞬间同时绽放、发生在很短的连续时间内，
> 还是由长曝光或后期叠加形成，单张图不足以判定；前景树种以及底部零散亮光的具体来源也无法
> 确认。

依据：单张 JPEG 没有可读地点/时间标识或可验证 EXIF 拍摄信息，画面也不能单独证明烟花时序、
拍摄参数、前景树种和底部光点来源。大稻埕名称只存在于使用者确认记录中。

## 验证结果

- 13 个 `analysis` 字段全部存在，且均为非空 string。
- 草稿与正式条目的 `analysis` 完全一致。
- `analysisSource` 与历史原文、旧标准化记录和更新前快照一致。
- 原图路径存在，SHA-256 匹配。
- 历史原文与旧标准化记录保留，SHA-256 匹配。
- 顶层 `title`、`category`、`accent`、`echoes` 未改变。
- `data/entries.json` 可解析；全库仍为 83 条、83 个引用图片、16 条带分析，无重复 id 或路径错误。
- Night Sparks 已不再产生“字段过短”或“uncertainty 待补充”警告。

自动检查：

```text
python3 -B scripts/check_analysis_recovery.py --entry fireworks-night
OK: 1 recovery sample(s), 1 reanalysis record(s), 0 warning(s)

python3 -B scripts/check_analysis_recovery.py
OK: 8 recovery sample(s), 1 reanalysis record(s), 1 warning(s)
WARN: frozen-water currently has no echoes; this is an existing, unrelated sample state.

python3 -B scripts/check_archive.py
OK: 14 warning(s)
```

结构检查通过。14 条 warning 均来自本轮未处理的其他历史条目，Night Sparks 不在 warning 列表。
本轮未修改网站设计，未处理其他历史记录，也未提交或推送 Git。
