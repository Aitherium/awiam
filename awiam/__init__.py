"""awiam — who is this caller?

    from awiam import Directory, Sessions, Subject

    d = Directory("iam.json")
    d.put(Subject(id="david", display="David", email="d@example.com"))
    s = Sessions(d)

    token = s.issue("david")
    r = s.resolve(token)
    if r:
        print(r.subject_id)

Deliberately NOT an authorization store. `awiam` answers who you are, `awbac`
what you may do, `awseal` what proves it. Three packages, three questions.
"""

from .directory import Directory, DirectoryUnreadableError, Subject
from .sessions import Resolution, Sessions

__version__ = "0.1.0"
__all__ = ["Directory", "Subject", "DirectoryUnreadableError", "Sessions", "Resolution"]
