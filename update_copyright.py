#!/usr/bin/python
#
# Copyright (C) 2009 W. Trevor King <wking@drexel.edu>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os.path
import re
import sys
import time

import os
import sys
import select
from subprocess import Popen, PIPE, mswindows
from threading import Thread

COPYRIGHT_TEXT="""#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA."""

COPYRIGHT_TAG='-xyz-COPYRIGHT-zyx-' # unlikely to occur in the wild :p

ALIASES = [
    ['Ben Finney <benf@cybersource.com.au>',
     'Ben Finney <ben+python@benfinney.id.au>',
     'John Doe <jdoe@example.com>'],
    ['Chris Ball <cjb@laptop.org>',
     'Chris Ball <cjb@thunk.printf.net>'],
    ['Gianluca Montecchi <gian@grys.it>',
     'gian <gian@li82-39>',
     'gianluca <gian@galactica>'],
    ['W. Trevor King <wking@drexel.edu>',
     'wking <wking@mjolnir>'],
    [None,
     'j^ <j@oil21.org>'],
    ]
COPYRIGHT_ALIASES = [
    ['Aaron Bentley and Panometrics, Inc.',
     'Aaron Bentley <abentley@panoramicfeedback.com>'],
    ]
EXCLUDES = [
    ['Aaron Bentley and Panometrics, Inc.',
     'Aaron Bentley <aaron.bentley@utoronto.ca>',]
    ]


IGNORED_PATHS = ['./.be/', './.bzr/', './build/']
IGNORED_FILES = ['COPYING', 'update_copyright.py', 'catmutt']

class Pipe (object):
    """
    Simple interface for executing POSIX-style pipes based on the
    subprocess module.  The only complication is the adaptation of
    subprocess.Popen._comminucate to listen to the stderrs of all
    processes involved in the pipe, as well as the terminal process'
    stdout.  There are two implementations of Pipe._communicate, one
    for MS Windows, and one for POSIX systems.  The MS Windows
    implementation is currently untested.

    >>> p = Pipe([['find', '/etc/'], ['grep', '^/etc/ssh$']])
    >>> p.stdout
    '/etc/ssh\\n'
    >>> p.status
    1
    >>> p.statuses
    [1, 0]
    >>> p.stderrs # doctest: +ELLIPSIS
    ["find: `...': Permission denied\\n...", '']
    """
    def __init__(self, cmds, stdin=None):
        # spawn processes
        self._procs = []
        for cmd in cmds:
            if len(self._procs) != 0:
                stdin = self._procs[-1].stdout
            self._procs.append(Popen(cmd, stdin=stdin, stdout=PIPE, stderr=PIPE))

        self.stdout,self.stderrs = self._communicate(input=None)

        # collect process statuses
        self.statuses = []
        self.status = 0
        for proc in self._procs:
            self.statuses.append(proc.wait())
            if self.statuses[-1] != 0:
                self.status = self.statuses[-1]

    # Code excerpted from subprocess.Popen._communicate()
    if mswindows == True:
        def _communicate(self, input=None):
            assert input == None, "stdin != None not yet supported"
            # listen to each process' stderr
            threads = []
            std_X_arrays = []
            for proc in self._procs:
                stderr_array = []
                thread = Thread(target=proc._readerthread,
                                args=(proc.stderr, stderr_array))
                thread.setDaemon(True)
                thread.start()
                threads.append(thread)
                std_X_arrays.append(stderr_array)
    
            # also listen to the last processes stdout
            stdout_array = []
            thread = Thread(target=proc._readerthread,
                            args=(proc.stdout, stdout_array))
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
            std_X_arrays.append(stdout_array)
    
            # join threads as they die
            for thread in threads:
                thread.join()
    
            # read output from reader threads
            std_X_strings = []
            for std_X_array in std_X_arrays:
                std_X_strings.append(std_X_array[0])

            stdout = std_X_strings.pop(-1)
            stderrs = std_X_strings
            return (stdout, stderrs)
    else: # POSIX
        def _communicate(self, input=None):
            read_set = []
            write_set = []
            read_arrays = []
            stdout = None # Return
            stderr = None # Return

            if self._procs[0].stdin:
                # Flush stdio buffer.  This might block, if the user has
                # been writing to .stdin in an uncontrolled fashion.
                self._procs[0].stdin.flush()
                if input:
                    write_set.append(self._procs[0].stdin)
                else:
                    self._procs[0].stdin.close()
            for proc in self._procs:
                read_set.append(proc.stderr)
                read_arrays.append([])
            read_set.append(self._procs[-1].stdout)
            read_arrays.append([])

            input_offset = 0
            while read_set or write_set:
                try:
                    rlist, wlist, xlist = select.select(read_set, write_set, [])
                except select.error, e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise
                if self._procs[0].stdin in wlist:
                    # When select has indicated that the file is writable,
                    # we can write up to PIPE_BUF bytes without risk
                    # blocking.  POSIX defines PIPE_BUF >= 512
                    chunk = input[input_offset : input_offset + 512]
                    bytes_written = os.write(self.stdin.fileno(), chunk)
                    input_offset += bytes_written
                    if input_offset >= len(input):
                        self._procs[0].stdin.close()
                        write_set.remove(self._procs[0].stdin)
                if self._procs[-1].stdout in rlist:
                    data = os.read(self._procs[-1].stdout.fileno(), 1024)
                    if data == "":
                        self._procs[-1].stdout.close()
                        read_set.remove(self._procs[-1].stdout)
                    read_arrays[-1].append(data)
                for i,proc in enumerate(self._procs):
                    if proc.stderr in rlist:
                        data = os.read(proc.stderr.fileno(), 1024)
                        if data == "":
                            proc.stderr.close()
                            read_set.remove(proc.stderr)
                        read_arrays[i].append(data)

            # All data exchanged.  Translate lists into strings.
            read_strings = []
            for read_array in read_arrays:
                read_strings.append(''.join(read_array))

            stdout = read_strings.pop(-1)
            stderrs = read_strings
            return (stdout, stderrs)

