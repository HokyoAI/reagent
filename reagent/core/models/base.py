from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as SA_UUID
from sqlalchemy.sql import func
from sqlmodel import Field, MetaData, SQLModel


def uuid_field():
    return Field(
        sa_column=Column(
            SA_UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
            nullable=False,
        )
    )


def utcnow():
    return datetime.now(timezone.utc)


def created_at_field():
    return Field(sa_column=Column(DateTime(timezone=True), default=utcnow))


def updated_at_field():
    return Field(sa_column=Column(DateTime(timezone=True), onupdate=utcnow))


def labels_field():
    """Create a JSONB field with GIN index for efficient querying of labels."""
    return Field(sa_column=Column(JSONB, nullable=False))


SHARED_SCHEMA = "shared"
NS_DEFAULT_SCHEMA = None

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_`%(constraint_name)s`",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class BasementModel(SQLModel):
    """Base model for all models in the system including in extensions."""

    metadata = MetaData(naming_convention=naming_convention)


class ReagentModel(BasementModel):
    pass


class SharedModel(BasementModel):
    """Base model for shared models."""

    # All shared models will automatically use the shared schema
    __table_args__ = {"schema": SHARED_SCHEMA}


class NamespaceModel(BasementModel):
    """Base model for namespace'd schema models."""

    __table_args__ = {"schema": NS_DEFAULT_SCHEMA}


class ReagentSharedModel(ReagentModel, SharedModel):
    pass


class ReagentNamespaceModel(ReagentModel, NamespaceModel):
    pass


def get_reagent_shared_metadata() -> MetaData:
    """Get the metadata for the shared schema."""
    meta = MetaData(naming_convention=naming_convention)
    for table in ReagentSharedModel.metadata.tables.values():
        if table.schema == SHARED_SCHEMA:
            table.to_metadata(meta)

    return meta


def get_reagent_namespace_metadata() -> MetaData:
    """Get the metadata for the namespace schemas."""
    meta = MetaData(naming_convention=naming_convention)
    for table in ReagentNamespaceModel.metadata.tables.values():
        if table.schema == NS_DEFAULT_SCHEMA:
            table.to_metadata(meta)

    return meta
