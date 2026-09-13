"""Typed CRUD and incremental permission changes for verified firmware profiles."""

import base64
import time
from .client import QnapError, UnverifiedOperation, field
from .models import User, Group, Share, Permission, SharePermission


def identity(value):
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode()) > 256
        or any(c in value for c in ("/", "\\", "\x00", "\n", "\r"))
    ):
        raise QnapError("Invalid resource name")
    return value


def optional(data, path, default=None):
    try:
        return field(data, path)
    except QnapError:
        return default


def mapped_model(item, mapping, model):
    values = {}
    for destination, source in mapping["fields"].items():
        value = field(item, source)
        if destination == "disabled":
            if value is True or value in ("1", 1):
                value = True
            elif value is False or value in ("0", 0):
                value = False
            else:
                raise QnapError("Unrecognized disabled flag")
            if mapping.get("transforms", {}).get(destination) == "invert_bool":
                value = not value
        elif destination in ("groups", "members"):
            if value == "":
                value = ()
            elif isinstance(value, list):
                value = tuple(value)
            elif isinstance(value, str):
                value = (value,)
            else:
                raise QnapError("Unrecognized membership response")
        elif destination == "uid":
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise QnapError("Invalid NAS user ID") from None
        values[destination] = value
    try:
        result = model(**values)
    except TypeError:
        raise QnapError("Profile fields do not match domain model") from None
    name = result.username if isinstance(result, User) else result.name
    identity(name)
    return result


def mapping_for(client, operation):
    mapping = client.manifest.get("operations", {}).get(operation, {}).get("model")
    if not mapping or not mapping.get("items_path") or not mapping.get("fields"):
        raise UnverifiedOperation("Typed results require verified field mappings")
    return mapping


def mapped_items(client, operation, model, parameters):
    mapping = mapping_for(client, operation)
    data = client.call(operation, **parameters)
    if mapping.get("count_path") and str(field(data, mapping["count_path"])) == "0":
        return []
    items = field(data, mapping["items_path"])
    if items in (None, ""):
        return []
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise QnapError("Unexpected collection in NAS response")
    return [mapped_model(item, mapping, model) for item in items]


def mapped_one(client, operation, model, parameters):
    mapping = mapping_for(client, operation)
    return mapped_model(
        field(client.call(operation, **parameters), mapping["items_path"]), mapping, model
    )


def all_items(client, operation, model, page_size=100):
    if not isinstance(page_size, int) or not 1 <= page_size <= 1000:
        raise QnapError("Invalid page size")
    spec = client.manifest["operations"].get(operation, {})
    if "lower" not in spec.get("parameters", []):
        return mapped_items(client, operation, model, {})
    mapping = mapping_for(client, operation)
    results = []
    lower = 0
    while True:
        data = client.call(operation, lower=lower, upper=lower + page_size)
        try:
            total = int(field(data, mapping["count_path"]))
        except (ValueError, TypeError):
            raise QnapError("Invalid collection count") from None
        if total == 0:
            return results
        items = field(data, mapping["items_path"])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list) or not items:
            raise QnapError("NAS pagination made no progress")
        page = [mapped_model(item, mapping, model) for item in items]

        def ids(row):
            return row.username if isinstance(row, User) else row.name

        if set(map(ids, results)) & set(map(ids, page)):
            raise QnapError("NAS pagination repeated results")
        results.extend(page)
        lower += len(page)
        if lower >= total:
            return results
        if lower > 100000:
            raise QnapError("Collection exceeds safety limit")


def confirm_removed(resource, name):
    deadline = time.monotonic() + resource.client.verification_timeout
    while True:
        items = resource.list_all()
        if name not in [x.username if isinstance(x, User) else x.name for x in items]:
            return
        if time.monotonic() >= deadline:
            raise QnapError("Deletion not yet confirmed; inspect NAS before retrying")
        time.sleep(0.2)