def _strip_email(*args):
    """
    >>> _strip_email('J Doe <jdoe@a.com>')
    ['J Doe']
    >>> _strip_email('J Doe <jdoe@a.com>', 'JJJ Smith <jjjs@a.com>')
    ['J Doe', 'JJJ Smith']
    """
    args = list(args)
    for i,arg in enumerate(args):
        if arg == None:
            continue
        index = arg.find('<')
        if index > 0:
            args[i] = arg[:index].rstrip()
    return args

def _replace_aliases(authors, with_email=True, aliases=None,
                     excludes=None):
    """
    >>> aliases = [['J Doe and C, Inc.', 'J Doe <jdoe@c.com>'],
    ...            ['J Doe <jdoe@a.com>', 'Johnny <jdoe@b.edu>'],
    ...            ['JJJ Smith <jjjs@a.com>', 'Jingly <jjjs@b.edu>'],
    ...            [None, 'Anonymous <a@a.com>']]
    >>> excludes = [['J Doe and C, Inc.', 'J Doe <jdoe@a.com>']]
    >>> _replace_aliases(['JJJ Smith <jjjs@a.com>', 'Johnny <jdoe@b.edu>',
    ...                   'Jingly <jjjs@b.edu>', 'Anonymous <a@a.com>'],
    ...                  with_email=True, aliases=aliases, excludes=excludes)
    ['J Doe <jdoe@a.com>', 'JJJ Smith <jjjs@a.com>']
    >>> _replace_aliases(['JJJ Smith', 'Johnny', 'Jingly', 'Anonymous'],
    ...                  with_email=False, aliases=aliases, excludes=excludes)
    ['J Doe', 'JJJ Smith']
    >>> _replace_aliases(['JJJ Smith <jjjs@a.com>', 'Johnny <jdoe@b.edu>',
    ...                   'Jingly <jjjs@b.edu>', 'J Doe <jdoe@c.com>'],
    ...                  with_email=True, aliases=aliases, excludes=excludes)
    ['J Doe and C, Inc.', 'JJJ Smith <jjjs@a.com>']
    """
    if aliases == None:
        aliases = ALIASES
    if excludes == None:
        excludes = EXCLUDES
    if with_email == False:
        aliases = [_strip_email(*alias) for alias in aliases]
        exclude = [_strip_email(*exclude) for exclude in excludes]
    for i,author in enumerate(authors):
        for alias in aliases:
            if author in alias[1:]:
                authors[i] = alias[0]
                break
    for i,author in enumerate(authors):
        for exclude in excludes:
            if author in exclude[1:] and exclude[0] in authors:
                authors[i] = None
    authors = sorted(set(authors))
    if None in authors:
        authors.remove(None)
    return authors

def authors_list():
    p = Pipe([['bzr', 'log', '-n0'],
              ['grep', '^ *committer\|^ *author'],
              ['cut', '-d:', '-f2'],
              ['sed', 's/ <.*//;s/^ *//'],
              ['sort'],
              ['uniq']])
    assert p.status == 0, p.statuses
    authors = p.stdout.rstrip().split('\n')
    return _replace_aliases(authors, with_email=False)

def update_authors(verbose=True):
    print "updating AUTHORS"
    f = file('AUTHORS', 'w')
    authors_text = 'Bugs Everywhere was written by:\n%s\n' % '\n'.join(authors_list())
    f.write(authors_text)
    f.close()

def ignored_file(filename, ignored_paths=None, ignored_files=None):
    """
    >>> ignored_paths = ['./a/', './b/']
    >>> ignored_files = ['x', 'y']
    >>> ignored_file('./a/z', ignored_paths, ignored_files)
    True
    >>> ignored_file('./ab/z', ignored_paths, ignored_files)
    False
    >>> ignored_file('./ab/x', ignored_paths, ignored_files)
    True
    >>> ignored_file('./ab/xy', ignored_paths, ignored_files)
    False
    >>> ignored_file('./z', ignored_paths, ignored_files)
    False
    """
    if ignored_paths == None:
        ignored_paths = IGNORED_PATHS
    if ignored_files == None:
        ignored_files = IGNORED_FILES
    for path in ignored_paths:
        if filename.startswith(path):
            return True
    if os.path.basename(filename) in ignored_files:
        return True
    if os.path.abspath(filename) != os.path.realpath(filename):
        return True # symink somewhere in path...
    return False

