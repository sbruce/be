# Copyright (C) 2005-2009 Aaron Bentley and Panometrics, Inc.
#                         W. Trevor King <wking@drexel.edu>
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
"""Create a new bug"""
from libbe import cmdutil, bugdir, settings_object
__desc__ = __doc__

def execute(args, test=False):
    """
    >>> import os, time
    >>> from libbe import bug
    >>> bd = bugdir.simple_bug_dir()
    >>> os.chdir(bd.root)
    >>> bug.uuid_gen = lambda: "X"
    >>> execute (["this is a test",], test=True)
    Created bug with ID X
    >>> bd.load()
    >>> bug = bd.bug_from_uuid("X")
    >>> print bug.summary
    this is a test
    >>> bug.time <= int(time.time())
    True
    >>> print bug.severity
    minor
    >>> bug.target == settings_object.EMPTY
    True
    """
    parser = get_parser()
    options, args = parser.parse_args(args)
    cmdutil.default_complete(options, args, parser)
    if len(args) != 1:
        raise cmdutil.UsageError("Please supply a summary message")
    bd = bugdir.BugDir(from_disk=True, manipulate_encodings=not test)
    bug = bd.new_bug(summary=args[0])
    if options.reporter != None:
        bug.reporter = options.reporter
    else:
        bug.reporter = bug.creator
    if options.assigned != None:
        bug.assigned = options.assigned
    elif bd.default_assignee != settings_object.EMPTY:
        bug.assigned = bd.default_assignee
    bd.save()
    print "Created bug with ID %s" % bd.bug_shortname(bug)

def get_parser():
    parser = cmdutil.CmdOptionParser("be new SUMMARY")
    parser.add_option("-r", "--reporter", metavar="REPORTER", dest="reporter",
                      help="The user who reported the bug", default=None)
    parser.add_option("-a", "--assigned", metavar="ASSIGNED", dest="assigned",
                      help="The developer in charge of the bug", default=None)
    return parser

longhelp="""
Create a new bug, with a new ID.  The summary specified on the commandline
is a string that describes the bug briefly.
"""

def help():
    return get_parser().help_str() + longhelp
