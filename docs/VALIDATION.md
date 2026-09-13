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