def _copyright_string(orig_year, final_year, authors):
    """
    >>> print _copyright_string(orig_year=2005,
    ...                         final_year=2005,
    ...                         authors=['A <a@a.com>', 'B <b@b.edu>']
    ...                        ) # doctest: +ELLIPSIS
    # Copyright (C) 2005 A <a@a.com>
    #                    B <b@b.edu>
    #
    # This program...
    >>> print _copyright_string(orig_year=2005,
    ...                         final_year=2009,
    ...                         authors=['A <a@a.com>', 'B <b@b.edu>']
    ...                        ) # doctest: +ELLIPSIS
    # Copyright (C) 2005-2009 A <a@a.com>
    #                         B <b@b.edu>
    #
    # This program...
    """
    if orig_year == final_year:
        date_range = '%s' % orig_year
    else:
        date_range = '%s-%s' % (orig_year, final_year)
    lines = ['# Copyright (C) %s %s' % (date_range, authors[0])]
    for author in authors[1:]:
        lines.append('#' +
                     ' '*(len(' Copyright (C) ')+len(date_range)+1) +
                     author)
    return '%s\n%s' % ('\n'.join(lines), COPYRIGHT_TEXT)

def _tag_copyright(contents):
    """
    >>> contents = '''Some file
    ... bla bla
    ... # Copyright (copyright begins)
    ... # (copyright continues)
    ... # bla bla bla
    ... (copyright ends)
    ... bla bla bla
    ... '''
    >>> print _tag_copyright(contents),
    Some file
    bla bla
    -xyz-COPYRIGHT-zyx-
    (copyright ends)
    bla bla bla
    """
    lines = []
    incopy = False
    for line in contents.splitlines():
        if incopy == False and line.startswith('# Copyright'):
            incopy = True
            lines.append(COPYRIGHT_TAG)
        elif incopy == True and not line.startswith('#'):
            incopy = False
        if incopy == False:
            lines.append(line.rstrip('\n'))
    return '\n'.join(lines)+'\n'

def _update_copyright(contents, orig_year, authors):
    current_year = time.gmtime()[0]
    copyright_string = _copyright_string(orig_year, current_year, authors)
    contents = _tag_copyright(contents)
    return contents.replace(COPYRIGHT_TAG, copyright_string)

def update_file(filename, verbose=True):
    if verbose == True:
        print "updating", filename
    contents = file(filename, 'r').read()

    p = Pipe([['bzr', 'log', '-n0', filename],
              ['grep', '^ *timestamp: '],
              ['tail', '-n1'],
              ['sed', 's/^ *//;'],
              ['cut', '-b', '16-19']])
    if p.status != 0:
        assert p.statuses[0] == 3, p.statuses
        return # bzr doesn't version that file
    assert p.status == 0, p.statuses
    orig_year = int(p.stdout.strip())

    p = Pipe([['bzr', 'log', '-n0', filename],
              ['grep', '^ *author: \|^ *committer: '],
              ['cut', '-d:', '-f2'],
              ['sed', 's/^ *//;s/ *$//'],
              ['sort'],
              ['uniq']])
    assert p.status == 0, p.statuses
    authors = p.stdout.rstrip().split('\n')
    authors = _replace_aliases(authors, with_email=True,
                               aliases=ALIASES+COPYRIGHT_ALIASES)

    contents = _update_copyright(contents, orig_year, authors)
    f = file(filename, 'w')
    f.write(contents)
    f.close()

def test():
    import doctest
    doctest.testmod() 

if __name__ == '__main__':
    import optparse
    usage = """%prog [options] [file ...]

Update copyright information in source code with information from
the bzr repository.  Run from the BE repository root.

Replaces every line starting with '^# Copyright' and continuing with
'^#' with an auto-generated copyright blurb.  If you want to add
#-commented material after a copyright blurb, please insert a blank
line between the blurb and your comment (as in this file), so the
next run of update_copyright.py doesn't clobber your comment.

If no files are given, a list of files to update is generated
automatically.
"""
    p = optparse.OptionParser(usage)
    p.add_option('--test', dest='test', default=False,
                 action='store_true', help='Run internal tests and exit')
    options,args = p.parse_args()

    if options.test == True:
        test()
        sys.exit(0)

    update_authors()

    files = args
    if len(files) == 0:
        p = Pipe([['grep', '-rc', '# Copyright', '.'],
                  ['grep', '-v', ':0$'],
                  ['cut', '-d:', '-f1']])
        assert p.status == 0
        files = p.stdout.rstrip().split('\n')

    for filename in files:
        if ignored_file(filename) == True:
            continue
        update_file(filename)
