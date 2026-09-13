# QTS 5.1.9.2954 protocol notes

English | [Simplified Chinese](zh_cn/API_DISCOVERY.md) | [Documentation](README.md)

The discovery device was a TS-873, build 20241120. Parameters were identified in the downloaded QTS frontend and replayed through an independent Playwright session. Mutations used only the approved resources `sdk_test_0913_u`, `sdk_test_0913_g` and `sdk_test_0913_s`. Typed Python APIs subsequently checked fresh responses and resulting state.

| Resource or operation | CGI | Selection parameters |
| --- | --- | --- |
| User, group and share lists | priv/privRequest.cgi | subfunc=user / group / share |
| Create user | wizReq.cgi | wiz_func=user_create, action=add_user |
| Read/update user | priv/privWizard.cgi | wiz_func=user_edit, action=account_edit for updates |
| Delete user | priv/privRequest.cgi | subfunc=user, apply=1, fork_del=1, user_list |
| Create group | wizReq.cgi | wiz_func=user_group_create, action=add_group |
| Read/update group | priv/privWizard.cgi | wiz_func=group_user_detail, action=group_user_edit for updates |
| Group membership | priv/privWizard.cgi | wiz_func=group_user_edit, select_user / unselect_user |
| User's groups | priv/privWizard.cgi | wiz_func=user_group_edit |
| Delete group | priv/privRequest.cgi | subfunc=group, apply=1, group_list |
| Create share | wizReq.cgi | wiz_func=share_create, action=add_share |
| Read/update share | priv/privWizard.cgi | wiz_func=share_property, action=share_property for updates |
| Delete share | priv/privRequest.cgi | subfunc=share, apply=1, share_list, delsymboliconly |
| Read user/group share permissions | priv/privWizard.cgi | wiz_func=user_share_edit, userName / groupName |
| Update user/group share permissions | priv/privWizard.cgi | wiz_func=user_share_edit / group_share_edit, matching action |

All paths start with `/cgi-bin/`. Exact query/form placement, defaults, field mappings, success criteria and evidence are in the [bundled firmware contract](../qnap_sdk/profiles/qts_5_1_9_2954.json).

The user list's `user_enable=1` means enabled; the detail response's `chk_disable=1` means disabled. Disabling an account requires `a_enable`, `a_expire`, `a_uid` and date fields. Sending only `a_enable` did not confirm a successful change.

Permission updates use counts and indexed entries for `rd_share`, `rw_share`, `no_share` and `empty_share`. Empty lists do not replace permissions on other shares. Explicit `type` values R/W/I map to RO/RW/DENY; a missing value means no explicit rule. `preview` is returned separately and can differ from the explicit permission.

Some creation/update responses contain only `authPassed`, so successful authentication does not prove a successful mutation. The SDK reads details back to check names, descriptions or state. Membership changes read `ownUser`, permissions read `type`, and deletion checks the full list.

Live verification covered account enable/disable, descriptions, group membership, share descriptions/visibility/renaming, and all four permission states for users and groups. Test accounts, groups and the empty share were removed; the discovery baseline returned to 3 users, 3 groups and 2 shares. Original reports remain local; see the [validation summary](VALIDATION.md).

## Password reset

POST `/cgi-bin/priv/privWizard.cgi` with query parameters `wiz_func=user_password_edit`, `action=user_password_edit` and `sid`. Form fields are `username`, `password` (UTF-8 Base64), an empty `old_password`, and `need_check=no`. The operation requires administrator or otherwise authorized management privileges.

Both `func.userPasswordEdit.passwordCheck` and `func.userPasswordEdit.passwordChange` must be 0. Authentication success alone is insufficient; the SDK rejects failed or missing result fields.

The dedicated account was used to verify `reset_password`, `disable`, `enable`, and preservation of disabled state after resetting its password. The account was deleted afterward.

## Native authentication

Subsequent regression used the standard-library `urllib` transport directly for POST `authLogin.cgi`, SID checks and `authLogout.cgi`. Logout verification requires the old SID to be rejected. Direct CRUD regression confirmed cleanup and restoration of the identity baseline; see [VALIDATION.md](VALIDATION.md).
