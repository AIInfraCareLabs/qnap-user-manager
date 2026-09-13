# Publishing to PyPI through GitHub

English | [Simplified Chinese](zh_cn/PUBLISHING.md) | [Documentation](README.md)

Repository: [AIInfraCareLabs/qnap-user-manager](https://github.com/AIInfraCareLabs/qnap-user-manager). Distribution: `qnap-user-manager`. License: MIT.

## One-time account binding

Sign in to [PyPI Publishing](https://pypi.org/manage/account/publishing/) and add a GitHub Pending Publisher:

| Field | Value |
| --- | --- |
| PyPI project name | qnap-user-manager |
| Repository owner | AIInfraCareLabs |
| Repository name | qnap-user-manager |
| Workflow name | publish.yml |
| Environment name | pypi |

Use the filename `publish.yml`, not the workflow display name. The first upload creates the project; a Pending Publisher does not reserve its name. For an existing project owned by your account, add the same identity in that project's Publishing settings. The account must meet PyPI's email-verification and two-step-verification requirements.

The repository uses the `pypi` environment under Settings → Environments, restricted to `v*` tags. Only the publishing job receives `id-token: write`. Trusted Publishing uses temporary OIDC credentials; no PyPI API token or `PYPI_TOKEN` secret is required.

## Validation and release

Pushes to `main` and pull requests run CI. Actions → CI → Run workflow also runs validation without publishing.

CI runs offline regression, coverage reporting and Ruff on Python 3.11, 3.12 and 3.13. It builds wheel/sdist archives, verifies MIT licensing, bundled contracts and archive paths, then installs the wheel outside the source tree. It does not connect to a NAS.

After binding PyPI, publish an official GitHub Release with a tag matching `v<package version>`, such as `v0.4.0`. Verify that `main` CI passes first. The tagged commit must belong to `main` history, and versions in `pyproject.toml` and `qnap_sdk/__init__.py` must match.

The `release.published` event in `publish.yml` runs release checks and the complete CI workflow, then uploads that run's verified artifacts. Drafts and prereleases do not upload; ordinary `main` pushes do not upload either. Do not create an official Release before completing the binding.

After publication, check the [PyPI project](https://pypi.org/project/qnap-user-manager/) and install in a clean environment:

```sh
python -m pip install --index-url https://pypi.org/simple qnap-user-manager==0.4.0
qnap-manager --version
```

Do not upload the same version repeatedly. Subsequent releases need a new version and an updated changelog. Changing GitHub documentation does not overwrite README metadata in an existing PyPI release; that metadata changes with the next distribution release.

## TestPyPI and rollback

TestPyPI verification is recommended before production uploads. TestPyPI has separate accounts and publisher bindings; registering on PyPI does not register on TestPyPI. This project has not configured or uploaded to TestPyPI. To add that stage, create a `testpypi` environment and matching identity and verify test-index installation before production upload.

Review Actions logs after a failure. For identity errors, check owner, repository, workflow filename and environment instead of bypassing incorrect configuration with a token. Published files cannot be overwritten. Yank a bad release on PyPI and publish a corrected version; clients can temporarily pin an earlier release with `pip install qnap-user-manager==<previous-version>`.

## Publication history

[Version 0.4.0](https://pypi.org/project/qnap-user-manager/0.4.0/) is published. The GitHub Release is `v0.4.0`; publishing run `34766400639` succeeded after retry.

The first attempt reported `invalid-publisher`. The user's Pending Publisher screenshot showed matching fields, and retry succeeded without workflow changes. The initial error's exact cause remains undetermined. Official-index installation, version checks, bundled contracts and CLI verification passed.

For the next release, synchronize versions, push `main`, confirm successful CI, and publish the corresponding official Release.

## Official references

- [Creating a project with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [Publishing with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
