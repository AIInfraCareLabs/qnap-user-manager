# 开发关键记录与续开发入口

## 2026-09-13：设备契约与资源管理

目标：内部 QNAP 远程用户管理 SDK。授权测试设备为 TS-873 / QTS 5.1.9.2954 build 20241120；设备地址保留在本地实测工具配置中，不作为发行默认值。

最初使用独立 Playwright 会话分析前端请求。随后补齐标准库 HTTP 认证与回归，运行时无需浏览器。只将发现且有证据的操作标为 verified，不推断其他固件兼容性。

用户授权在专用 sdk_test_0913_u 用户、sdk_test_0913_g 组和 sdk_test_0913_s 空目录上做 CRUD、成员、RO/RW/DENY、密码重置及禁用测试，结束删除测试资源。未授权修改其他业务资源。

关键协议细节：用户创建密码为 UTF-8 Base64；查询与修改 CGI 的 query/form 位置不同。组成员通过增量选择参数修改。共享属性 supportNameMangling / showSnapshots 是 yes/no 字符串，写入需转换 1/0，并保留未指定属性。权限显式 type 与有效 preview 必须分开，撤销规则可能留下继承访问。认证成功不能代表写操作生效，修改后需查询验证；异步删除仅轮询读操作，不重发写请求。密码专用结果同时检查 passwordCheck 与 passwordChange；重置不带启用字段。

## 2026-09-13：原生真实回归完成

本地 reports/live-auth-regression.json（08:41:28 UTC）与 live-direct-regression.json（08:41:29 UTC）确认通过。涵盖密码登录、SID 检查、注销后旧 SID 被拒绝、重新登录、CRUD/权限/密码/禁用、退出及生成新会话。直接回归 baseline_restored=true、cleanup_errors=[]。本次发行整理读取既有结果，未重新对 NAS 发起写操作。

私人会话在工作区 work/qnap-discovery/nas-session.txt；不得读取、打印、提交或打包。SID可能过期；需要时重新使用隐藏输入登录。原始报告留在本地，不收入发布包；脱敏摘要见 docs/VALIDATION.md。

## 2026-09-13：0.4.0 发行准备

将固件契约随 wheel 打包；新增 get_profile/available_profiles、公开版本与 CLI profiles/login/logout。会话文件采用原子写入与 0600 校验，拒绝符号链接和异常内容。完善响应对象/大小校验、认证 HTTP 401/403 清会话和密码 UTF-8 长度检查。

新增离线 CLI、私密会话、原生传输失败与状态化资源生命周期测试；补充 README、开发指引、示例、源码包清单。运行时依赖为空。最终离线 65 项测试通过，总覆盖率 81%；Ruff、Twine、干净环境 wheel 安装与 sdist 重建/回归通过。发行准备不包含索引上传，现已按用户指令选择 MIT 许可证，仓库为 https://github.com/AIInfraCareLabs/qnap-user-manager。

## 下次继续

1. 读取本文、CONTRIBUTING.md 和 docs/VALIDATION.md，先运行离线回归与质量检查。
2. 公开固件契约位于 qnap_sdk/profiles/，discovery/endpoints.json 为镜像，保持一致。
3. 增强真实新固件支持时先采集脱敏证据，新增独立 profile；不要修改版本标识伪造兼容。
4. 优先候选：CLI 两步验证交互、Python 3.11/3.13 和 Windows 实测、创建资源多步骤补偿、细粒度文件 ACL 与应用权限、配额协议验证；AD/LDAP 需独立适配，不混入本地用户假设。
5. 项目采用 MIT，实际 Git remote 使用 AIInfraCareLabs/qnap-user-manager；设置后补充真实元数据、CI 与索引发布流程。保持新增功能与证据配套，记录版本、测试、限制和未完成项。

## 2026-09-13：MIT 与 GitHub 提交准备

用户授权 MIT 许可及提交 GitHub。版权与提交身份统一使用 GitHub 用户名 puluto，加入 LICENSE、SPDX MIT 包元数据与发行许可证文件。用户已指定 AIInfraCareLabs 组织及公开仓库，仓库名使用 qnap-user-manager。仅提交源码、脱敏契约、文档和测试，原始发现报告与本地会话不提交。

GitHub 早期设备授权连接曾因 EOF / 超时失败。用户随后完成系统登录，账号 puluto 通过钥匙串认证，已确认组织管理员权限；公开目标为 https://github.com/AIInfraCareLabs/qnap-user-manager，分支 main。系统 gh 可用；不会提交凭据或本地 CLI 文件。后续增强先检查远程历史并正常推送；仅用户明确要求修正历史时使用带明确远程 SHA 校验的 force-with-lease。

## 提交身份约定

本仓库 author / committer 使用 puluto，邮箱使用 4004102+puluto@users.noreply.github.com；本地仓库 Git 配置已固定。用户要求修正已发布记录，四条历史提交的作者、提交者及版权/文档姓名已统一为用户名。后续不得使用系统全局真实姓名或公司邮箱提交本项目。

## 2026-09-13：自动发布配置

新增 ci.yml（Python 3.11/3.12/3.13 离线测试、Ruff、构建、发行检查及隔离安装）与 publish.yml（正式 Release 触发，通过 OIDC 上传本次已验证产物）。Actions 固定官方版本 SHA；只在发布任务授予 id-token: write。版本标签必须与 Python/metadata 一致，发行扫描拒绝私人目录和会话。用户名与隐私邮箱约定继续有效。PyPI Trusted Publisher 绑定需用户在注册账号中完成，字段见 docs/PUBLISHING.md；本次配置不触发正式上传。

配置验证：本地 68 项测试、源码包内离线回归、发行检查及 actionlint 全部通过；GitHub CI 34765889598 的三个 Python 版本和构建任务成功。已配置 pypi 环境的 v* 标签限制。PyPI 页面已请求打开，需用户按发布指引添加 Pending Publisher。为避免新工作流沿用弃用运行时，官方 Actions 已升级到当前稳定版本的固定 SHA。
