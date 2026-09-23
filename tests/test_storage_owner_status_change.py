import datetime

from coldfront_interface_api.models import (
    StorageOwnerStatusChange,
    StorageOwnerStatusNotes,
)


def make_change(
    db_session,
    *,
    username="alice",
    change_date=datetime.date(2026, 1, 1),
    reviewed_by_rdms="No",
    review_date=None,
    ncq_expiration_date=None,
):
    change = StorageOwnerStatusChange(
        date=change_date,
        username=username,
        reviewed_by_rdms=reviewed_by_rdms,
        review_date=review_date,
        ncq_expiration_date=ncq_expiration_date,
    )
    db_session.add(change)
    db_session.commit()
    return change


def update_url(username, change_date):
    return f"/api/v1/secure/storage-owner-status-change/{username}/{change_date.isoformat()}"


def test_update_returns_404_when_change_not_found(client):
    response = client.patch(
        update_url("alice", datetime.date(2026, 1, 1)),
        json={"author_utln": "abc01", "reviewed_by_rdms": "Yes"},
    )
    assert response.status_code == 404


def test_update_requires_at_least_one_field(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    make_change(db_session, change_date=change_date)

    response = client.patch(
        update_url("alice", change_date),
        json={"author_utln": "abc01"},
    )
    assert response.status_code == 400


def test_update_missing_author_utln_is_rejected(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    make_change(db_session, change_date=change_date)

    response = client.patch(
        update_url("alice", change_date),
        json={"reviewed_by_rdms": "Yes"},
    )
    assert response.status_code == 422


def test_update_rejects_invalid_reviewed_by_rdms(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    make_change(db_session, change_date=change_date)

    response = client.patch(
        update_url("alice", change_date),
        json={"author_utln": "abc01", "reviewed_by_rdms": "Maybe"},
    )
    assert response.status_code == 422


def test_update_transition_to_yes_sets_review_date_and_reviewed_note(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    make_change(db_session, change_date=change_date, reviewed_by_rdms="No")

    response = client.patch(
        update_url("alice", change_date),
        json={"author_utln": "abc01", "reviewed_by_rdms": "Yes"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["change"]["reviewed_by_rdms"] == "Yes"
    assert body["change"]["review_date"] == datetime.date.today().isoformat()
    assert [n["note"] for n in body["notes"]] == ["Reviewed"]
    assert body["notes"][0]["author_utln"] == "abc01"


def test_update_already_yes_does_not_touch_review_date_or_add_note(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    existing_review_date = datetime.date(2025, 6, 1)
    make_change(
        db_session,
        change_date=change_date,
        reviewed_by_rdms="Yes",
        review_date=existing_review_date,
    )

    response = client.patch(
        update_url("alice", change_date),
        json={"author_utln": "abc01", "reviewed_by_rdms": "Yes"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["change"]["review_date"] == existing_review_date.isoformat()
    assert body["notes"] == []


def test_update_ncq_expiration_date_forces_yes_and_adds_grace_note(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    make_change(db_session, change_date=change_date, reviewed_by_rdms="No")
    expiration = datetime.date(2026, 6, 30)

    response = client.patch(
        update_url("alice", change_date),
        json={"author_utln": "abc01", "ncq_expiration_date": expiration.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["change"]["reviewed_by_rdms"] == "Yes"
    assert body["change"]["ncq_expiration_date"] == expiration.isoformat()
    assert body["change"]["review_date"] == datetime.date.today().isoformat()
    assert [n["note"] for n in body["notes"]] == [f"Grace period granted until {expiration.isoformat()}"]


def test_update_ncq_expiration_date_suppresses_reviewed_note_but_keeps_manual_note(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    make_change(db_session, change_date=change_date, reviewed_by_rdms="No")
    expiration = datetime.date(2026, 6, 30)

    response = client.patch(
        update_url("alice", change_date),
        json={
            "author_utln": "abc01",
            "ncq_expiration_date": expiration.isoformat(),
            "note": "Approved after department review",
        },
    )
    assert response.status_code == 200
    body = response.json()
    note_texts = [n["note"] for n in body["notes"]]
    assert note_texts == [
        f"Grace period granted until {expiration.isoformat()}",
        "Approved after department review",
    ]
    assert "Reviewed" not in note_texts


def test_get_storage_owner_status_changes_attaches_related_notes(client, db_session):
    change_date = datetime.date(2026, 1, 1)
    make_change(db_session, change_date=change_date, username="alice", reviewed_by_rdms="No")
    make_change(db_session, change_date=change_date, username="bob", reviewed_by_rdms="No")

    note = StorageOwnerStatusNotes(username="alice", author_utln="abc01", note="Some note")
    db_session.add(note)
    db_session.commit()

    response = client.get("/api/v1/secure/storage-owner-status-change")
    assert response.status_code == 200
    results_by_username = {r["username"]: r for r in response.json()["results"]}
    assert [n["note"] for n in results_by_username["alice"]["notes"]] == ["Some note"]
    assert results_by_username["bob"]["notes"] == []


def test_get_storage_owner_status_changes_filters_by_reviewed_by_rdms(client, db_session):
    make_change(db_session, change_date=datetime.date(2026, 1, 1), username="alice", reviewed_by_rdms="No")
    make_change(db_session, change_date=datetime.date(2026, 1, 2), username="bob", reviewed_by_rdms="Yes")

    response = client.get("/api/v1/secure/storage-owner-status-change", params={"reviewed_by_rdms": "Yes"})
    assert response.status_code == 200
    assert [r["username"] for r in response.json()["results"]] == ["bob"]
