import os
import os.path
import cmdutil
import errno
import names
import mapfile
from rcs import rcs_by_name

class NoBugDir(Exception):
    def __init__(self, path):
        msg = "The directory \"%s\" has no bug directory." % path
        Exception.__init__(self, msg)
        self.path = path
    

def tree_root(dir, old_version=False):
    rootdir = os.path.realpath(dir)
    while (True):
        versionfile=os.path.join(rootdir, ".be/version")
        if os.path.exists(versionfile):
            if not old_version:
                test_version(versionfile)
            break;
        elif rootdir == "/":
            raise NoBugDir(dir)
        rootdir=os.path.dirname(rootdir)
    return BugDir(os.path.join(rootdir, ".be"))

class BadTreeVersion(Exception):
    def __init__(self, version):
        Exception.__init__(self, "Unsupported tree version: %s" % version)
        self.version = version

def test_version(path):
    tree_version = file(path, "rb").read()
    if tree_version != TREE_VERSION_STRING:
        raise BadTreeVersion(tree_version)

def set_version(path, rcs):
    rcs.set_file_contents(os.path.join(path, "version"), TREE_VERSION_STRING)
    

TREE_VERSION_STRING = "Bugs Everywhere Tree 1 0\n"

def create_bug_dir(path, rcs):
    root = os.path.join(path, ".be")
    rcs.mkdir(root)
    rcs.mkdir(os.path.join(root, "bugs"))
    set_version(root, rcs)
    map_save(rcs, os.path.join(root, "settings"), {"rcs_name": rcs.name})
    return BugDir(path)


def setting_property(name, valid=None):
    def getter(self):
        value = self.settings.get(name) 
        if valid is not None:
            if value not in valid:
                raise InvalidValue(name, value)
        return value

    def setter(self, value):
        if valid is not None:
            if value not in valid and value is not None:
                raise InvalidValue(name, value)
        if value is None:
            del self.settings[name]
        else:
            self.settings[name] = value
        self.save_settings()
    return property(getter, setter)


class BugDir:
    def __init__(self, dir):
        self.dir = dir
        self.bugs_path = os.path.join(self.dir, "bugs")
        try:
            self.settings = map_load(os.path.join(self.dir, "settings"))
        except NoSuchFile:
            self.settings = {"rcs_name": "None"}

    rcs_name = setting_property("rcs_name", ("None", "Arch"))
    _rcs = None

    def save_settings(self):
        map_save(self.rcs, os.path.join(self.dir, "settings"), self.settings)

    def get_rcs(self):
        if self._rcs is not None and self.rcs_name == _rcs.name:
            return self._rcs
        self._rcs = rcs_by_name(self.rcs_name)
        return self._rcs

    rcs = property(get_rcs)

    def list(self):
        for uuid in self.list_uuids():
            yield Bug(self.bugs_path, uuid, self.rcs_name)

    def list_uuids(self):
        for uuid in os.listdir(self.bugs_path):
            if (uuid.startswith('.')):
                continue
            yield uuid

    def new_bug(self):
        uuid = names.uuid()
        path = os.path.join(self.bugs_path, uuid)
        self.rcs.mkdir(path)
        bug = Bug(self.bugs_path, None, self.rcs_name)
        bug.uuid = uuid
        return bug

class InvalidValue(Exception):
    def __init__(self, name, value):
        msg = "Cannot assign value %s to %s" % (value, name)
        Exception.__init__(self, msg)
        self.name = name
        self.value = value


def checked_property(name, valid):
    def getter(self):
        value = self.__getattribute__("_"+name)
        if value not in valid:
            raise InvalidValue(name, value)
        return value

    def setter(self, value):
        if value not in valid:
            raise InvalidValue(name, value)
        return self.__setattr__("_"+name, value)
    return property(getter, setter)

severity_levels = ("wishlist", "minor", "serious", "critical", "fatal")

severity_value = {}
for i in range(len(severity_levels)):
    severity_value[severity_levels[i]] = i

class Bug(object):
    status = checked_property("status", (None, "open", "closed"))
    severity = checked_property("severity", (None, "wishlist", "minor",
                                             "serious", "critical", "fatal"))

    def __init__(self, path, uuid, rcs_name):
        self.path = path
        self.uuid = uuid
        if uuid is not None:
            dict = map_load(self.get_path("values"))
        else:
            dict = {}

        self.rcs_name = rcs_name

        self.summary = dict.get("summary")
        self.creator = dict.get("creator")
        self.target = dict.get("target")
        self.status = dict.get("status")
        self.severity = dict.get("severity")
        self.assigned = dict.get("assigned")

    def get_path(self, file):
        return os.path.join(self.path, self.uuid, file)

    def _get_active(self):
        return self.status == "open"

    active = property(_get_active)

    def add_attr(self, map, name):
        value = self.__getattribute__(name)
        if value is not None:
            map[name] = value

    def save(self):
        map = {}
        self.add_attr(map, "assigned")
        self.add_attr(map, "summary")
        self.add_attr(map, "creator")
        self.add_attr(map, "target")
        self.add_attr(map, "status")
        self.add_attr(map, "severity")
        path = self.get_path("values")
        map_save(rcs_by_name(self.rcs_name), path, map)


def map_save(rcs, path, map):
    """Save the map as a mapfile to the specified path"""
    if not os.path.exists(path):
        rcs.add_id(path)
    output = file(path, "wb")
    mapfile.generate(output, map)

class NoSuchFile(Exception):
    def __init__(self, pathname):
        Exception.__init__(self, "No such file: %s" % pathname)


def map_load(path):
    try:
        return mapfile.parse(file(path, "rb"))
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise e
        raise NoSuchFile(path)


class MockBug:
    def __init__(self, severity):
        self.severity = severity

def cmp_severity(bug_1, bug_2):
    """
    Compare the severity levels of two bugs, with more sever bugs comparing
    as less.

    >>> cmp_severity(MockBug(None), MockBug(None))
    0
    >>> cmp_severity(MockBug("wishlist"), MockBug(None)) < 0
    True
    >>> cmp_severity(MockBug(None), MockBug("wishlist")) > 0
    True
    >>> cmp_severity(MockBug("critical"), MockBug("wishlist")) < 0
    True
    """
    val_1 = severity_value.get(bug_1.severity)
    val_2 = severity_value.get(bug_2.severity)
    return -cmp(val_1, val_2)
