def unique_name(bug, bugs):
    chars = 1
    for some_bug in bugs:
        if bug.uuid == some_bug.uuid:
            continue
        while (bug.uuid[:chars] == some_bug.uuid[:chars]):
            chars+=1
    return bug.uuid[:chars]

class UserError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

def get_bug(spec, bug_dir):
    matches = []
    bugs = list(bug_dir.list())
    for bug in bugs:
        if bug.uuid.startswith(spec):
            matches.append(bug)
    if len(matches) > 1:
        raise UserError("More than one bug matches %s.  Please be more"
                        " specific." % spec)
    if len(matches) == 1:
        return matches[0]
        
    matches = []
    for bug in bugs:
        if bug.name == spec:
            matches.append(bug)
    if len(matches) > 1:
        raise UserError("More than one bug has the name %s.  Please use the"
                        " uuid." % spec)
    if len(matches) == 0:
        raise UserError("No bug has the name %s" % spec)
    return matches[0]
