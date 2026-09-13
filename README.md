# qnap-user-manager

用于内部 QNAP 用户管理的 Python SDK。原生 HTTP 登录、会话检查与退出，以及用户、组、共享文件夹和共享权限管理均无需浏览器。运行时仅使用 Python 标准库，支持 Python 3.11+；Linux CI 已验证 Python 3.11、3.12、3.13；真实 NAS 回归使用 Python 3.12。

**固件边界：仅已验证 QTS 5.1.9.2954（build 20241120，TS-873）。** 不自动套用到其他 QTS 或 QuTS hero。CGI 属于固件实现接口，并非 QNAP 官方稳定 SDK。配额、文件级 ACL 和应用权限尚未验证。

## 安装

```sh
# 官方 PyPI
python -m pip install qnap-user-manager==0.4.0
qnap-manager --version
qnap-manager profiles
qnap-manager contracts
```

发行包名为 `qnap-user-manager`，Python 导入名为 `qnap_sdk`。

## 登录和查询

```python
from getpass import getpass
from qnap_sdk import QnapClient, DEFAULT_FIRMWARE, get_profile

client = QnapClient.authenticate(
    "https://nas.example.internal:443",
    DEFAULT_FIRMWARE,
    get_profile(),
    "manager",
    getpass("QNAP password: "),
    # ca_file="/path/to/internal-ca.pem",
)
try:
    client.check_session()
    for user in client.users.list_all():
        print(user.username, user.disabled)
finally:
    client.logout()
```

HTTPS 校验证书；自签名证书请配置 CA。仅明确需要明文 HTTP 时传 `allow_http=True`，密码 Base64 编码不提供加密。启用两步验证时，API 登录可传 `security_code`；CLI 尚未提供两步验证码参数。

`close()` 和上下文退出只清除本地 SID。`logout()` 请求 NAS 注销并验证旧 SID 失效；退出失败仍清除本地 SID并抛出错误。SID 过期或 HTTP 401/403 会触发 `SessionExpired`。写请求不会自动重试；返回后通过只读接口验证状态，密码变更按专用接口结果校验。

## 管理 API

| 资源 | 查询 | 创建 | 修改 | 删除 |
| --- | --- | --- | --- | --- |
| 用户 | `users.list/list_all/get/groups` | `users.create` | `users.update/disable/enable/reset_password` | `users.delete` |
| 组 | `groups.list/list_all/get/members` | `groups.create` | `groups.update/add_member/remove_member` | `groups.delete` |
| 共享目录 | `shares.list/list_all/get` | `shares.create` | `shares.update` | `shares.delete` |
| 共享权限 | `permissions.list/get` | `permissions.grant` | `permissions.set` | `permissions.revoke/delete` |

默认只读。操作正式资源必须在构造或认证时明确设置 `allow_writes=True`。测试模式可设置 `allow_test_writes=True`，限制资源名称及关联目标使用 `test_prefix`（默认 `sdk_test_`）。

```python
from qnap_sdk import Permission

# client 已在登录时开启 allow_writes=True；以下调用会改变 NAS 状态。
client.groups.create("research", description="Research team")
client.users.create("alice", getpass("Initial password: "), groups=("research",))
client.users.update("alice", description="Research member")
client.users.disable("alice")
client.users.reset_password("alice", getpass("New password: "))
client.users.enable("alice")
client.shares.create("research-data", volume=1, description="Research data")
client.shares.update("research-data", description="Team data", hidden=False)
client.permissions.grant("research", "research-data", Permission.READ_WRITE, subject_type="group")
client.permissions.revoke("research", "research-data", subject_type="group")
client.groups.remove_member("research", "alice")
client.users.delete("alice")
client.groups.delete("research")
client.shares.delete("research-data")  # 默认保留磁盘文件
```

`volume` 是设备的卷 ID，请先在目标设备确认。`shares.delete(delete_files=True)` 会同时删除目录数据。权限可选 `RO`、`RW`、`DENY`；撤销删除显式规则，继承权限可能仍有效，结果分别提供 `permission` 与 `effective_permission`。创建用户后添加组成员、创建组后添加成员属于多个独立调用，失败时可能留下部分结果；需查询状态并补偿。

密码创建与重置接受 1–64 个 UTF-8 字节，NAS 仍可能因自身密码策略拒绝。用户更新保留联系人信息，密码重置不改变禁用状态；共享目录更新保留未指定属性。

## 会话文件与 CLI

```sh
qnap-manager login --origin https://nas.example.internal --username manager --session-file ./nas-session.txt
qnap-manager logout --origin https://nas.example.internal --session-file ./nas-session.txt
```

密码隐藏输入，不存储；SID 文件按 POSIX 0600 原子保存，读取拒绝公开权限、符号链接及异常内容。不要提交会话文件。CLI 原始 `call` 接受隐藏 SID 输入，输出只包含操作状态，具体参数请见 `--help` 和固件契约。

## 开发、示例和验证

```sh
python -m pip install -e '.[dev]'
python tests/run_regression.py  # 阻止网络连接与子进程
python -m pytest --cov=qnap_sdk --cov-report=term-missing
python -m ruff check qnap_sdk tests examples
python -m build
python -m twine check dist/*
```

[开发指引](CONTRIBUTING.md)、[示例](examples/)、[开发关键记录](DEVELOPMENT_LOG.md)、[验证记录](docs/VALIDATION.md)、[兼容性](docs/COMPATIBILITY.md)。真实回归入口为 `tests/run_login_regression.py --help`，会登录并修改专用测试资源，仅用于获得授权的测试设备。

0.4.0 已通过 GitHub Actions Trusted Publishing 发布到 [PyPI](https://pypi.org/project/qnap-user-manager/0.4.0/)，并完成官方索引隔离安装验证。项目采用 [MIT 许可证](LICENSE)。

## 自动发布

GitHub Actions 自动运行离线 CI。配置 PyPI Trusted Publisher 后，发布正式 GitHub Release 可自动上传发行包；详见 [PyPI 发布指引](docs/PUBLISHING.md)。main 推送不会自动发布。
