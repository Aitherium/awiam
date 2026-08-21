# awiam

**Who is this caller?** A directory and session store where deactivation is
immediate and a corrupt store is never mistaken for an empty one.

```bash
pip install awiam
```

```python
from awiam import Directory, Sessions, Subject

d = Directory("iam.json")
d.put(Subject(id="david", email="d@example.com"))

s = Sessions(d)
token = s.issue("david")

r = s.resolve(token)
if r:
    print(r.subject_id)      # david
else:
    print(r.reason)          # every refusal says why
```

```bash
awiam --store iam.json add david --email d@example.com
awiam --store iam.json issue david
awiam --store iam.json resolve <token>      # 0 resolved · 1 refused · 2 could not judge
awiam --store iam.json deactivate david
```

## The failures it refuses

Everything dangerous in an identity store is a **silent success**, so each of
these is a refusal that names itself:

**A session that outlives its account.** `deactivate()` disables the subject and
drops their sessions in **one operation**. Two calls would leave a window where
the account is off and the token still resolves — and that window is exactly
when someone is being removed for cause.

```bash
awiam deactivate david
awiam resolve $TOKEN     # REFUSED: unknown token   (exit 1)
```

**Issuing to a disabled account.** Refused at `issue()`, not only at `resolve()`
— otherwise reactivating the account later revives every token minted while it
was off.

**A corrupt store reading as an empty one.** `Directory` raises
`DirectoryUnreadableError` rather than returning `{}`. An empty directory denies
everyone while looking perfectly healthy, and a caller that treats absence as
"first run" would recreate it and lose every identity. The CLI exits **2**, not
1: a refusal is a decision, this is the absence of one.

**Tokens in a file that gets copied.** Sessions are stored **hashed**. The store
gets backed up, pasted into an issue, copied to a laptop — live tokens in it are
credentials in all of those places. Comparison is constant-time; the leak is
small, entirely avoidable, and costs one stdlib call.

**A session pointing at a subject that vanished.** Resolution re-checks the
subject every time, so a deleted or disabled account cannot be reached through
an old token.

## What it deliberately does not do

It does **not** decide what you may do. That is [`awbac`](https://github.com/Aitherium/awbac).
It does **not** hold key material. That is [`awseal`](https://github.com/Aitherium/awseal).

| package | question |
|---|---|
| **`awiam`** | **who is this caller?** |
| `awbac` | may this subject do X to Y? |
| `awseal` | what proves it? |

Three packages on purpose. An identity service that also owns authorization has
nobody to check it; one that owns its own key material has nobody to attest it.
Merging them would be less code and a worse boundary.

## Design notes

- **No dependencies.** An identity check that needs a service to answer fails
  open the moment that service is unreachable — which is the one time it matters.
- **No cache.** The store is read fresh per call, deliberately: a cache is a
  thing that keeps answering after a revocation. Adding one is a design change
  that must invalidate on revoke, not an optimisation.
- **Atomic writes** (`os.replace`), because a torn write loses every identity.

## Tests

10 tests, each driving the system into a silent-success state and asserting the
refusal — including deactivation killing a live session, a corrupt store
raising, and a check that the issued token does not appear in the file.

```bash
pip install -e ".[dev]" && pytest
```

Apache-2.0.
