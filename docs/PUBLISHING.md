# GitHub 自动发布到 PyPI

仓库：https://github.com/AIInfraCareLabs/qnap-user-manager
包名：qnap-user-manager；采用 MIT 许可证。

## 一次性账号绑定

登录 https://pypi.org/manage/account/publishing/ ，添加 GitHub Pending Publisher：

| 字段 | 值 |
| --- | --- |
| PyPI project name | qnap-user-manager |
| Repository owner | AIInfraCareLabs |
| Repository name | qnap-user-manager |
| Workflow name | publish.yml |
| Environment name | pypi |

这里填写文件名 publish.yml，不是工作流显示名称。首次发布时创建 PyPI 项目；Pending Publisher 不会保留包名。若项目已存在且属于你的账号，在该项目 Publishing 设置添加同一发布身份。账号还需满足 PyPI 的邮箱验证、两步验证等当前要求。

GitHub 仓库 Settings → Environments 中使用 pypi 环境。它限制部署到 v* 标签；只有发布任务拥有 id-token: write。Trusted Publishing 通过 OIDC 获取临时身份，不需 PyPI API Token，不要设置 PYPI_TOKEN secret。

## 验证与首次发布

推送 main / 提交 PR 时 CI 自动运行；也可在 Actions → CI → Run workflow 手动验证，不发布。

CI 对 Python 3.11、3.12、3.13 执行离线回归、覆盖率报告及 Ruff；构建 wheel/sdist，检查 MIT、固件契约、异常归档路径，再在源码目录之外安装验证。该过程不连接真实 NAS。

完成 PyPI 绑定后，发布 GitHub 正式 Release，标签必须是 v<版本号>，例如当前版本 v0.4.0。初次发布前先确保 main CI 已成功。标签对应提交必须属于 main 历史；pyproject.toml 和 qnap_sdk/__init__.py 版本必须一致。

publish.yml 的 release.published 事件启动版本检查、全套 CI，再下载该次构建产物上传。草稿和 prerelease 不上传；正常 main 推送也不上传。绑定前不要创建正式 Release。

发布成功后确认 https://pypi.org/project/qnap-user-manager/ ，在干净环境执行：

```sh
python -m pip install --index-url https://pypi.org/simple qnap-user-manager==0.4.0
qnap-manager --version
```

不要反复上传同一版本。发布后改动需要增加版本号，并更新 CHANGELOG。

## TestPyPI 与回退

首次生产发布前建议先在 TestPyPI 验证。TestPyPI 有独立账号和绑定，注册 PyPI 并不等于注册 TestPyPI；本次未替用户配置它，也未执行真实上传。如需增加该阶段，应新增 testpypi 环境和对应发布身份，在正式上传前确认测试索引安装成功。

发布异常先查看 Actions 日志。身份校验失败时核对 owner/repo/文件名/environment，避免用 Token 绕过配置错误。错误版本不能覆盖文件；使用 PyPI 的 yank 功能撤回该版本的默认选择，并发布修复版本。客户端临时固定上一版本：`pip install qnap-user-manager==<previous-version>`。

## 当前状态

仓库内的 CI 与发布配置已完成；GitHub 环境通过 API 配置。用户确认绑定后已创建 v0.4.0 正式 Release；首次运行 34766400639 在 OIDC 交换时报 invalid-publisher，尚未上传包。核对正式 PyPI 的绑定 owner/repo/workflow/environment 后，重跑失败任务：`gh run rerun 34766400639 --repo AIInfraCareLabs/qnap-user-manager --failed`，不要重新创建 Release 或移动标签。

官方参考：

- https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
- https://docs.pypi.org/trusted-publishers/using-a-publisher/
