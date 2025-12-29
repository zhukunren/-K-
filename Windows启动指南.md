# 股票预测系统 - Windows 启动指南

## 📋 快速启动

### 方式一：PowerShell 脚本（推荐）
```powershell
# 右键点击文件 "启动项目.ps1" -> 使用 PowerShell 运行
# 或在 PowerShell 中执行：
.\启动项目.ps1
```

### 方式二：批处理脚本
```batch
# 双击运行 "启动项目.bat"
# 或在命令行中执行：
启动项目.bat
```

## ✨ 新脚本功能特性

### 1. 自动环境检查
- ✅ 检查 Python、Node.js、npm 是否安装
- ✅ 检查虚拟环境是否存在
- ✅ 检查项目依赖是否安装

### 2. 智能依赖管理
- 🔧 自动创建 Python 虚拟环境（如果不存在）
- 📦 自动安装 Python 依赖（如果未安装）
- 📦 自动安装前端依赖（如果未安装）

### 3. 端口冲突处理
- 🔍 检查端口 8001（后端）和 5173（前端）是否被占用
- 🔄 自动释放被占用的端口
- 🧹 清理旧的进程

### 4. 友好的用户界面
- 🎨 彩色输出，易于阅读
- 📊 详细的进度提示
- ✅ 清晰的成功/失败状态
- 🌐 询问是否自动打开浏览器

### 5. 进程管理
- 💾 保存进程 PID 信息
- 🔧 支持优雅关闭服务
- 📝 详细的进程信息显示

## 🛑 停止服务

### PowerShell 停止脚本
```powershell
.\停止项目.ps1
```

### 批处理停止脚本
```batch
停止项目.bat
```

停止脚本会：
- 从 PID 文件读取进程信息并停止
- 检查端口占用并释放
- 清理所有相关进程
- 显示停止的进程数量

## 📍 访问地址

启动成功后，可以访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:5173 | Vue3 + Vite 开发服务器 |
| 后端 API | http://localhost:8001 | FastAPI 服务 |
| API 文档 | http://localhost:8001/docs | Swagger UI 接口文档 |

## 🔧 系统要求

- **Python**: 3.8 或更高版本
- **Node.js**: 14.0 或更高版本
- **npm**: 6.0 或更高版本
- **操作系统**: Windows 10/11

## 📦 依赖安装

如果需要手动安装依赖：

### 后端依赖
```bash
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 前端依赖
```bash
cd frontend
npm install
```

## 🐛 常见问题

### 1. PowerShell 执行策略错误
如果遇到 "无法加载文件，因为在此系统上禁止运行脚本" 错误：

```powershell
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. 端口被占用
脚本会自动处理端口冲突，如果仍然有问题，可以：
```powershell
# 手动查找并停止占用端口的进程
netstat -ano | findstr :8001
netstat -ano | findstr :5173
taskkill /F /PID <进程ID>
```

### 3. 依赖安装失败
- 检查网络连接
- 使用国内镜像源：
```bash
# Python
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# npm
npm install --registry=https://registry.npmmirror.com
```

## 📂 脚本文件说明

| 文件名 | 类型 | 说明 |
|--------|------|------|
| `启动项目.ps1` | PowerShell | 完整功能的启动脚本（推荐） |
| `启动项目.bat` | 批处理 | 批处理版本的启动脚本 |
| `停止项目.ps1` | PowerShell | 优雅停止所有服务 |
| `停止项目.bat` | 批处理 | 批处理版本的停止脚本 |
| `启动.ps1` | PowerShell | 原始的简单启动脚本 |

## 🎯 新旧脚本对比

| 特性 | 旧脚本 | 新脚本 |
|------|--------|--------|
| 环境检查 | ❌ | ✅ |
| 依赖自动安装 | ❌ | ✅ |
| 端口冲突处理 | 部分 | ✅ 完整 |
| 错误提示 | 简单 | ✅ 详细 |
| 彩色输出 | 基础 | ✅ 丰富 |
| 进程管理 | 基础 | ✅ 完善 |
| 自动打开浏览器 | ❌ | ✅ |
| 停止服务脚本 | ❌ | ✅ |

## 📝 更新日志

### v2.0 (2025-12-29)
- ✨ 新增完整的环境检查
- ✨ 新增依赖自动安装
- ✨ 改进端口冲突处理
- ✨ 添加停止服务脚本
- ✨ 优化用户界面和提示信息
- ✨ 添加自动打开浏览器功能
- ✨ 添加进程管理功能

## 📞 技术支持

如有问题，请检查：
1. Python 和 Node.js 是否正确安装
2. 网络连接是否正常
3. 查看启动过程中的错误提示
4. 检查 logs 目录中的日志文件
