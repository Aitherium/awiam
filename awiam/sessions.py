"""Sessions: turning a token back into a subject, and refusing to when it should.

Every lookup re-checks the SUBJECT, not just the token. A session that outlives
the account it belongs to is the thing everyone means when they say "we removed
their access and they were still in" — so `resolve()` denies on a missing
subject, an inactive subject, an expired session, and an unknown token, and says
which.

Tokens are compared in constant time. A session store that compares with `==`
leaks token bytes through timing; it is a small leak, it is entirely avoidable,
and the cost of avoiding it is one stdlib call.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from .directory import Directory

DEFAULT_TTL = 12 * 3600


@dataclass(frozen=True)
class Resolution:
    ok: bool
    subject_id: str | None
    reason: str

    def __bool__(self) -> bool:
        return self.ok


def _hash(token: str) -> str:
    """Tokens are stored HASHED.

    A directory file is backed up, copied to a laptop, pasted into an issue. If
    it holds live tokens, every one of those is a credential leak; if it holds
    hashes, they are useless to whoever ends up with the file.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Sessions:
    def __init__(self, directory: Directory, ttl: int = DEFAULT_TTL) -> None:
        self.dir = directory
        self.ttl = ttl

    def issue(self, subject_id: str) -> str | None:
        """Mint a session. Returns None if the subject cannot hold one."""
        subj = self.dir.get(subject_id)
        if subj is None or not subj.active:
            # Refuse at ISSUE as well as at resolve. Minting a session for a
            # disabled account and rejecting it later works, right up until
            # someone reactivates the account and the old token comes back to
            # life.
            return None
        token = secrets.token_urlsafe(32)
        data = self.dir._load()
        data["sessions"][_hash(token)] = {
            "subject": subject_id,
            "issued": time.time(),
            "expires": time.time() + self.ttl,
        }
        self.dir._save(data)
        return token

    def resolve(self, token: str) -> Resolution:
        if not token:
            return Resolution(False, None, "no token presented")
        data = self.dir._load()
        want = _hash(token)

        found = None
        for stored, sess in data["sessions"].items():
            # constant-time compare over the HASHES
            if hmac.compare_digest(stored, want):
                found = sess
                break
        if found is None:
            return Resolution(False, None, "unknown token")
        if found.get("expires", 0) < time.time():
            return Resolution(False, None, "session expired")

        subj = self.dir.get(found.get("subject", ""))
        if subj is None:
            return Resolution(False, None, "session refers to a subject that no longer exists")
        if not subj.active:
            return Resolution(False, None, f"subject {subj.id!r} is deactivated")
        return Resolution(True, subj.id, "resolved")

    def revoke(self, token: str) -> bool:
        data = self.dir._load()
        h = _hash(token)
        if h not in data["sessions"]:
            return False
        del data["sessions"][h]
        self.dir._save(data)
        return True

    def purge_expired(self) -> int:
        data = self.dir._load()
        now = time.time()
        keep = {t: s for t, s in data["sessions"].items() if s.get("expires", 0) >= now}
        n = len(data["sessions"]) - len(keep)
        if n:
            data["sessions"] = keep
            self.dir._save(data)
        return n
