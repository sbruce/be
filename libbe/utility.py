# Copyright (C) 2005 Aaron Bentley and Panometrics, Inc.
# <abentley@panoramicfeedback.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
import calendar
import time
import os
import tempfile

class FileString(object):
    """Bare-bones pseudo-file class
    
    >>> f = FileString("me\\nyou")
    >>> len(list(f))
    2
    >>> len(list(f))
    0
    >>> f = FileString()
    >>> f.write("hello\\nthere")
    >>> "".join(list(f))
    'hello\\nthere'
    """
    def __init__(self, str=""):
        object.__init__(self)
        self.str = str
        self._iter = None

    def __iter__(self):
        if self._iter is None:
            self._iter = self._get_iter()
        return self._iter

    def _get_iter(self):
        for line in self.str.splitlines(True):
            yield line

    def write(self, line):
        self.str += line


def get_file(f):
    """
    Return a file-like object from input.  This is a helper for functions that
    can take either file or string parameters.

    :param f: file or string
    :return: a FileString if input is a string, otherwise return the imput 
    object.

    >>> isinstance(get_file(file("/dev/null")), file)
    True
    >>> isinstance(get_file("f"), FileString)
    True
    """
    if isinstance(f, basestring):
        return FileString(f)
    else:
        return f


RFC_2822_TIME_FMT = "%a, %d %b %Y %H:%M:%S +0000"


def time_to_str(time_val):
    """Convert a time value into an RFC 2822-formatted string.  This format
    lacks sub-second data.
    >>> time_to_str(0)
    'Thu, 01 Jan 1970 00:00:00 +0000'
    """
    return time.strftime(RFC_2822_TIME_FMT, time.gmtime(time_val))

def str_to_time(str_time):
    """Convert an RFC 2822-fomatted string into a time falue.
    >>> str_to_time("Thu, 01 Jan 1970 00:00:00 +0000")
    0
    >>> q = time.time()
    >>> str_to_time(time_to_str(q)) == int(q)
    True
    """
    return calendar.timegm(time.strptime(str_time, RFC_2822_TIME_FMT))

def handy_time(time_val):
    return time.strftime("%a, %d %b %Y %H:%M", time.localtime(time_val))

class CantFindEditor(Exception):
    def __init__(self):
        Exception.__init__(self, "Can't find editor to get string from")

def editor_string():

    """Invokes the editor, and returns the user_produced text as a string

    >>> del os.environ["EDITOR"]
    >>> editor_string()
    Traceback (most recent call last):
    CantFindEditor: Can't find editor to get string from
    >>> os.environ["EDITOR"] = "echo bar > "
    >>> editor_string()
    'bar\\n'
    """
    try:
        editor = os.environ["EDITOR"]
    except KeyError:
        raise CantFindEditor()
    fhandle, fname = tempfile.mkstemp()
    try:
        os.close(fhandle)
        oldmtime = os.path.getmtime(fname)
        os.system("%s %s" % (editor, fname))
        if oldmtime == os.path.getmtime(fname) and\
            file(fname, "rb").read() == "":
            output = None
        else:
            output = file(fname, "rb").read()
    finally:
        os.unlink(fname)
    return output
