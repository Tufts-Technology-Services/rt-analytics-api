import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlmodel import Session, func, select

from ..auth import get_user
from ..models import (
    PrFis,
    StorageOwnerStatus,
    StorageOwnerStatusChange,
    StorageOwnerStatusChangeUpdate,
    StorageOwnerStatusNotes,
    engine,
)

secure_router = APIRouter()

# Shared pagination parameters, reused across the list endpoints below.
START_PARAM = Query(default=0, ge=0, description="Number of matching records to skip, for pagination.")
ROWS_PARAM = Query(default=100, ge=1, le=500, description="Maximum number of records to return (1-500).")

@secure_router.get("/user")
async def get_secure_route(user: dict = Depends(get_user)):
    """Return the identity of the authenticated caller, as resolved from the API key."""
    return user


@secure_router.get("/ncq/eligibility/{username}")
def get_user_eligibility(
    username: str = Path(description="Tufts username (UTLN) to look up."),
):
    """Get the no-cost-quota (NCQ) eligibility record for a single user."""
    with Session(engine) as session:
        statement = select(StorageOwnerStatus).where(StorageOwnerStatus.username == username)
        result = session.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, "eligibility": result}


@secure_router.get("/ncq/eligibility")
def get_ncq_eligibility(start: int = START_PARAM, rows: int = ROWS_PARAM):
    """List no-cost-quota (NCQ) eligibility records for all users, paginated."""
    with Session(engine) as session:
        statement = select(func.count(StorageOwnerStatus.username))
        total_count = session.exec(statement).one()
        statement = select(StorageOwnerStatus).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No more users found")
    return {"start": start, "rows": rows, "total_count": total_count, "results": result}


@secure_router.get("/storage-owner-status-change/{username}")
def get_storage_owner_status_change(
    username: str = Path(description="Tufts username (UTLN) to look up."),
    start: int = START_PARAM,
    rows: int = ROWS_PARAM,
):
    """List storage-owner status-change history for a single user, most recent first."""
    with Session(engine) as session:
        statement = select(StorageOwnerStatusChange).where(StorageOwnerStatusChange.username == username)
        total_count = session.exec(select(func.count()).select_from(statement.subquery())).one()
        statement = statement.order_by(StorageOwnerStatusChange.date.desc()).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No status changes found for user")
    return {"username": username, "start": start, "rows": rows, "total_count": total_count, "results": result}


@secure_router.get("/storage-owner-status-change")
def get_storage_owner_status_changes(
    reviewed_by_rdms: Optional[Literal['Yes', 'No']] = Query(
        default=None, description="If set, only return records with this RDMS review status."
    ),
    start: int = START_PARAM,
    rows: int = ROWS_PARAM,
):
    """List storage-owner status-change records across all users, most recent first.

    Each result has any related notes (same username) attached under "notes", and the owner's
    "full_name" and "email" attached from pr_fis, if a matching identity record exists.
    """
    with Session(engine) as session:
        statement = select(StorageOwnerStatusChange)
        if reviewed_by_rdms is not None:
            statement = statement.where(StorageOwnerStatusChange.reviewed_by_rdms == reviewed_by_rdms)
        total_count = session.exec(select(func.count()).select_from(statement.subquery())).one()
        statement = statement.order_by(StorageOwnerStatusChange.date.desc()).limit(rows).offset(start)
        changes = session.exec(statement).all()
        if not changes:
            raise HTTPException(status_code=404, detail="No status changes found")

        usernames = {change.username for change in changes}
        notes_statement = select(StorageOwnerStatusNotes).where(
            StorageOwnerStatusNotes.username.in_(usernames)
        ).order_by(StorageOwnerStatusNotes.note_timestamp.desc())
        notes_by_username = {username: [] for username in usernames}
        for note in session.exec(notes_statement).all():
            notes_by_username[note.username].append(note)

        identity_statement = select(PrFis).where(PrFis.pr_identity_utln.in_(usernames))
        identity_by_username = {}
        for identity in session.exec(identity_statement).all():
            name_parts = [
                identity.pr_identity_firstname,
                identity.pr_identity_middlename,
                identity.pr_identity_lastname,
            ]
            identity_by_username[identity.pr_identity_utln] = {
                "full_name": " ".join(part for part in name_parts if part),
                "email": identity.pr_identity_email,
            }

        result = [
            {
                **change.model_dump(),
                "notes": notes_by_username[change.username],
                **identity_by_username.get(change.username, {"full_name": None, "email": None}),
            }
            for change in changes
        ]
    return {"start": start, "rows": rows, "total_count": total_count, "results": result}


