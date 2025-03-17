from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from reagent.core.models.base import (
    ReagentNamespaceModel,
    ReagentSharedModel,
    created_at_field,
    labels_field,
    updated_at_field,
    uuid_field,
)


class HKRA_Dummy(ReagentSharedModel, table=True):
    """A dummy model for shared schema, used for migrations and testing."""

    id: Optional[UUID] = uuid_field()
    created_at: Optional[datetime] = created_at_field()
    updated_at: Optional[datetime] = updated_at_field()


class Thread(ReagentNamespaceModel, table=True):
    id: Optional[UUID] = uuid_field()
    created_at: Optional[datetime] = created_at_field()
    updated_at: Optional[datetime] = updated_at_field()
    invocations: List["Invocation"] = Relationship(back_populates="thread")
    labels: dict = labels_field()


Index(None, Thread.labels, postgresql_using="gin")  # type: ignore


class Invocation(ReagentNamespaceModel, table=True):
    id: Optional[UUID] = uuid_field()
    created_at: Optional[datetime] = created_at_field()
    updated_at: Optional[datetime] = updated_at_field()
    thread_id: UUID = Field(foreign_key="thread.id")
    thread: Thread = Relationship(back_populates="invocations")
    completed: bool
    ledger: List["LedgerEntry"] = Relationship(back_populates="invocation")


class LedgerEntry(ReagentNamespaceModel, table=True):
    id: Optional[UUID] = uuid_field()
    created_at: Optional[datetime] = created_at_field()
    updated_at: Optional[datetime] = updated_at_field()
    invocation_id: UUID = Field(foreign_key="invocation.id")
    invocation: Invocation = Relationship(back_populates="ledger")
    source: str  # formatted string as taskable . function  ?
    closing: bool  # Whether this is the opening entry or closing entry for this source. Should be balanced
    data: dict = Field(..., sa_type=JSONB)  # JSONB field for storing arbitrary data
