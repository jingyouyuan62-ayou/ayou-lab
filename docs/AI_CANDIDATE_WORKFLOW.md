# Ayou-Lab AI 候选图工作流

状态：已实现，等待 GitHub Actions Secret 配置、提交和推送后启用。

## 目标

每天自动产生恰好 3 个符合 Ayou-Lab Visual DNA 的公开领域候选。每个候选进入
GitHub Issue，项目所有者可以在手机上查看、批准或拒绝。批准后，工作流重新检查图片、
来源、授权、重复项和数据结构，并创建一个审核 PR。`main` 不会被自动覆盖。

这条流程不依赖 Codex Cloud、ChatGPT Work Cloud 或 Mac 保持开机。

## 流程

```text
每天 08:17（Asia/Shanghai）
  → GitHub Actions
  → 从 Wikimedia Commons 找 Public Domain / CC0 图片
  → 下载并压缩图片，以内嵌 JPEG 交给 DeepSeek 视觉分析
  → 创建 3 个 GitHub Issue
  → 手机添加 ayou-approved
  → 再次下载、解码、核对视觉内容和来源授权
  → 感知哈希去重
  → 写入 images/ 与 data/entries.json
  → 创建 PR
  → 人工合并后发布
```

## 来源与授权

第一版自动发现只使用 Wikimedia Commons 中明确标记为 Public Domain 或 CC0
的文件。Art Institute of Chicago 的许可核验代码保留，但其图片服务器目前会对
GitHub 托管运行器返回 Cloudflare 403，因此暂不参与自动发现。

不接受仅凭“网页上能打开”“Pinterest 上有转载”或模型猜测为可用的图片。候选 Issue
会显示来源页、作者、许可名称、许可链接和自动核验依据。

这不构成法律意见。若来源页的授权信息本身发生变化，以最终人工审核和 PR 合并为发布闸门。

## GitHub 标签

- `ayou-candidate`：由自动工作流创建的候选。
- `ayou-pending`：等待审核。
- `ayou-approved`：批准。添加此标签会触发导入工作流。
- `ayou-rejected`：人工拒绝；不会触发写入。
- `ayou-imported`：已经生成审核 PR。

当前流程只接受仓库所有者添加 `ayou-approved`；其他账户即使拥有标签权限也不会触发导入。

## 启用步骤

1. 在 GitHub 仓库 `Settings → Secrets and variables → Actions` 添加
   `DEEPSEEK_API_KEY`。
2. 确认 Actions 已启用。
3. 提交并推送本目录中的工作流、脚本和 `requirements.txt`。
4. 在 Actions 页面手动运行一次 `Daily visual candidates` 测试。
5. 检查是否创建 3 个 Issue，但不要立即批准，先核对预览和来源。
6. 如果仓库设置阻止 `GITHUB_TOKEN` 创建 Pull Request，在
   `Settings → Actions → General → Workflow permissions` 中允许 GitHub Actions
   创建 Pull Request；不要授予无关权限。

`DEEPSEEK_API_KEY` 只存放在 GitHub Actions Secrets，不写入仓库或 Issue。

## 工作流

- `.github/workflows/daily-visual-candidates.yml`
  - 每日定时和手动触发。
  - 需要 `issues: write`。
- `.github/workflows/approve-visual-candidate.yml`
  - 只响应对 `ayou-candidate` Issue 添加 `ayou-approved`。
  - 创建 `codex/import-candidate-*` 分支和 Pull Request。
  - 需要 `contents: write`、`issues: write`、`pull-requests: write`。
- `.github/workflows/validate-archive.yml`
  - 在 PR、`main` push 和手动运行时检查单元测试、历史恢复数据与 Archive 结构。

## 安全规则

- 未批准的候选图片不会写入仓库。
- `echoes.confirmed` 在批准前必须为空；AI 只能生成 `echoes.candidates`。
- 导入时重新测量 accent，不接受模型自报的颜色值。
- 导入时重新查询来源 API；授权已变化则停止。
- 导入时比较审批前后的 dHash；来源图片在审批后被替换则停止。
- 导入时重新检查内容裁剪后的 dHash；距离 12 或以下视为重复并停止。
- 候选分析使用 Actions 当场下载并压缩后的内嵌 JPEG；DeepSeek 不需要直接访问
  Art Institute 或 Wikimedia 图片服务器。
- 导入脚本只向 `entries.json` 末尾追加一条，不重排已有条目。
- 任何检查失败都删除新图片并恢复原始 `entries.json`。
- 工作流只创建 PR，不直接推送到 `main`。

## 本地检查

```bash
python3 -m unittest discover -s tests -p "test_*.py"
python3 scripts/check_analysis_recovery.py
python3 scripts/check_archive.py --strict-analysis
```

候选生成和导入涉及 JPEG、PNG、WebP/GIF 解码，CI 使用
`requirements.txt` 中锁定的 Pillow。当前本地 Python 没有安装 Pillow，但 macOS 会回退到
系统自带的 `sips`；本次本地单元测试已经覆盖图片解码、accent、dHash、自重复匹配和 JPEG
转换。GitHub Actions 的 Ubuntu 环境则使用 Pillow。

## 当前限制

- 这是候选发现与分析流水线，不是自动审美决策系统。
- 公共领域来源限制了候选范围，可能无法覆盖用户私人收集或社交平台图片。
- DeepSeek 的颜色、材质、空间判断仍需人工复核。
- 手机审核依赖 GitHub Mobile 或手机浏览器；不会把 Issue 自动同步到 Codex 聊天窗口。
- 用户批准 Issue 后只生成 PR；合并 PR 仍是发布前的最后检查。