class Users:
    def __init__(self, client):
        self.client = client

    def list(self, **parameters):
        return mapped_items(self.client, "users.list", User, parameters)

    def list_all(self, page_size=100):
        return all_items(self.client, "users.list", User, page_size)

    def get(self, username):
        identity(username)
        if username not in [x.username for x in self.list_all()]:
            raise QnapError("User not found")
        result = mapped_one(self.client, "users.get", User, {"userName": username})
        return User(
            result.username, result.description, result.disabled, self.groups(username), result.uid
        )

    def groups(self, username):
        data = self.client.call("users.groups", userName=identity(username), lower=0, upper=10)
        value = field(data, "func.ownContent.ownGroup")
        return tuple(value.split(", ")) if value else ()

    def create(self, username, password, *, description="", groups=()):
        identity(username)
        if not isinstance(password, str) or not password or len(password.encode("utf-8")) > 64:
            raise QnapError("Password must contain 1 to 64 UTF-8 bytes")
        if username in [x.username for x in self.list_all()]:
            raise QnapError("User already exists")
        if len(username.encode()) > 32:
            raise QnapError("QTS username exceeds 32 bytes")
        self.client.call(
            "users.create",
            target=username,
            a_passwd=base64.b64encode(password.encode("utf-8")).decode(),
            a_description=description,
        )
        for group in groups:
            self.client.groups.add_member(group, username)
        return self.get(username)

    def update(self, username, *, description=None, disabled=None):
        if disabled is not None and not isinstance(disabled, bool):
            raise QnapError("disabled must be a boolean")
        if description is not None and not isinstance(description, str):
            raise QnapError("description must be a string")
        data = self.client.call("users.get", userName=identity(username))
        old = field(data, "userInfo")
        if old["username"] != username or int(old["uid"]) == 0:
            raise QnapError("User not found or protected")
        params = {
            "a_description": old["description"] if description is None else description,
            "a_email": old["email"],
            "a_tel": old["tel"],
            "a_tel_country_code": old["tel_country_code"],
            "a_uid": int(old["uid"]),
        }
        if disabled is not None:
            if not isinstance(disabled, bool):
                raise QnapError("disabled must be a boolean")
            params.update(
                a_enable=0 if disabled else 1,
                a_expire=0,
                year=int(old["year"]),
                month=int(old["month"]),
                day=int(old["day"]),
            )
        self.client.call("users.update", target=username, **params)
        return self.get(username)

    def set_disabled(self, username, disabled=True):
        return self.update(username, disabled=disabled)

    def disable(self, username):
        return self.set_disabled(username, True)

    def enable(self, username):
        return self.set_disabled(username, False)

    def set_password(self, username, password):
        identity(username)
        if not isinstance(password, str) or not password or len(password.encode("utf-8")) > 64:
            raise QnapError("Password must contain 1 to 64 UTF-8 bytes")
        self.get(username)
        self.client.call(
            "users.set_password",
            target=username,
            password=base64.b64encode(password.encode("utf-8")).decode(),
        )

    def reset_password(self, username, password):
        return self.set_password(username, password)

    def delete(self, username):
        if username not in [x.username for x in self.list_all()]:
            raise QnapError("User not found")
        self.client.call("users.delete", target=identity(username))
        confirm_removed(self, username)


class Groups:
    def __init__(self, client):
        self.client = client

    def list(self, **parameters):
        return mapped_items(self.client, "groups.list", Group, parameters)

    def list_all(self, page_size=100):
        return all_items(self.client, "groups.list", Group, page_size)

    def get(self, name):
        identity(name)
        if name not in [x.name for x in self.list_all()]:
            raise QnapError("Group not found")
        result = mapped_one(self.client, "groups.get", Group, {"groupname": name})
        return Group(result.name, result.description, self.members(name))

    def members(self, name):
        data = self.client.call("groups.members", groupname=identity(name), lower=0, upper=10)
        value = optional(data, "func.ownContent.ownUser", "")
        return tuple(value.split(", ")) if value else ()

    def create(self, name, *, description="", members=()):
        identity(name)
        if name in [x.name for x in self.list_all()]:
            raise QnapError("Group already exists")
        self.client.call("groups.create", target=name, a_description=description)
        for member in members:
            self.add_member(name, member)
        return self.get(name)

    def update(self, name, *, description):
        self.get(name)
        self.client.call("groups.update", target=identity(name), a_description=description)
        return self.get(name)

    def add_member(self, name, username):
        return self._member(name, username, True)

    def remove_member(self, name, username):
        return self._member(name, username, False)

    def _member(self, name, username, select):
        identity(name)
        identity(username)
        key = "select_user" if select else "unselect_user"
        self.client.call(
            "groups.members_update",
            target=name,
            **{key: username, "select_user_len": int(select), "unselect_user_len": int(not select)},
        )
        members = self.members(name)
        if (username in members) != select:
            raise QnapError("Group membership change not confirmed")
        return members

    def delete(self, name):
        self.get(name)
        self.client.call("groups.delete", target=identity(name))
        confirm_removed(self, name)


