# HF Space Watchdog (GitHub Actions)

## 功能

每15分钟自动检查 HuggingFace Space (`avvnire/agent-data`) 的运行状态，发现被挤占（hardware=None）、503、RUNTIME_ERROR等异常时，自动触发Space强制重启。

**与本地机器完全脱钩**，跑在GitHub服务器上，24/7不间断。

## 配置步骤

### 1. 创建GitHub仓库

将本目录推送到GitHub（公开仓库免费无限分钟数）：

```bash
cd ~/Downloads/space-watchdog
git init
git add .
git commit -m "HF Space watchdog"
git remote add origin https://github.com/<你的用户名>/space-watchdog.git
git push -u origin main
```

### 2. 添加Secret

进入 GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret：

- Name: `HF_TOKEN`
- Value: 你的HuggingFace token（从 https://huggingface.co/settings/tokens 获取，需要write权限）

### 3. 启用Actions

进入 GitHub 仓库 → Settings → Actions → General → 确保选择 "Allow all actions"

### 4. 验证

- 进入 Actions 页面，应能看到 "HF Space Watchdog" workflow
- 点击 "Run workflow" 手动触发一次测试
- 之后每15分钟自动执行

## 修改检查频率

编辑 `.github/workflows/watchdog.yml` 中的 cron 表达式：
- `*/15 * * * *` → 每15分钟
- `*/30 * * * *` → 每30分钟
- `0 */1 * * *` → 每小时

## 费用

GitHub Actions 公开仓库完全免费，私有仓库每月2000分钟免费额度。
每15分钟跑一次 ≈ 96次/天 × ~30秒/次 ≈ 48分钟/天 ≈ 1440分钟/月，在免费额度内。
