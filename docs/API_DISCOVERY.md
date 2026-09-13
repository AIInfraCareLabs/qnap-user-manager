# QTS 5.1.9.2954 协议记录

设备 TS-873，build 20241120。参数从设备下载的 QTS 前端中确认，再以独立 Playwright 浏览器会话重放。写请求只使用用户批准的 `sdk_test_0913_u`、`sdk_test_0913_g`、`sdk_test_0913_s` 专用资源，Python 类型接口随后验证新鲜响应和读回结果。

| 资源 | CGI | 选择参数 |
|---|---|---|
| 用户、组、共享列表 | priv/privRequest.cgi | subfunc=user / group / share |
| 用户创建 | wizReq.cgi | wiz_func=user_create, action=add_user |
| 用户详情、修改 | priv/privWizard.cgi | wiz_func=user_edit, action=account_edit（修改） |
| 用户删除 | priv/privRequest.cgi | subfunc=user, apply=1, fork_del=1, user_list |
| 组创建 | wizReq.cgi | wiz_func=user_group_create, action=add_group |
| 组详情、修改 | priv/privWizard.cgi | wiz_func=group_user_detail, action=group_user_edit（修改） |
| 组成员 | priv/privWizard.cgi | wiz_func=group_user_edit, select_user / unselect_user |
| 用户所在组 | priv/privWizard.cgi | wiz_func=user_group_edit |
| 组删除 | priv/privRequest.cgi | subfunc=group, apply=1, group_list |
| 共享创建 | wizReq.cgi | wiz_func=share_create, action=add_share |
| 共享详情、修改 | priv/privWizard.cgi | wiz_func=share_property, action=share_property（修改） |
| 共享删除 | priv/privRequest.cgi | subfunc=share, apply=1, share_list, delsymboliconly |
| 用户、组权限读取 | priv/privWizard.cgi | wiz_func=user_share_edit, userName / groupName |
| 用户、组权限修改 | priv/privWizard.cgi | wiz_func=user_share_edit / group_share_edit；同名 action |

所有路径以 `/cgi-bin/` 开头。准确的查询参数/表单位置、默认值、字段映射、成功判定与验证证据在 qnap_sdk/profiles/qts_5_1_9_2954.json 中。

用户列表 `user_enable=1` 表示启用，详情 `chk_disable=1` 表示禁用。禁用写入需要 a_enable、a_expire、a_uid 与日期字段；仅传 a_enable 无法确认禁用成功。

权限修改使用 rd_share、rw_share、no_share、empty_share 的长度和索引参数；空列表不覆盖其他共享目录。读取 `type` 的 R/W/I 分别对应 RO/RW/DENY，缺失表示无显式条目。preview 单独返回，可能与显式权限不同。

部分创建/修改响应只有 authPassed，没有操作结果码，因此认证成功不作为最终成功证据；SDK 使用详情读回检查名称、描述或状态。成员变更读回 ownUser，权限变更读回 type，删除读回全量列表。

SDK 验证了用户启用/禁用、描述修改、组成员增删、共享描述/隐藏/重命名，以及用户和组权限的四种状态。账号、组及专用空目录已删除，数量恢复到用户 3、组 3、共享目录 2。具体旧发现报告保留在本地；发行版摘要见 VALIDATION.md。

## 密码重置

POST `/cgi-bin/priv/privWizard.cgi`，查询参数 wiz_func=user_password_edit、action=user_password_edit 和 sid；表单 username、password（UTF-8 Base64）、old_password 为空、need_check=no。需要管理员或实际获准的管理权限。

实际响应结果在 `func.userPasswordEdit.passwordCheck` 与 `func.userPasswordEdit.passwordChange` 中；必须两者为 0，认证成功不能代替密码修改成功。SDK 拒绝失败/缺失结果字段。

已在专用账号上验证 SDK reset_password、disable、enable，以及禁用时重置后保持禁用；测试账号已删除。详情摘要见 VALIDATION.md。

## 原生认证

后续通过标准库 urllib 直接验证 POST authLogin.cgi、SID 检查与 authLogout.cgi；注销后再次检查旧 SID 必须被拒绝。直接 CRUD 回归确认资源与身份基线恢复，摘要见 VALIDATION.md。
