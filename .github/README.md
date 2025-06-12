# GitHub Actions 工作流说明

本项目包含多个优化的GitHub Actions工作流，提供自动化的构建、测试、部署和维护功能。

## 📋 工作流概览

### 1. 主要工作流

#### `deploy.yml` - 微信读书自动阅读
- **触发条件**: 定时任务（每天凌晨1点）、手动触发
- **功能**: 执行微信读书自动阅读任务
- **优化特性**:
  - ✅ Python依赖缓存
  - ✅ 智能参数生成
  - ✅ 多种执行模式
  - ✅ 详细的任务日志
  - ✅ 错误处理和重试

#### `test.yml` - 测试和验证
- **触发条件**: 代码推送、PR创建
- **功能**: 代码质量检查、单元测试、Docker构建测试
- **测试内容**:
  - 多Python版本兼容性测试
  - 代码风格检查
  - 模块导入测试
  - Docker镜像构建测试
  - 安全扫描

#### `release.yml` - 版本发布
- **触发条件**: 标签推送、手动触发
- **功能**: 自动构建和发布新版本
- **发布内容**:
  - GitHub Release
  - Docker镜像
  - 源码归档
  - 更新日志

### 2. 维护工作流

#### `dependency-update.yml` - 依赖更新
- **触发条件**: 每周一自动执行、手动触发
- **功能**: 检查并更新Python依赖包
- **自动化流程**:
  - 检测依赖更新
  - 运行兼容性测试
  - 创建更新PR

#### `cache-cleanup.yml` - 缓存清理
- **触发条件**: 每周日自动执行、手动触发
- **功能**: 清理过期的GitHub Actions缓存
- **清理策略**:
  - 删除7天前的缓存
  - 提供缓存统计信息

## 🚀 使用指南

### 手动触发任务

1. **执行阅读任务**:
   - 进入 Actions → 微信读书自动阅读
   - 点击 "Run workflow"
   - 可选择阅读时长、日志级别等参数

2. **发布新版本**:
   - 创建新的Git标签: `git tag v2.1.0`
   - 推送标签: `git push origin v2.1.0`
   - 或在Actions中手动触发

### 配置环境变量

在仓库的 Settings → Secrets and variables → Actions 中配置：

#### 必需的Secrets:
```
WXREAD_CURL_BASH     # 微信读书curl命令
PUSH_METHOD          # 推送方式 (pushplus/telegram/wxpusher)
PUSHPLUS_TOKEN       # PushPlus token (可选)
TELEGRAM_BOT_TOKEN   # Telegram bot token (可选)
TELEGRAM_CHAT_ID     # Telegram chat ID (可选)
WXPUSHER_SPT         # WxPusher token (可选)
```

#### 可选的Secrets:
```
HTTP_PROXY           # HTTP代理
HTTPS_PROXY          # HTTPS代理
DOCKER_USERNAME      # Docker Hub用户名
DOCKER_PASSWORD      # Docker Hub密码
```

## 🔧 优化特性

### 缓存策略
- **Python依赖缓存**: 使用`actions/cache@v3`缓存pip包
- **Docker层缓存**: 使用GitHub Actions缓存加速Docker构建
- **智能缓存键**: 基于requirements.txt哈希值的缓存键

### 性能优化
- **并行执行**: 多个测试任务并行运行
- **条件执行**: 根据条件跳过不必要的步骤
- **浅克隆**: 使用`fetch-depth: 1`加速代码检出

### 安全增强
- **最小权限**: 每个工作流只获得必需的权限
- **非root用户**: Docker容器使用非root用户运行
- **安全扫描**: 集成代码安全扫描工具

### 监控和通知
- **详细日志**: 每个步骤都有清晰的日志输出
- **状态通知**: 使用GitHub Annotations显示任务状态
- **失败处理**: 智能的错误处理和重试机制

## 📊 工作流状态

可以通过以下方式查看工作流状态：

1. **仓库主页**: 显示最新的工作流状态徽章
2. **Actions页面**: 查看详细的执行历史和日志
3. **通知**: 通过配置的推送方式接收任务通知

## 🛠️ 故障排除

### 常见问题

1. **依赖安装失败**:
   - 检查requirements.txt格式
   - 清理缓存后重试

2. **Docker构建失败**:
   - 检查Dockerfile语法
   - 验证基础镜像可用性

3. **推送通知失败**:
   - 验证推送配置和token
   - 检查网络连接

### 调试技巧

1. **启用调试日志**:
   - 设置`LOG_LEVEL`为`DEBUG`
   - 查看详细的执行日志

2. **本地测试**:
   - 使用`act`工具本地运行Actions
   - 在本地环境复现问题

3. **缓存问题**:
   - 手动清理缓存
   - 检查缓存键是否正确

## 📝 更新日志

- **v2.0.0**: 全面重构GitHub Actions工作流
  - 添加智能缓存机制
  - 优化性能和安全性
  - 增加自动化维护功能
  - 支持多种执行模式
