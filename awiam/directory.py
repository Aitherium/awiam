"""The directory: who exists, and what is true about them.

Deliberately NOT an authorization store. `awiam` answers *who is this caller*;
`awbac` answers *what may they do*; `awseal` holds *what proves it*. An identity
service that also owns authorization has nobody to check it, and one that owns
its own key material has nobody to attest it — so the seam is kept even though
merging them would be less code.

Storage is a single JSON file, read fresh per call. Not a performance decision:
an identity store that caches is one that keeps answering after a revocation,
and "the user is still logged in three minutes after you disabled them" is the
failure this shape has to refuse. If it ever needs a cache, the revocation path
has to invalidate it, and that is a design change rather than an optimisation.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Subject:
    """A person or a machine. `id` is the only thing other packages should key on."""
    id: str
    display: str = ""
    email: str = ""
    #: False disables sign-in AND invalidates existing sessions. Two separate
    #: things elsewhere, one flag here, because a disabled account that keeps a
    #: live session is the exact gap people mean by "we disabled them".
    active: bool = True
    attrs: dict = field(default_factory=dict)


class Directory:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    # ── storage ─────────────────────────────────────────────────────────────
    def _load(self) -> dict:
        if not self.path.is_file():
            return {"subjects": {}, "sessions": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # A corrupt store is NOT an empty one. Returning {} would make every
            # lookup answer "no such subject", which reads as a clean directory
            # and silently denies everyone -- or, in a caller that treats absence
            # as "first run", quietly recreates it empty.
            raise DirectoryUnreadableError(f"{self.path} exists but does not parse")

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)     # atomic; a torn write loses every identity

    # ── subjects ────────────────────────────────────────────────────────────
    def put(self, subject: Subject) -> Subject:
        data = self._load()
        data["subjects"][subject.id] = asdict(subject)
        self._save(data)
        return subject

    def get(self, subject_id: str) -> Subject | None:
        if not subject_id:
            return None
        raw = self._load()["subjects"].get(subject_id)
        return Subject(**raw) if raw else None

    def list(self) -> list[Subject]:
        return [Subject(**r) for r in self._load()["subjects"].values()]

    def deactivate(self, subject_id: str) -> bool:
        """Disable the subject AND drop their sessions, in one operation.

        Two calls would leave a window in which the account is disabled and the
        session still resolves -- and that window is precisely when someone is
        being removed for cause.
        """
        data = self._load()
        raw = data["subjects"].get(subject_id)
        if not raw:
            return False
        raw["active"] = False
        data["sessions"] = {t: s for t, s in data["sessions"].items()
                            if s.get("subject") != subject_id}
        self._save(data)
        return True


class DirectoryUnreadableError(RuntimeError):
    """Raised rather than returning empty. Callers must distinguish 'no such
    subject' from 'I could not read the directory' — they call for opposite
    responses, and conflating them denies everyone while looking healthy."""