class Shares:
    def __init__(self, client):
        self.client = client

    def list(self, **parameters):
        return mapped_items(self.client, "shares.list", Share, parameters)

    def list_all(self, page_size=100):
        return all_items(self.client, "shares.list", Share, page_size)

    def get(self, name):
        identity(name)
        if name not in [x.name for x in self.list_all()]:
            raise QnapError("Shared folder not found")
        return mapped_one(self.client, "shares.get", Share, {"sharename": name})

    def create(self, name, *, volume, description=""):
        identity(name)
        if name in [x.name for x in self.list_all()]:
            raise QnapError("Shared folder already exists")
        if not isinstance(volume, int) or volume < 1:
            raise QnapError("A valid volume ID is required")
        self.client.call("shares.create", target=name, vol_no=volume, comment=description)
        return self.get(name)

    def update(self, name, *, description=None, new_name=None, hidden=None):
        self.get(name)
        d = field(self.client.call("shares.get", sharename=name), "shareProperty")
        desired = identity(new_name) if new_name is not None else name
        if desired != name and desired in [x.name for x in self.list_all()]:
            raise QnapError("Shared folder already exists")
        if hidden is not None and not isinstance(hidden, bool):
            raise QnapError("hidden must be boolean")
        parameters = {
            "new_sname": desired,
            "share_comment": d["comment"] if description is None else description,
            "manual_path": d["path"],
            "vol_no": int(d["selectedVol"]),
            "share_hidden": int(d["hidden"]) if hidden is None else int(hidden),
            "oplocks": int(d["oplocks"]),
            "mangled_names": 1 if d["supportNameMangling"] == "yes" else 0,
            "ftp_wonly": int(d["ftp_wonly"]["val"]),
            "recycle_bin": int(d["recyclePerShare"]),
            "recycle_bin_administrators_only": int(d["recycleAdministratorsOnly"]),
            "qsync": int(d["qsync"]),
            "hide_unreadable": int(d["hide_unreadable"] == "yes"),
            "share_enumeration": int(d["share_enumeration"] == "yes"),
            "timemachine": int(d["timemachine"]),
        }
        if "showSnapshots" in d:
            parameters["showSnapshots"] = int(d["showSnapshots"] == "yes")
        if "smb_encryption" in d:
            parameters["EncryptData"] = int(d["smb_encryption"])
        self.client.call("shares.update", target=name, **parameters)
        return self.get(desired)

    def delete(self, name, *, delete_files=False):
        """Remove registration; delete_files=True also removes stored files."""
        if not isinstance(delete_files, bool):
            raise QnapError("delete_files must be boolean")
        self.get(name)
        self.client.call(
            "shares.delete", target=identity(name), delsymboliconly=0 if delete_files else 1
        )
        confirm_removed(self, name)


class Permissions:
    def __init__(self, client):
        self.client = client

    def list(self, subject, *, subject_type="user"):
        if subject_type not in ("user", "group"):
            raise QnapError("Subject type must be user or group")
        identity(subject)
        if subject_type == "user" and subject not in [
            x.username for x in self.client.users.list_all()
        ]:
            raise QnapError("User not found")
        if subject_type == "group" and subject not in [
            x.name for x in self.client.groups.list_all()
        ]:
            raise QnapError("Group not found")
        key = "userName" if subject_type == "user" else "groupName"
        operation = "permissions." + subject_type + "_get"
        results = []
        lower = 0
        page_size = 100
        codes = {"R": Permission.READ_ONLY, "W": Permission.READ_WRITE, "I": Permission.DENY}
        while True:
            data = self.client.call(
                operation, **{key: subject, "lower": lower, "upper": lower + page_size}
            )
            root = field(data, "func.ownContent.shareroot")
            total = int(root["data"]["count"])
            if total == 0:
                return results
            rows = root["data"]["share"]
            rows = [rows] if isinstance(rows, dict) else rows
            if not rows:
                raise QnapError("Permission pagination made no progress")
            for row in rows:
                code = row.get("type", "")
                effective = row.get("preview", "")
                if code not in ("", "R", "W", "I") or effective not in ("", "N", "R", "W", "I"):
                    raise QnapError("Unrecognized permission response")
                if row["sharename"] in [x.share for x in results]:
                    raise QnapError("Permission pagination repeated results")
                results.append(
                    SharePermission(row["sharename"], codes.get(code), codes.get(effective))
                )
            lower += len(rows)
            if lower >= total:
                return results
            if lower > 100000:
                raise QnapError("Permission list exceeds safety limit")

    def get(self, subject, share, *, subject_type="user"):
        for entry in self.list(subject, subject_type=subject_type):
            if entry.share == share:
                return entry
        raise QnapError("Shared folder not found in permission response")

    def set(self, subject, share, permission, *, subject_type="user"):
        identity(subject)
        identity(share)
        if subject_type not in ("user", "group"):
            raise QnapError("Subject type must be user or group")
        desired = Permission(permission) if permission is not None else None
        prefix = {
            Permission.READ_ONLY: "rd_share",
            Permission.READ_WRITE: "rw_share",
            Permission.DENY: "no_share",
            None: "empty_share",
        }[desired]
        parameters = {
            p + "_len": int(p == prefix)
            for p in ("rd_share", "rw_share", "no_share", "empty_share")
        }
        parameters[prefix + "0"] = share
        self.client.call("permissions." + subject_type + "_set", target=subject, **parameters)
        result = self.get(subject, share, subject_type=subject_type)
        if result.permission != desired:
            raise QnapError("Permission change not confirmed")
        return result

    def grant(self, subject, share, permission, *, subject_type="user"):
        return self.set(subject, share, permission, subject_type=subject_type)

    def revoke(self, subject, share, *, subject_type="user"):
        return self.set(subject, share, None, subject_type=subject_type)

    def delete(self, subject, share, *, subject_type="user"):
        return self.revoke(subject, share, subject_type=subject_type)


class Quotas:
    def __init__(self, client):
        self.client = client

    def get(self, **parameters):
        return self.client.call("quota.get", **parameters)

    def set(self, username, **parameters):
        return self.client.call("quota.set", target=username, **parameters)
