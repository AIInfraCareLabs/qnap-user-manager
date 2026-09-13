# 开发指引

[English](../../CONTRIBUTING.md) | [中文文档目录](README.md) | [中文 README](../../README-zh_cn.md)


先阅读 README、DEVELOPMENT_LOG.md 与 docs/VALIDATION.md。不要读取或输出本地 nas-session 内容，也不要将原始 HAR、账号、密码或 SID 写入测试与发行包。

## 环境与检查

使用 Python 3.11+ 创建虚拟环境，执行 `python -m pip install -e '.[dev]'`。依次运行：

```sh
python tests/run_regression.py
python -m pytest --cov=qnap_sdk --cov-report=term-missing --cov-report=xml:reports/coverage.xml
python -m ruff format --check qnap_sdk tests examples scripts
python -m ruff check qnap_sdk tests examples scripts
python -m build
python -m twine check dist/*
```

离线 runner 禁止网络和子进程；默认 pytest 只发现 test_*.py，真实环境 runner 不会自动运行。新增测试必须覆盖行为、错误、状态读回或实际请求契约，不将远程写入放入普通测试。

## 架构与固件增强

- client.py：受限 origin、传输、响应解析、固件契约执行与写后验证。
- auth.py：原生认证、会话检查、NAS 注销与撤销确认。
- resources.py / models.py：公开资源 API、分页和模型。
- profile.py / profiles/*.json：随发行包安装的固件接口契约。
- session.py / cli.py：显式会话文件与命令行。
- browser_transport.py / dashboard.py：可选本地桥接工具；核心 SDK 不依赖浏览器。

包内 profiles JSON 为发行契约，discovery/endpoints.json 是兼容旧发现工具的镜像；修改现有契约时同步两者，测试检查一致性。新增固件使用独立 JSON 并在 profile.PROFILES 注册，禁止简单替换版本号。记录 method/path、query 与 form 参数位置、成功和失败字段、模型映射、证据与写后只读验证。

先分析获授权设备前端已使用的接口，再做只读确认；写入只针对明确授权的专用测试资源。新增用户、组、共享目录前检查冲突；记录基线并在 finally 中清理，只删除本次新建资源。失败后先核实状态，不盲目重发写请求。密码修改只能用合成测试账号验证。

本次已授权的历史测试范围与证据见开发记录；下一次按当次用户授权范围判断是否需要询问。需要管理员登录时请用户通过隐藏输入或独立登录窗口操作，聊天中不收集密码。

## 示例与发行验证

examples/read_only.py 演示登录查询；examples/session_usage.py 演示 SID 保存与退出。均需显式命令行参数，不在导入时联网。README 给出完整资源管理 API 示例。

构建后在项目目录以外创建干净环境，用 `pip install --no-deps /absolute/path/to/wheel`，检查导入、get_profile()、三个离线 CLI 命令，确认不需要 discovery/ 或开发工作区。解压 sdist 并重新构建也必须成功。检查归档内容，不包含 work/、reports/、会话、原始抓包与缓存。

版本号需同步 pyproject.toml 和 qnap_sdk/__init__.py，填写 CHANGELOG 和开发记录。项目使用 MIT 许可证；实际仓库 URL 由维护者确认，禁止填入虚构值。发布内部索引：`python -m twine upload --repository-url <approved-index> dist/*`；上传是单独授权的外部动作，0.4.0 已正式发布到 PyPI，后续使用 [发布指引](PUBLISHING.md)。

## 文档语言

默认文档使用英文，中文入口为 [README-zh_cn.md](../../README-zh_cn.md)，中文指南放在 docs/zh_cn/。维护时同步两种语言，保留 API 名称和示例，检查语言切换与相对链接。已发布 PyPI 版本的 README 元数据不能覆盖，会随下次版本发布更新。
