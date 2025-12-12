# SSHive - SSH连接管理工具

一个基于PyQt6开发的图形化SSH连接管理工具，提供直观的界面来管理和连接SSH服务器。

## 功能特性

- **主机管理**
  - 添加、编辑、删除SSH主机配置
  - 支持密码认证和密钥认证
  - 主机信息加密存储在SQLite数据库中

- **SSH连接**
  - 双击主机即可快速连接
  - 支持多标签页，同时连接多个主机
  - 实时终端交互，支持常用快捷键（Ctrl+C, Ctrl+D等）
  - 命令历史记录（上下箭头键）

- **用户界面**
  - 左侧主机列表，右侧终端界面
  - 支持主机搜索和过滤
  - 右键菜单快速操作
  - 暗色终端主题

## 安装

### 前置要求

- Python 3.13+
- uv包管理器

### 安装步骤

1. 克隆或下载项目

2. 使用uv安装依赖：
```bash
uv sync --index-url https://mirrors.aliyun.com/pypi/simple/
```

## 使用

### 启动应用

```bash
uv run python main.py
```

### 添加主机

1. 点击左上角"添加主机"按钮
2. 填写主机信息：
   - 名称：自定义主机名称
   - 主机地址：SSH服务器IP或域名
   - 端口：默认22
   - 用户名：SSH登录用户名
   - 认证方式：选择密码认证或密钥认证
   - 密码/私钥路径：根据认证方式填写
   - 描述：可选的备注信息
3. 点击"保存"

### 连接主机

- **双击**主机列表中的主机即可连接
- 或**右键点击**主机，选择"连接"

### 编辑/删除主机

- **右键点击**主机，选择"编辑"或"删除"

## 数据存储

- 主机配置存储在 `sshive.db` SQLite数据库中
- 密码使用Fernet对称加密存储
- 加密密钥保存在 `sshive.key` 文件中

**注意**：请妥善保管 `sshive.key` 文件，丢失将无法解密已保存的密码。

## 安全建议

1. 建议使用SSH密钥认证代替密码认证
2. 定期备份 `sshive.db` 和 `sshive.key` 文件
3. 不要将数据库和密钥文件提交到版本控制系统

## 项目结构

```
sshive/
├── main.py                 # 应用入口
├── main_window.py          # 主窗口
├── database.py             # 数据库管理
├── ssh_client.py           # SSH客户端
├── terminal_widget.py      # 终端组件
├── host_list_widget.py     # 主机列表组件
├── host_dialog.py          # 主机编辑对话框
├── pyproject.toml          # 项目配置
├── .gitignore              # Git忽略文件
└── README.md               # 项目说明
```

## 依赖库

- PyQt6 >= 6.6.0 - GUI框架
- paramiko >= 3.4.0 - SSH协议实现
- cryptography >= 41.0.0 - 密码加密

## 开发

使用uv进行开发：

```bash
# 安装依赖
uv sync

# 运行应用
uv run python main.py

# 添加新依赖
uv add package_name
```

## 许可证

本项目仅供学习和个人使用。

## 贡献

欢迎提交Issue和Pull Request！
