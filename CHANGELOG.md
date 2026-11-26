# Changelog

English | [Simplified Chinese](docs/zh_cn/CHANGELOG.md)

## Unreleased

- Make English the default documentation language and add a Chinese README and translated documentation tree.
- Add language navigation and include both languages in source distributions.
- Collect complete user, group and shared-folder inventories in the local dashboard instead of the first page.
- Remove `lower`/`upper` from group-membership and user-group reads and their readback verification; the NAS ignores them for these operations.
- Paginate shared-folder enumeration through the declared `[lower, upper)` contract.
- Record live write validation on QTS 5.1.9.2954 (24 checks) and the membership and shared-folder pagination findings.

## 0.4.0 — 2026-09-13

- Installable wheel and sdist with an exact bundled firmware contract and public profile loader.
- Native login, session checks, verified logout and private SID files; CLI login/logout and contract queries.
- User, group, shared-folder and share-permission CRUD, membership changes, password reset and disable/enable.
- Mutation readback, separate explicit/inherited permissions, preservation of unchanged properties and no automatic write retries.
- Offline regression, package-installation verification, development records and examples.

Only QTS 5.1.9.2954 is live-verified. Version 0.4.0 is published on PyPI.
