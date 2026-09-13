# Compatibility

English | [Simplified Chinese](zh_cn/COMPATIBILITY.md) | [Documentation](README.md)

Live verification covers only TS-873 / QTS 5.1.9.2954, build 20241120. The client requires an exact firmware/profile match. Matching a version does not mean another device has been tested.

Discovery used an independent Playwright context. Subsequent native HTTP login, session management and resource regression passed without a browser. Direct HTTPS, other device models or firmware, and QuTS hero have not been verified against real devices.

Supported operations concern local users, groups, top-level shared folders and explicit share permissions. AD/LDAP, file-level or Windows ACLs, application permissions, quotas and scheduled account expiration are outside the verified scope.

Discovery records parameter placement, contracts and response hashes; credentials are excluded from deliverables. New adapters need separate firmware profiles and live evidence. Do not mark guessed parameters verified.

Live testing also covers administrator password reset, disable/enable and preservation of disabled state after resetting a password. Actual SMB authentication and disconnection of active sessions remain untested.

Linux CI verifies Python 3.11, 3.12 and 3.13. Live NAS regression used Python 3.12. Windows behavior has not been verified.
