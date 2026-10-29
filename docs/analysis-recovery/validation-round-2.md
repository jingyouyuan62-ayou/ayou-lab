# 第二轮历史分析标准化验证

验证日期：2026-10-27
范围：5 条原始历史分析及其独立标准化草案
正式数据：未修改 `data/entries.json`，未重新看图

## 1. Tomato

- 原始分析：`original/tomato.txt`
- 标准化草案：`normalized/tomato.json`
- 原始格式：`structured_json`
- 结构差异：嵌套 color / typography / dna 对象、interaction 数组、`visualHierarchy`，且原文没有 Echoes。
- 信息遗漏：未发现；原文的 `implementationHints` 不属于 16 项分析，完整保留在原文文件中并在映射说明中登记。
- 判断改变：未发现；Visual DNA 仍是 strange + color，现有 category 保持 strange。
- 新增内容：没有新增观察；只将对象和数组展开成等价文字。
- 字段映射：`visualHierarchy → hierarchy`；其余字段原位或类型规范化。
- 来源追溯：session、message、原文路径、SHA-256 和 `sourceTitle` 均已记录。
- Echoes：原文没有 Echoes；当前 confirmed「Matisse, La Danse」来自后续使用者确认，原样保留，未伪装成当次分析结果。
- 验证结果：通过，`ready_for_review`。

## 2. Night Sparks

- 原始分析：`original/night-sparks.txt`
- 标准化草案：`normalized/night-sparks.json`
- 原始格式：`structured_markdown`
- 结构差异：开头是未标字段名的“画面”段落；字段顺序与正式结构不同；原文完全缺少 `uncertainty`。
- 信息遗漏：没有遗漏已有判断；缺失的 `uncertainty` 明确保留为待补充。
- 判断改变：未发现；Visual DNA 仍是 dream + color。
- 新增内容：只增加了结构规范和待补充说明，没有推测地点、拍摄参数或不确定项。
- 字段映射：未命名的画面段映射到 `content`；其余字段按原名映射，Echoes 留在顶层。
- 来源追溯：session、message、原文路径、SHA-256 和 `sourceTitle` 均已记录。
- Echoes：原文候选为「夏日祭 / 花火大会」「跨年烟花」；当前使用者确认的是「大稻埕夏日烟花祭」。标准化保留当前 confirmed，不恢复后来已被排除的跨年候选。
- 验证结果：通过结构验证，但等待确认是否接受 `uncertainty` 的明确待补充句；`needs_owner_confirmation`。

## 3. Ginkgo & Fence

- 原始分析：`original/ginkgo-fence.txt`
- 标准化草案：`normalized/ginkgo-fence.json`
- 原始格式：`structured_markdown`
- 结构差异：分析当时标题为 `Maple & Fence`；树种识别带明确不确定性；当前条目已经改名。
- 信息遗漏：未发现；原文的疑问、构图、颜色、材质、空间和 Echoes 候选均有去向。
- 判断改变：没有把原文的“更像银杏，不太像枫树”改写成确定句；`uncertainty` 同时记录当次疑问和后续确认。
- 新增内容：没有新增画面事实；只记录后来确实发生过的改名与确认。
- 字段映射：开头画面段映射到 `content`；其余字段按原名映射。
- 来源追溯：`sourceTitle` 保存了分析当时的 `Maple & Fence`；当前 title 保持 `Ginkgo & Fence`。
- Echoes：当前条目没有 Echoes；原文两个 AI 候选只恢复到 `proposedPatch.echoes.candidates`，confirmed 仍为空。
- 验证结果：通过，`ready_for_review`。

## 4. Henna Collage

- 原始分析：`original/henna-collage.txt`
- 标准化草案：`normalized/henna-collage.json`
- 原始格式：`structured_markdown`
- 结构差异：Visual DNA 为主 strange、次 color；原文 Echoes 只有 AI 候选；海娜位置在原文中尚未确认。
- 信息遗漏：未发现；原文画面、拼贴层次、颜色、材质、交互和疑问均保留。
- 判断改变：原文的保留语气没有被改成确定视觉事实；后续使用者确认只记录在 `uncertainty` 的已解决说明和当前 confirmed 中。
- 新增内容：没有增加新的视觉描述；只明确区分“当次疑问”和“后续确认”。
- 字段映射：画面段映射到 `content`；`spatialDepth` 明确写成扁平拼贴；其他字段按原名映射。
- 来源追溯：session、message、原文路径、SHA-256 和 `sourceTitle` 均已记录。
- Echoes：原文 AI candidates 不回填；当前 confirmed 的个人海娜纹身信息原样保留。
- 验证结果：通过，`ready_for_review`。

## 5. Lantern Tree

- 原始分析：`original/lantern-tree.txt`
- 标准化草案：`normalized/lantern-tree.json`
- 原始格式：`dense_prose`
- 结构差异：13 个维度压缩在同一条观察段落里，没有逐项字段标签。
- 信息遗漏：未发现；尺寸、灯杆、灯罩、叶色、虚实层次、情绪、风格、交互与地点疑点均有对应字段。
- 判断改变：未发现；主类仍为 DREAM。
- 新增内容：没有增加地点、城市、树种或灯罩数量；只将原句按维度拆开。
- 字段映射：按原句语义直接拆分；`material` 只保留原文明确写出的“灯杆表面有金属粗糙感”，其他材质标记为无法进一步确认。
- 来源追溯：session、message、原文路径、SHA-256 和 `sourceTitle` 均已记录。
- Echoes：当前 candidate 原样保留；没有把原文的“欧式街灯、公园夜路、旧照片”升级成确认项。
- 验证结果：通过，`ready_for_review`。

## 本轮发现

1. **标题会变，来源必须保存分析当时的标题。** `Ginkgo & Fence` 的原文标题是 `Maple & Fence`；只存当前 title 会切断追溯。因此已将 `sourceTitle` 加入 `analysisSource`，映射版本升级为 `2026-10-26.v2.1`。
2. **“缺字段”不能靠常识补齐。** `Night Sparks` 原文没有 uncertainty，只能保留待补充状态。
3. **后续用户确认不能倒写进当次视觉分析。** `Henna Collage` 的疑问和后续确认必须分层记录。
4. **当前 Echoes 是权威状态。** 已被后续确认或排除的候选不能机械恢复；原文候选留在原始文件，必要时写入 `mappingNotes`。
5. **完全缺 Echoes 时也只恢复 AI candidates。** `Ginkgo & Fence` 的候选可以恢复，但 confirmed 必须是空数组。
6. **散文分析只能拆句，不能重写。** `Lantern Tree` 的标准化不得顺手补充材质、地点或视觉关系。
7. **16 项之外的旧字段不能丢。** `implementationHints` 不融入正式 13 字段，但完整保留在原始文件中，并在映射说明中登记。

## 结论

5 条均可追溯到原始历史分析，未发现视觉判断被擅自改变或新增画面外事实。除 `Night Sparks` 的
`uncertainty` 待补充需要确认外，其余 4 条可以进入下一轮审阅。正式写入仍需等待项目所有者确认。
