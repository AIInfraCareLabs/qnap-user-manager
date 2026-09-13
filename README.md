# qnap-user-manager

English | [Simplified Chinese](README-zh_cn.md)

A Python SDK for internal QNAP administration. Native HTTP login, session checks and logout, as well as user, group, shared-folder and share-permission management, work without a browser. The runtime uses only the Python standard library and requires Python 3.11+. Linux CI verifies Python 3.11, 3.12 and 3.13; live NAS regression used Python 3.12.

**Verified firmware: QTS 5.1.9.2954 (build 20241120), on a TS-873.** Contracts are not automatically reused for other QTS versions or QuTS hero. These CGI endpoints are firmware implementation interfaces, not an official stable QNAP SDK. Quotas, file-level ACLs and application permissions remain unverified.

## Installation

```sh
# Official PyPI
python -m pip install qnap-user-manager==0.4.0
qnap-manager --version
qnap-manager profiles
qnap-manager contracts
```

The distribution name is `qnap-user-manager`; the Python import name is `qnap_sdk`.

## Login and queries

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

HTTPS validates certificates; supply a CA file for a self-signed certificate. Set `allow_http=True` only when plain HTTP is explicitly required. Base64 password encoding does not provide encryption. API authentication accepts `security_code` for two-step verification; the CLI does not yet expose that parameter.

`close()` and context-manager exit clear only the local SID. `logout()` asks the NAS to revoke the session and verifies that the old SID is rejected. A failed logout still clears the local SID and raises an error. An expired SID or HTTP 401/403 raises `SessionExpired`; 403 can also indicate insufficient authorization. Write requests are never automatically retried. Changes use read-only requests to verify the resulting state; password changes check the dedicated endpoint's result fields.

## Management API

| Resource | Read | Create | Update | Delete |
| --- | --- | --- | --- | --- |
| Users | `users.list/list_all/get/groups` | `users.create` | `users.update/disable/enable/reset_password` | `users.delete` |
| Groups | `groups.list/list_all/get/members` | `groups.create` | `groups.update/add_member/remove_member` | `groups.delete` |
| Shared folders | `shares.list/list_all/get` | `shares.create` | `shares.update` | `shares.delete` |
| Share permissions | `permissions.list/get` | `permissions.grant` | `permissions.set` | `permissions.revoke/delete` |

Clients are read-only by default. To change regular resources, explicitly set `allow_writes=True` when constructing or authenticating the client. Alternatively, `allow_test_writes=True` restricts resource names and related targets to `test_prefix`, which defaults to `sdk_test_`.

```python
from qnap_sdk import Permission

# Authenticate client with allow_writes=True before running these mutations.
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
client.shares.delete("research-data")  # Preserves files on disk by default.
```

`volume` is the device's volume ID; confirm it on the target NAS first. `shares.delete(delete_files=True)` also removes stored data. Permissions accept `RO`, `RW` or `DENY`. Revoking an explicit rule can leave inherited access in effect: results distinguish `permission` from `effective_permission`.

Creating a user and adding group memberships, or creating a group and adding members, involves separate calls. A failure can leave partial results; inspect the current state and apply compensation as needed.

User creation and password reset accept 1–64 UTF-8 bytes, subject to the NAS password policy. User updates preserve contact information, password reset preserves disabled state, and shared-folder updates preserve properties that were not explicitly changed.

## Session files and CLI

```sh
qnap-manager login --origin https://nas.example.internal --username manager --session-file ./nas-session.txt
qnap-manager logout --origin https://nas.example.internal --session-file ./nas-session.txt
```

Passwords are entered through a hidden prompt and are not stored. SID files are saved atomically with POSIX mode 0600. Loading rejects public permissions, symbolic links and invalid content. Do not commit session files. The raw CLI `call` command accepts a SID through hidden input and prints only operation status; see `--help` and the firmware contract for parameters.

## Development, examples and validation

```sh
python -m pip install -e '.[dev]'
python tests/run_regression.py  # Forbids network connections and subprocesses.
python -m pytest --cov=qnap_sdk --cov-report=term-missing
python -m ruff check qnap_sdk tests examples scripts
python -m build
python -m twine check dist/*
```

See the [documentation index](docs/README.md), [development guide](CONTRIBUTING.md), [examples](examples/), [development record](DEVELOPMENT_LOG.md), [validation record](docs/VALIDATION.md) and [compatibility notes](docs/COMPATIBILITY.md).

`tests/run_login_regression.py --help` describes live regression. It authenticates and changes dedicated test resources; run it only against an authorized test device.

Version 0.4.0 is published on [PyPI](https://pypi.org/project/qnap-user-manager/0.4.0/) through GitHub Actions Trusted Publishing, with official-index installation verified in a clean environment. The project uses the [MIT license](LICENSE).

## Automated publishing

GitHub Actions runs offline CI. With a PyPI Trusted Publisher configured, publishing an official GitHub Release uploads verified distributions automatically. See the [publishing guide](docs/PUBLISHING.md). Pushing `main` does not publish to PyPI.
