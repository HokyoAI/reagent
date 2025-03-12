from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, Field, Relationship, SQLModel


class LedgerEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ledger_id: UUID = Field(foreign_key="ledger.id")
    ledger: "Ledger" = Relationship(back_populates="entries")
    task_id: UUID
    entry_type: str
    data: JSON


class Ledger(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    entries: List[LedgerEntry] = Relationship(back_populates="ledger")
