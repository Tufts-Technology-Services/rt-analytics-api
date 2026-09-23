import datetime
import decimal
import os
from typing import Literal, Optional

from sqlalchemy import CHAR, DECIMAL, Column, Date, DateTime, Index, Integer, String, Text, text
from sqlmodel import Field, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "mysql://localhost:3306")
engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True, pool_recycle=1800)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

class StorageOwnerStatus(SQLModel, table=True):
    __tablename__ = 'storage_owner_status'

    username: str = Field(sa_column=Column('username', String(50), primary_key=True))
    ncq_tier_1: decimal.Decimal = Field(
        sa_column=Column('ncq_tier_1', DECIMAL(5, 2), nullable=False, server_default=text('0.00'))
    )
    ncq_tier_2: decimal.Decimal = Field(
        sa_column=Column('ncq_tier_2', DECIMAL(5, 2), nullable=False, server_default=text('0.00'))
    )
    no_cost_quota_eligible: Optional[str] = Field(default=None, sa_column=Column('no_cost_quota_eligible', String(5)))
    is_faculty: Optional[str] = Field(default=None, sa_column=Column('is_faculty', Text))
    pi_eligible: Optional[str] = Field(default=None, sa_column=Column('pi_eligible', String(5)))
    status_category: Optional[str] = Field(default=None, sa_column=Column('status_category', Text))
    dean_provost_status: Optional[str] = Field(default=None, sa_column=Column('dean_provost_status', String(5)))
    hr_title_primary_clean: Optional[str] = Field(default=None, sa_column=Column('hr_title_primary_clean', Text))
    hr_title_secondary_clean: Optional[str] = Field(default=None, sa_column=Column('hr_title_secondary_clean', Text))
    med_title_clean: Optional[str] = Field(default=None, sa_column=Column('med_title_clean', Text))
    title_prioritize_faculty: Optional[str] = Field(default=None, sa_column=Column('title_prioritize_faculty', Text))
    tmc: Optional[str] = Field(default=None, sa_column=Column('tmc', Text))
    current_project_owner: Optional[str] = Field(default=None, sa_column=Column('current_project_owner', Text))


class StorageOwnerStatusChange(SQLModel, table=True):
    __tablename__ = 'storage_owner_status_change'
    __table_args__ = (
        Index('idx_review_queue', 'reviewed_by_rdms', 'date'),
        Index('idx_username', 'username'),
    )

    date: datetime.date = Field(sa_column=Column('date', Date, primary_key=True, nullable=False))
    username: str = Field(sa_column=Column('username', String(25), primary_key=True, nullable=False))
    current_project_owner: Optional[str] = Field(default=None, sa_column=Column('current_project_owner', CHAR(3)))
    current_project_approver: Optional[str] = Field(default=None, sa_column=Column('current_project_approver', CHAR(3)))
    current_ncq_sharer: Optional[str] = Field(default=None, sa_column=Column('current_ncq_sharer', CHAR(3)))
    ncq_eligible_old: Optional[str] = Field(default=None, sa_column=Column('ncq_eligible_old', CHAR(3)))
    ncq_eligible_new: Optional[str] = Field(default=None, sa_column=Column('ncq_eligible_new', CHAR(3)))
    active_status_old: Optional[str] = Field(default=None, sa_column=Column('active_status_old', CHAR(1)))
    active_status_new: Optional[str] = Field(default=None, sa_column=Column('active_status_new', CHAR(1)))
    title_old: Optional[str] = Field(default=None, sa_column=Column('title_old', String(255)))
    title_new: Optional[str] = Field(default=None, sa_column=Column('title_new', String(255)))
    primary_affiliation_old: Optional[str] = Field(
        default=None, sa_column=Column('primary_affiliation_old', String(25))
    )
    primary_affiliation_new: Optional[str] = Field(
        default=None, sa_column=Column('primary_affiliation_new', String(25))
    )
    reviewed_by_rdms: str = Field(
        sa_column=Column('reviewed_by_rdms', CHAR(3), nullable=False, server_default=text("'No'"))
    )
    review_date: Optional[datetime.date] = Field(default=None, sa_column=Column('review_date', Date))
    ncq_expiration_date: Optional[datetime.date] = Field(default=None, sa_column=Column('ncq_expiration_date', Date))


class StorageOwnerStatusNotes(SQLModel, table=True):
    __tablename__ = 'storage_owner_status_notes'
    __table_args__ = (
        Index('idx_author', 'author_utln'),
        Index('idx_username_ts', 'username', 'note_timestamp'),
    )

    id: Optional[int] = Field(default=None, sa_column=Column('id', Integer, primary_key=True, autoincrement=True))
    note_timestamp: datetime.datetime = Field(
        sa_column=Column('note_timestamp', DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    )
    username: str = Field(sa_column=Column('username', String(25), nullable=False))
    author_utln: str = Field(sa_column=Column('author_utln', String(25), nullable=False))
    note: str = Field(sa_column=Column('note', Text, nullable=False))


class StorageOwnerStatusChangeUpdate(SQLModel):
    """At least one of reviewed_by_rdms, ncq_expiration_date, or note must be provided."""

    author_utln: str = Field(
        description="Tufts username (UTLN) of the person making this update. "
        "Used as the author on any note created by this request."
    )
    reviewed_by_rdms: Optional[Literal['Yes', 'No']] = Field(
        default=None,
        description="RDMS review status to set. Must be 'Yes' or 'No'. "
        "Ignored if ncq_expiration_date is also provided, since that always sets it to 'Yes'.",
    )
    ncq_expiration_date: Optional[datetime.date] = Field(
        default=None,
        description="Grace-period expiration date to set, in ISO 8601 format (YYYY-MM-DD). "
        "Setting this always sets reviewed_by_rdms to 'Yes' and adds a "
        "'Grace period granted until <date>' note automatically.",
    )
    note: Optional[str] = Field(
        default=None,
        description="Free-text note to add, in addition to any note generated automatically by this update.",
    )


class APIUser(SQLModel, table=True):
    __tablename__ = 'api_users'

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column('username', String(50), unique=True, nullable=False))
    api_key: str = Field(sa_column=Column('api_key', String(100), unique=True, nullable=False))


create_db_and_tables()
