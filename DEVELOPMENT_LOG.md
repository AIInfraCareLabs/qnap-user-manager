# Development record and continuation guide

English | [Simplified Chinese](docs/zh_cn/DEVELOPMENT_LOG.md)

## 2026-09-13: device contracts and resource management

Goal: an internal QNAP remote-user-management SDK. The authorized test device was a TS-873 / QTS 5.1.9.2954 build 20241120. Its address remains in local test configuration and is not a distribution default.

Initial discovery used an independent Playwright session to inspect frontend requests. Standard-library HTTP authentication and regression were added later, removing the browser requirement at runtime. Only discovered operations with evidence are marked `verified`; other firmware compatibility is not assumed.

The user authorized CRUD, membership, RO/RW/DENY, password-reset and account-disable tests on `sdk_test_0913_u`, `sdk_test_0913_g` and the empty `sdk_test_0913_s` share, followed by cleanup. Changes to other business resources were not authorized.

Key protocol findings:

- User-creation passwords use UTF-8 Base64; query/form placement differs between read and mutation endpoints.
- Membership updates use incremental selection parameters.
- Share properties `supportNameMangling` and `showSnapshots` use yes/no responses and 1/0 mutation values; unspecified properties must be preserved.
- Explicit permission `type` differs from effective `preview`; revocation can leave inherited access.
- Authentication success does not establish mutation success. Read back changes; poll reads for asynchronous deletion without resending the write.
- Password changes check both `passwordCheck` and `passwordChange`; resetting a password must not change enabled/disabled state.

## 2026-09-13: native live regression

Local `reports/live-auth-regression.json` at 08:41:28 UTC and `live-direct-regression.json` at 08:41:29 UTC confirmed success. Checks covered password login, SID validation, old-SID rejection after logout, relogin, CRUD, permissions, password reset, disabled state, logout and fresh-session persistence. Direct regression reported `baseline_restored=true` and `cleanup_errors=[]`.

Later distribution preparation reviewed these reports without repeating NAS mutations. The private session file is in the workspace's `work/qnap-discovery/nas-session.txt`; do not read, print, commit or package it. It can expire, requiring hidden-input authentication. Original reports stay local; see the [validation summary](docs/VALIDATION.md).

## 2026-09-13: 0.4.0 distribution preparation

Bundled the firmware contract in wheels; added `get_profile`, `available_profiles`, public version metadata and CLI profile/login/logout commands. Session persistence uses atomic writes, 0600 permission checks and rejection of symbolic links or invalid content. Improved response-object/size checks, authentication HTTP 401/403 handling and UTF-8 password-length validation.

Added CLI, private-session, native-transport-failure and stateful lifecycle tests. Prepared README, developer guides, examples and source manifests. Runtime dependencies remain empty. Initial validation passed 65 tests at 81% overall coverage, Ruff, Twine, isolated wheel installation and sdist rebuild/regression.

## MIT licensing, GitHub and commit identity

The user selected MIT and the public repository [AIInfraCareLabs/qnap-user-manager](https://github.com/AIInfraCareLabs/qnap-user-manager). Copyright and commit identity use the GitHub username `puluto`. Only source, anonymized contracts, documentation and tests are submitted; raw discovery reports and private sessions are excluded.

Early GitHub device authentication failed with EOF/timeouts. The user subsequently authenticated the system CLI through the keyring as `puluto`, with organization-admin permissions. The default branch is `main`. Do not submit credentials or local CLI downloads.

The user requested correction of published real-name author metadata. All four original commits, their authors/committers and copyright/documentation names were rewritten to the username, then pushed with an exact-SHA lease. Repository-local Git identity is fixed to `puluto <4004102+puluto@users.noreply.github.com>`. Do not inherit a real name or company email from global Git configuration. Normal development uses regular pushes; rewrite history only when explicitly requested, with a checked remote SHA.

## Automated publishing

Added `ci.yml` for offline tests on Python 3.11/3.12/3.13, Ruff, distributions, archive checks and isolated installation. `publish.yml` responds to official Release publication and uses OIDC to upload verified artifacts. Official Actions are pinned to stable-version SHAs; only the publishing job receives `id-token: write`.

Tags must match Python and package metadata versions. Archive validation rejects private directories and sessions. Added release-gate tests, raising the offline suite to 68 tests. Local regression, sdist regression and actionlint passed. Initial CI run `34765889598` and final workflow run `34766006491` passed. The `pypi` environment restricts deployment to `v*` tags. See the [publishing guide](docs/PUBLISHING.md).

## First PyPI attempt and successful retry

After the user confirmed binding, Release `v0.4.0` was created at commit `54392e4`. Run `34766400639` passed version checks, all Python tests and builds, but its initial OIDC exchange returned `invalid-publisher` before any upload.

Expected identity: `AIInfraCareLabs/qnap-user-manager`, workflow `publish.yml`, environment `pypi`, organization ID `289012739`. PyPI's official `GitHubPublisherMixin` looks up owner/name/owner ID/workflow/environment and treats `sub` as unchecked; the error was not established to be an immutable-subject incompatibility.

The user's Pending Publisher screenshot showed matching fields. Retrying failed jobs succeeded without workflow changes. Version 0.4.0 wheel/sdist files were uploaded to official PyPI, retaining the original Release/tag. The initial error's exact cause remains undetermined; do not record it as a fixed SDK defect.

A clean environment installed from `https://pypi.org/simple` using `--isolated`, `--no-cache-dir` and `--no-deps`. Version, bundled profile and CLI version/profiles/contracts checks passed. The local default Python CA setup was incomplete, so verification used an explicit trusted certifi bundle; TLS was not disabled. Never reuse a published version or commit account credentials.

## 2026-09-14: documentation localization

English is now the default for root documents and `docs/`. Chinese documentation is available through `README-zh_cn.md` and `docs/zh_cn/`, with language switches and links to matching-language guides. Both languages are included in the sdist; package metadata continues to read the English `README.md`.

Validation passed for all 20 Markdown documents: English defaults, local links and Chinese README routing. Source archives include both languages and wheel metadata uses the English README. All 68 offline tests, Twine and distribution-content checks passed.

This documentation update does not overwrite published 0.4.0 artifacts or create a Release. PyPI README metadata will use the English version in the next package release.

## Continue from here

1. Read this record, [CONTRIBUTING.md](CONTRIBUTING.md) and [VALIDATION.md](docs/VALIDATION.md); run offline checks first.
2. Keep `qnap_sdk/profiles/` and the `discovery/endpoints.json` mirror synchronized.
3. For a new firmware, collect anonymized evidence and add a separate profile; never change version labels to imply verification.
4. Candidate extensions: CLI two-step interaction, Windows testing, compensation for multi-call creation, file ACLs, application permissions and quota protocols. AD/LDAP needs a separate adapter. Linux Python 3.11/3.13 testing is already covered by CI.
5. Follow the existing publishing workflow and commit-identity policy. Record new decisions, versions, evidence, limitations and remaining work. Update English and Chinese documentation together.
