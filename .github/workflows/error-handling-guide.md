# GitHub Actions 错误处理指南

本文档说明了项目中GitHub Actions工作流的错误处理策略，确保所有流程都能优雅地处理错误，避免不必要的红色失败状态。

## 🎯 错误处理原则

### 1. 优雅降级
- 非关键步骤失败不应导致整个工作流失败
- 提供fallback机制和替代方案
- 使用`continue-on-error: true`处理可选步骤

### 2. 智能重试
- 网络相关操作自动重试
- 使用指数退避策略
- 设置合理的重试次数和超时时间

### 3. 条件执行
- 使用`if`条件控制步骤执行
- 检查前置条件和依赖
- 避免在缺少必要条件时执行步骤

### 4. 详细日志
- 记录错误原因和上下文
- 提供调试信息
- 使用统一的日志格式

## 🔧 实施策略

### 关键步骤 vs 可选步骤

#### 关键步骤（必须成功）
- 代码检出
- 基础环境设置
- 核心业务逻辑

#### 可选步骤（可以失败）
- 缓存操作
- 代码风格检查
- 性能测试
- 通知发送

### 错误处理模式

#### 1. 基础错误处理
```yaml
- name: 可选步骤
  continue-on-error: true
  run: |
    command || echo "⚠️ 命令失败，但继续执行"
```

#### 2. 条件执行
```yaml
- name: 依赖步骤
  if: steps.previous.outcome == 'success'
  run: command
```

#### 3. 重试机制
```yaml
- name: 网络操作
  run: |
    RETRY_COUNT=0
    MAX_RETRIES=3
    
    while [ $RETRY_COUNT -le $MAX_RETRIES ]; do
      if command; then
        break
      fi
      RETRY_COUNT=$((RETRY_COUNT + 1))
      sleep $((RETRY_COUNT * 2))
    done
```

#### 4. Fallback机制
```yaml
- name: 主要操作
  run: |
    primary_command || {
      echo "⚠️ 主要操作失败，尝试备用方案"
      fallback_command || echo "❌ 备用方案也失败"
    }
```

## 📋 工作流特定策略

### deploy.yml (主要阅读任务)
- **网络配置**: `continue-on-error: true`
- **依赖安装**: 多级fallback
- **阅读任务**: 重试机制 + 优雅失败
- **结果报告**: 总是执行

### test.yml (测试和验证)
- **代码检查**: `continue-on-error: true`
- **单元测试**: 允许部分失败
- **Docker构建**: 独立执行，不依赖测试结果
- **安全扫描**: 可选步骤

### release.yml (版本发布)
- **构建包**: `continue-on-error: true`
- **Docker登录**: 条件执行（检查secrets）
- **镜像推送**: 依赖登录成功
- **Release创建**: 核心步骤，必须成功

### dependency-update.yml (依赖更新)
- **工具安装**: `continue-on-error: true`
- **更新检查**: 完整错误处理
- **测试**: 允许失败但记录
- **PR创建**: 条件执行

### cache-cleanup.yml (缓存清理)
- **所有步骤**: `continue-on-error: true`
- **API调用**: try-catch包装
- **统计**: 独立执行

## 🚨 常见错误场景

### 1. 网络问题
```yaml
- name: 网络操作
  continue-on-error: true
  run: |
    if ! ping -c 3 example.com; then
      echo "⚠️ 网络连接问题，使用离线模式"
      export OFFLINE_MODE=true
    fi
```

### 2. 依赖缺失
```yaml
- name: 可选依赖
  run: |
    if command -v optional_tool; then
      optional_tool --action
    else
      echo "⚠️ 可选工具未安装，跳过相关操作"
    fi
```

### 3. 权限问题
```yaml
- name: 权限敏感操作
  if: secrets.TOKEN != ''
  continue-on-error: true
  run: |
    if [ -n "$TOKEN" ]; then
      authenticated_operation
    else
      echo "⚠️ 认证信息缺失，跳过操作"
    fi
```

### 4. 资源限制
```yaml
- name: 资源密集操作
  timeout-minutes: 30
  continue-on-error: true
  run: |
    timeout 1800 resource_intensive_command || {
      echo "⚠️ 操作超时，但工作流继续"
      exit 0
    }
```

## 📊 监控和通知

### 状态检查
```yaml
- name: 工作流状态总结
  if: always()
  run: |
    if [ "${{ job.status }}" = "success" ]; then
      echo "::notice title=工作流完成::✅ 所有步骤执行完成"
    else
      echo "::warning title=工作流警告::⚠️ 部分步骤失败，但工作流完成"
    fi
```

### 错误通知
```yaml
- name: 错误通知
  if: failure()
  continue-on-error: true
  run: |
    echo "::error title=工作流失败::❌ 关键步骤失败"
    # 发送通知逻辑
```

## 🔍 调试技巧

### 1. 启用调试模式
在仓库设置中添加secret：`ACTIONS_STEP_DEBUG=true`

### 2. 详细日志
```yaml
- name: 调试信息
  if: env.DEBUG == 'true'
  run: |
    echo "🔍 调试信息:"
    env | sort
    ls -la
```

### 3. 条件调试
```yaml
- name: 条件调试
  if: failure()
  run: |
    echo "🔍 失败时的环境信息:"
    # 收集调试信息
```

## ✅ 最佳实践总结

1. **预防性错误处理**: 在问题发生前就考虑可能的失败场景
2. **分层错误处理**: 不同级别的错误采用不同的处理策略
3. **用户友好**: 错误信息要清晰、可操作
4. **监控友好**: 便于后续分析和改进
5. **文档化**: 记录错误处理的决策和原因

通过这些策略，确保GitHub Actions工作流既稳定又用户友好，避免不必要的红色失败状态。
