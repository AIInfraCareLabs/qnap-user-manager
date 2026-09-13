# Instructions for continued development

Read DEVELOPMENT_LOG.md, CONTRIBUTING.md and docs/VALIDATION.md before extending the project. Default tests must not connect to or change a NAS. Require an exact firmware match and evidence before marking an operation verified. Keep the bundled contract and discovery mirror consistent.

Do not read or print nas-session files, passwords, SIDs or raw HAR captures. Ask the user to authenticate through hidden input when needed. Determine live-test scope from the authorization already granted in the current conversation; do not ask again for existing authorization. Check resource collisions first and clean up resources created by the test in finally blocks. Publishing to a package index requires an explicit user instruction.

After changes, run offline regression, Ruff and applicable build/installation checks. Record key decisions, device versions, validation results and remaining work. Do not describe assumptions as verified facts.

Use the GitHub username puluto and private email 4004102+puluto@users.noreply.github.com for commits in this repository. Do not inherit a real name or company email from global Git configuration.

Default documentation is English. Keep README-zh_cn.md and docs/zh_cn/ synchronized with their English counterparts. Chinese README links must lead to Chinese guides; each translated guide should link back to its English counterpart.
