"""The gaps this package exists to refuse, each asserted as a refusal.

The dangerous failures in an identity store are all *silent successes*: a
session that outlives the account, a corrupt file that reads as an empty
directory, a token that still works after revocation. So every test below drives
the system into that state and asserts it is refused, with the reason.
"""

import json

import pytest

from awiam import Directory, DirectoryUnreadableError, Sessions, Subject


def store(tmp_path):
    d = Directory(tmp_path / "iam.json")
    d.put(Subject(id="david", display="David", email="d@example.com"))
    return d


def test_issue_and_resolve(tmp_path):
    d = store(tmp_path)
    tok = Sessions(d).issue("david")
    r = Sessions(d).resolve(tok)
    assert r and r.subject_id == "david"


def test_deactivation_kills_live_sessions_immediately(tmp_path):
    """The failure everyone means by 'we removed their access and they were
    still in'."""
    d = store(tmp_path)
    tok = Sessions(d).issue("david")
    assert Sessions(d).resolve(tok)

    d.deactivate("david")
    r = Sessions(d).resolve(tok)
    assert not r
    assert "deactivated" in r.reason or "unknown token" in r.reason


def test_cannot_issue_to_a_deactivated_subject(tmp_path):
    """Refused at ISSUE too — otherwise reactivating the account revives every
    token minted while it was disabled."""
    d = store(tmp_path)
    d.deactivate("david")
    assert Sessions(d).issue("david") is None


def test_expired_session_is_refused_and_says_so(tmp_path):
    d = store(tmp_path)
    s = Sessions(d, ttl=-1)             # already expired
    tok = s.issue("david")
    r = Sessions(d).resolve(tok)
    assert not r and r.reason == "session expired"


def test_revoked_token_stops_working(tmp_path):
    d = store(tmp_path)
    s = Sessions(d)
    tok = s.issue("david")
    assert s.revoke(tok)
    assert not Sessions(d).resolve(tok)


def test_unknown_and_empty_tokens_are_refused(tmp_path):
    d = store(tmp_path)
    assert not Sessions(d).resolve("")
    assert not Sessions(d).resolve("not-a-real-token")


def test_session_whose_subject_vanished_is_refused(tmp_path):
    d = store(tmp_path)
    tok = Sessions(d).issue("david")
    raw = json.loads(d.path.read_text(encoding="utf-8"))
    del raw["subjects"]["david"]        # subject removed out from under the session
    d.path.write_text(json.dumps(raw), encoding="utf-8")
    r = Sessions(d).resolve(tok)
    assert not r and "no longer exists" in r.reason


def test_tokens_are_not_stored_in_the_clear(tmp_path):
    """The store gets backed up, copied, pasted into issues. Live tokens in it
    are credentials in all of those places."""
    d = store(tmp_path)
    tok = Sessions(d).issue("david")
    assert tok not in d.path.read_text(encoding="utf-8")


def test_corrupt_store_raises_rather_than_reading_as_empty(tmp_path):
    """An empty directory denies everyone while looking healthy; a caller that
    treats absence as 'first run' would recreate it and lose every identity."""
    d = store(tmp_path)
    d.path.write_text("{not json", encoding="utf-8")
    with pytest.raises(DirectoryUnreadableError):
        d.get("david")


def test_purge_only_removes_expired(tmp_path):
    d = store(tmp_path)
    live = Sessions(d).issue("david")
    Sessions(d, ttl=-1).issue("david")
    assert Sessions(d).purge_expired() == 1
    assert Sessions(d).resolve(live), "purge must not touch a live session"
