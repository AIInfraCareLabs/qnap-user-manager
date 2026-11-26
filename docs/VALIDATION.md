# Validation record

English | [Simplified Chinese](zh_cn/VALIDATION.md) | [Documentation](README.md)

## Live device regression — 2026-09-13

Device: TS-873 / QTS 5.1.9.2954 build 20241120. Native HTTP transport, without a browser. Existing local reports confirm:

- Password login, SID checks, logout rejection of the old SID, relogin and saving a fresh session: passed.
- User, group and shared-folder CRUD; membership addition/removal: passed.
- User/group share permissions RO/RW/DENY and revocation: passed.
- Password reset, disable, preservation of disabled state and re-enable: passed.
- Test-resource cleanup and identity-baseline restoration: passed, with no cleanup errors.

Distribution and documentation work did not repeat remote mutations. These results do not establish compatibility with other firmware, QuTS hero or Windows, or verify real-device two-step authentication, quotas, file ACLs or application permissions.

## Offline and distribution validation

Default tests use synthetic identities, anonymized XML and injected transports. The offline runner forbids network connections and subprocesses. Tests cover resource lifecycles, silently ignored writes, pagination without progress, failure without retries, session expiration, safe parsing, private credential files and the CLI.

Initial 0.4.0 preparation passed 65 tests with 81% overall line coverage and 100% coverage for `session.py`. Ruff and Twine passed. A clean environment verified wheel imports, version, bundled contracts and CLI commands. The sdist was extracted, rebuilt and tested. Archives excluded sessions, HAR captures, caches, `work/` and `reports/`.

Release-gate tests subsequently increased the suite to 68 tests. Linux CI verified Python 3.11, 3.12 and 3.13, Ruff, wheel/sdist checks and isolated installation. Workflow syntax passed actionlint. The final workflow configuration passed [CI run 34766006491](https://github.com/AIInfraCareLabs/qnap-user-manager/actions/runs/34766006491). The `pypi` environment restricts deployment to `v*` tags.

Optional browser-bridge and dashboard coverage is lower than core SDK coverage. Coverage does not imply general firmware compatibility. Detailed local results remain in ignored `reports/` files.

## Official PyPI verification

[Publishing run 34766400639](https://github.com/AIInfraCareLabs/qnap-user-manager/actions/runs/34766400639) succeeded after retry. Version 0.4.0 was installed from the official PyPI index into a clean virtual environment. Version checks, bundled profiles and CLI `--version` / `profiles` / `contracts` all passed.

The local Python default CA configuration was incomplete, so installation verification used an explicit trusted certifi CA bundle. TLS verification remained enabled. Earlier notes about an unpublished package describe historical stages; 0.4.0 is now published.

## Documentation localization — 2026-09-14

All 20 Markdown documents passed checks for English defaults, local link targets and Chinese README routing. The rebuilt sdist contains the Chinese README and all translated guides; wheel metadata reads the English README. Offline regression still passes all 68 tests. Twine and release archive checks passed. These local builds are validation artifacts, not a replacement for published 0.4.0 files.

## Live write and pagination validation — 2026-11-26

Device: TS-873 / QTS 5.1.9.2954 build 20241120, matching the bundled profile exactly. Test users, groups and shared folders were created for the tests and removed afterwards; no existing data was modified. Final baseline: 3 users, 3 groups, 2 shared folders.

- Standard live regression (run before the membership-read change): all 24 checks passed with write readback (CRUD, membership, share properties, password reset, disable/enable and user/group permissions); `baseline_restored=true` and `cleanup_errors=[]`.
- Membership: with 11 test users in one group, `groups.members` and `Group.members()` returned all 11. The `lower`/`upper` parameters do not paginate membership strings. The structured `userroot` candidate user directory returned 1, 10 and 14 rows for `upper=1/10/100`. Adding and removing a member with 11 members succeeded. The ignored pagination parameters were removed from the profile and the two SDK membership readers. A post-change live check with a two-member group passed membership reads, add/remove and cleanup with the baseline restored.
- Shared folders: 11 test shares were created; together with 2 existing shares, `shares.list` without `lower`/`upper` returned `count=13` and 13 rows, and the SDK also returned 13. The endpoint does accept `[lower, upper)` (with 2 existing shares, `upper=1` returned 1). The bundled profile now declares `lower`/`upper`, so `Shares.list_all()` paginates; an offline test covers page boundaries. A default limit above 13 rows is still not established, but `list_all()` no longer relies on it.
- Cleanup: rapid consecutive user deletion can be silently ignored by the NAS `fork_del` path. The SDK reported an unconfirmed deletion instead of claiming success; spaced deletions with a longer verification timeout completed cleanup. Live cleanup scripts should space user deletions and verify the list.
- A read-only browser-session cross-check on QTS 5.2.11.3683 reproduced the membership behavior (full `ownUser`, paginated `userroot`) and showed that `users.list` honors `upper`; the dashboard had requested only the first page and now uses `list_all()`. This cross-check is not a compatibility claim for that firmware.

## Official PyPI verification — 0.5.0

Release `v0.5.0` was created at commit `559c0ec`. Publishing workflow run `45824925053` completed successfully. A clean Python 3.12 environment installed `qnap-user-manager==0.5.0` from the official PyPI index; CLI `--version`, `profiles`, `contracts`, package import and the bundled QTS 5.1.9.2954 profile all passed. The published artifacts correspond to the tagged commit.
