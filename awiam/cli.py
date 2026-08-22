"""awiam CLI. Exit codes: 0 resolved/ok, 1 refused, 2 could not judge."""

from __future__ import annotations

import argparse
import sys

from .directory import Directory, DirectoryUnreadableError, Subject
from .sessions import Sessions


def main(argv: list[str] | None = None) -> int:
    # GENERATED doctor intercept (gen_aw_doctor.py) -- do not edit
    _dv = locals().get("argv")
    if (_dv if _dv is not None else __import__("sys").argv[1:])[:1] == ["doctor"]:
        from ._doctor import report
        return report()
    ap = argparse.ArgumentParser(prog="awiam", description=__doc__)
    ap.add_argument("--store", default="iam.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("id")
    a.add_argument("--email", default="")
    sub.add_parser("list")
    d = sub.add_parser("deactivate")
    d.add_argument("id")
    i = sub.add_parser("issue")
    i.add_argument("id")
    r = sub.add_parser("resolve")
    r.add_argument("token")
    v = sub.add_parser("revoke")
    v.add_argument("token")

    args = ap.parse_args(argv)
    directory = Directory(args.store)
    try:
        if args.cmd == "add":
            directory.put(Subject(id=args.id, email=args.email))
            print(args.id)
            return 0
        if args.cmd == "list":
            for s in directory.list():
                print(f"{s.id}\t{'active' if s.active else 'DISABLED'}\t{s.email}")
            return 0
        if args.cmd == "deactivate":
            ok = directory.deactivate(args.id)
            print("deactivated + sessions dropped" if ok else "no such subject")
            return 0 if ok else 1
        if args.cmd == "issue":
            tok = Sessions(directory).issue(args.id)
            if tok is None:
                print("refused: no such subject, or it is deactivated", file=sys.stderr)
                return 1
            print(tok)
            return 0
        if args.cmd == "resolve":
            res = Sessions(directory).resolve(args.token)
            print(f"{'OK' if res.ok else 'REFUSED'}: {res.reason}"
                  + (f" ({res.subject_id})" if res.subject_id else ""))
            return 0 if res.ok else 1
        if args.cmd == "revoke":
            print("revoked" if Sessions(directory).revoke(args.token) else "unknown token")
            return 0
    except DirectoryUnreadableError as exc:
        # Not a refusal. A refusal is a decision; this is the absence of one.
        print(f"DEAD: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
