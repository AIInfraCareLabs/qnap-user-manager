"""Validate release identity and distribution contents without making network requests."""

import argparse
import ast
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import tarfile
import tomllib
import zipfile


def check_version(root, tag=None):
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    tree = ast.parse((root / "qnap_sdk/__init__.py").read_text())
    version = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
    )
    if project["version"] != version:
        raise ValueError("Package metadata and Python version differ")
    if tag is not None and tag != "v" + version:
        raise ValueError("Release tag must match v<package version>")
    return project["name"], version


def check_archive_names(names):
    forbidden = {"work", "reports", "__pycache__", ".git", ".env", ".DS_Store"}
    for name in names:
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or forbidden.intersection(path.parts)
            or name.endswith((".har", ".pyc"))
            or any("nas-session" in part or "credentials" in part for part in path.parts)
        ):
            raise ValueError("Distribution contains forbidden paths")


def check_distributions(root, directory):
    name, version = check_version(root)
    stem = name.replace("-", "_") + "-" + version
    expected = {stem + "-py3-none-any.whl", stem + ".tar.gz"}
    files = {p.name for p in directory.iterdir() if p.is_file()}
    if files != expected:
        raise ValueError("Expected exactly one wheel and one sdist for this version")
    with zipfile.ZipFile(directory / (stem + "-py3-none-any.whl")) as archive:
        names = archive.namelist()
        check_archive_names(names)
        metadata = BytesParser().parsebytes(archive.read(stem + ".dist-info/METADATA"))
        if (
            metadata["Name"] != name
            or metadata["Version"] != version
            or metadata["License-Expression"] != "MIT"
        ):
            raise ValueError("Unexpected wheel metadata")
        if archive.read(stem + ".dist-info/licenses/LICENSE") != (root / "LICENSE").read_bytes():
            raise ValueError("Wheel license differs from source")
        profile = "qnap_sdk/profiles/qts_5_1_9_2954.json"
        if archive.read(profile) != (root / profile).read_bytes():
            raise ValueError("Bundled firmware profile differs from source")
    with tarfile.open(directory / (stem + ".tar.gz")) as archive:
        check_archive_names(archive.getnames())
        license_file = archive.extractfile(stem + "/LICENSE")
        if license_file is None or license_file.read() != (root / "LICENSE").read_bytes():
            raise ValueError("Source distribution license differs from source")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    parser.add_argument("--dist", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    check_version(root, args.tag)
    if args.dist is not None:
        check_distributions(root, args.dist)
    print("Release metadata and requested distribution checks: PASS")


if __name__ == "__main__":
    main()
