"""scripts/set_user_role.py attaches ADR-029's role claim to an account, and takes it away.

Driven over a fake of firebase_admin.auth, so no test touches the real project. The claim is
the single source the edge gate and the Firestore rules read, so what matters is exactly
which claims end up on the account, and that revoking also ends the person's sessions.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.set_user_role import main  # noqa: E402


class FakeAuth:
    class UserNotFoundError(Exception):
        pass

    def __init__(self, users):
        self.users = users  # email -> {"uid", "custom_claims"}
        self.revoked = []

    def get_user_by_email(self, email):
        if email not in self.users:
            raise self.UserNotFoundError(email)
        u = self.users[email]
        return type("User", (), {"uid": u["uid"], "email": email, "custom_claims": u.get("custom_claims")})()

    def set_custom_user_claims(self, uid, claims):
        for u in self.users.values():
            if u["uid"] == uid:
                u["custom_claims"] = claims

    def revoke_refresh_tokens(self, uid):
        self.revoked.append(uid)


def _auth(claims=None):
    return FakeAuth({"person@example.com": {"uid": "u1", "custom_claims": claims}})


@pytest.mark.parametrize("role", ["owner", "team"])
def test_it_sets_the_role(role):
    auth = _auth()
    assert main(["person@example.com", role], auth=auth) == 0
    assert auth.users["person@example.com"]["custom_claims"] == {"role": role}


def test_it_keeps_any_other_claim_on_the_account():
    auth = _auth({"beta": True, "role": "team"})
    main(["person@example.com", "owner"], auth=auth)
    assert auth.users["person@example.com"]["custom_claims"] == {"beta": True, "role": "owner"}


def test_revoking_removes_the_role_and_ends_the_sessions():
    auth = _auth({"role": "team"})
    assert main(["person@example.com", "--revoke"], auth=auth) == 0
    assert auth.users["person@example.com"]["custom_claims"] is None
    assert auth.revoked == ["u1"]


def test_show_changes_nothing(capsys):
    auth = _auth({"role": "owner"})
    assert main(["person@example.com", "--show"], auth=auth) == 0
    assert auth.users["person@example.com"]["custom_claims"] == {"role": "owner"}
    assert "owner" in capsys.readouterr().out


def test_an_unknown_role_is_refused_before_anything_is_touched():
    auth = _auth()
    with pytest.raises(SystemExit) as exit_:
        main(["person@example.com", "admin"], auth=auth)
    assert exit_.value.code == 2
    assert auth.users["person@example.com"]["custom_claims"] is None


def test_an_account_that_never_signed_in_is_named_and_not_created(capsys):
    auth = _auth()
    assert main(["nobody@example.com", "team"], auth=auth) == 1
    assert "sign in once" in capsys.readouterr().err
    assert list(auth.users) == ["person@example.com"]
