import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from ..auth import get_user
from ..models import (
    StorageOwnerStatus,
    StorageOwnerStatusChange,
    StorageOwnerStatusChangeUpdate,
    StorageOwnerStatusNotes,
    engine,
)

secure_router = APIRouter()

@secure_router.get("/user")
async def get_secure_route(user: dict = Depends(get_user)):
    return user


@secure_router.get("/ncq/eligibility/{username}")
def get_user_eligibility(username: str):
    with Session(engine) as session:
        statement = select(StorageOwnerStatus).where(StorageOwnerStatus.username == username)
        result = session.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, "eligibility": result}


@secure_router.get("/ncq/eligibility")
def get_ncq_eligibility(start: int = 0, rows: int = 100):
    with Session(engine) as session:
        statement = select(func.count(StorageOwnerStatus.username))
        total_count = session.exec(statement).one()
        statement = select(StorageOwnerStatus).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No more users found")
    return {"start": start, "rows": rows, "total_count": total_count, "results": result}


@secure_router.get("/storage-owner-status-change/{username}")
def get_storage_owner_status_change(username: str, start: int = 0, rows: int = 100):
    with Session(engine) as session:
        statement = select(StorageOwnerStatusChange).where(StorageOwnerStatusChange.username == username)
        total_count = session.exec(select(func.count()).select_from(statement.subquery())).one()
        statement = statement.order_by(StorageOwnerStatusChange.date.desc()).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No status changes found for user")
    return {"username": username, "start": start, "rows": rows, "total_count": total_count, "results": result}


@secure_router.get("/storage-owner-status-change")
def get_storage_owner_status_changes(reviewed_by_rdms: Optional[str] = None, start: int = 0, rows: int = 100):
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

        result = [{**change.model_dump(), "notes": notes_by_username[change.username]} for change in changes]
    return {"start": start, "rows": rows, "total_count": total_count, "results": result}


@secure_router.patch("/storage-owner-status-change/{username}/{change_date}")
def update_storage_owner_status_change(
    username: str,
    change_date: datetime.date,
    payload: StorageOwnerStatusChangeUpdate,
):
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
def get_storage_owner_status_notes(username: str, start: int = 0, rows: int = 100):
    with Session(engine) as session:
        statement = select(StorageOwnerStatusNotes).where(StorageOwnerStatusNotes.username == username)
        total_count = session.exec(select(func.count()).select_from(statement.subquery())).one()
        statement = statement.order_by(StorageOwnerStatusNotes.note_timestamp.desc()).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No notes found for user")
    return {"username": username, "start": start, "rows": rows, "total_count": total_count, "results": result}