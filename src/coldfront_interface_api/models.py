from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Text, DECIMAL, text
import decimal
from typing import Optional


class StorageOwnerStatus(SQLModel, table=True):
    __tablename__ = 'storage_owner_status'

    username: str = Field(sa_column=Column('username', String(50), primary_key=True))
    ncq_tier_1: decimal.Decimal = Field(sa_column=Column('ncq_tier_1', DECIMAL(5, 2), nullable=False, server_default=text('0.00')))
    ncq_tier_2: decimal.Decimal = Field(sa_column=Column('ncq_tier_2', DECIMAL(5, 2), nullable=False, server_default=text('0.00')))
    no_cost_quota_eligible: Optional[str] = Field(default=None, sa_column=Column('no_cost_quota_eligible', String(5)))
    is_faculty: Optional[str] = Field(default=None, sa_column=Column('is_faculty', Text))
    pi_eligible: Optional[str] = Field(default=None, sa_column=Column('pi_eligible', String(5)))
    status_category: Optional[str] = Field(default=None, sa_column=Column('status_category', Text))
    dean_provost_status: Optional[str] = Field(default=None, sa_column=Column('dean_provost_status', String(5)))
    hr_title_primary_clean: Optional[str] = Field(default=None, sa_column=Column('hr_title_primary_clean', Text))
    hr_title_secondary_clean: Optional[str] = Field(default=None, sa_column=Column('hr_title_secondary_clean', Text))
    med_title_clean: Optional[str] = Field(default=None, sa_column=Column('med_title_clean', Text))
    title_prioritize_faculty: Optional[str] = Field(default=None, sa_column=Column('title_prioritize_faculty', Text))
    dean_provost_status: Optional[str] = Field(default=None, sa_column=Column('dean_provost_status', String(5)))
    hr_title_primary_clean: Optional[str] = Field(default=None, sa_column=Column('hr_title_primary_clean', Text))
    hr_title_secondary_clean: Optional[str] = Field(default=None, sa_column=Column('hr_title_secondary_clean', Text))
    med_title_clean: Optional[str] = Field(default=None, sa_column=Column('med_title_clean', Text))
    title_prioritize_faculty: Optional[str] = Field(default=None, sa_column=Column('title_prioritize_faculty', Text))
    tmc: Optional[str] = Field(default=None, sa_column=Column('tmc', Text))
    current_project_owner: Optional[str] = Field(default=None, sa_column=Column('current_project_owner', Text))