@secure_router.patch("/storage-owner-status-change/{username}/{change_date}")
def update_storage_owner_status_change(
    payload: StorageOwnerStatusChangeUpdate,
    username: str = Path(description="Tufts username (UTLN) of the storage owner."),
    change_date: datetime.date = Path(
        description="Date of the status-change record to update, in ISO 8601 format (YYYY-MM-DD)."
    ),
):
    """Update RDMS review status and/or NCQ grace period on one status-change record, and/or add a note.

    At least one of reviewed_by_rdms, ncq_expiration_date, or note must be provided in the body.

    - review_date is set automatically (to today) when reviewed_by_rdms transitions from 'No' to
      'Yes' — it cannot be set directly.
    - Providing ncq_expiration_date always sets reviewed_by_rdms to 'Yes', regardless of what (if
      anything) was passed for reviewed_by_rdms, and adds an automatic
      "Grace period granted until <date>" note.
    - Otherwise, a 'No' -> 'Yes' transition on reviewed_by_rdms adds an automatic "Reviewed" note.
    - Any note text supplied in the body is added in addition to the automatic note, if any.

    Returns the updated status-change record and the list of notes created by this request
    (which may be empty).
    """
    if all(
        value is None
        for value in (payload.reviewed_by_rdms, payload.ncq_expiration_date, payload.note)
    ):
        raise HTTPException(status_code=400, detail="No fields to update")

    with Session(engine) as session:
        statement = select(StorageOwnerStatusChange).where(
            StorageOwnerStatusChange.username == username,
            StorageOwnerStatusChange.date == change_date,
        )
        change = session.exec(statement).first()
        if not change:
            raise HTTPException(status_code=404, detail="Status change not found")

        reviewed_by_rdms = 'Yes' if payload.ncq_expiration_date is not None else payload.reviewed_by_rdms
        newly_reviewed = reviewed_by_rdms is not None and change.reviewed_by_rdms == 'No' and reviewed_by_rdms == 'Yes'
        if reviewed_by_rdms is not None:
            if newly_reviewed:
                change.review_date = datetime.date.today()
            change.reviewed_by_rdms = reviewed_by_rdms
        if payload.ncq_expiration_date is not None:
            change.ncq_expiration_date = payload.ncq_expiration_date
        session.add(change)

        note_texts = []
        if payload.ncq_expiration_date is not None:
            note_texts.append(f"Grace period granted until {payload.ncq_expiration_date}")
        elif newly_reviewed:
            note_texts.append("Reviewed")
        if payload.note is not None:
            note_texts.append(payload.note)

        notes = [
            StorageOwnerStatusNotes(username=username, author_utln=payload.author_utln, note=note_text)
            for note_text in note_texts
        ]
        for note in notes:
            session.add(note)

        session.commit()
        session.refresh(change)
        for note in notes:
            session.refresh(note)

    return {"change": change, "notes": notes}


@secure_router.get("/storage-owner-status-notes/{username}")
def get_storage_owner_status_notes(
    username: str = Path(description="Tufts username (UTLN) to look up."),
    start: int = START_PARAM,
    rows: int = ROWS_PARAM,
):
    """List notes for a single user, most recent first."""
    with Session(engine) as session:
        statement = select(StorageOwnerStatusNotes).where(StorageOwnerStatusNotes.username == username)
        total_count = session.exec(select(func.count()).select_from(statement.subquery())).one()
        statement = statement.order_by(StorageOwnerStatusNotes.note_timestamp.desc()).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No notes found for user")
    return {"username": username, "start": start, "rows": rows, "total_count": total_count, "results": result}