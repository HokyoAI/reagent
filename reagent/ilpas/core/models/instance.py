from sqlmodel import Field

from .base import IlpasTenantModel, created_at_field, updated_at_field, uuid_field


class Instance(IlpasTenantModel, table=True):
    """Model for instances."""

    id: str = uuid_field()
    created_at: str = created_at_field()
    updated_at: str = updated_at_field()

    guid: str = Field(
        index=True,
        nullable=False,
        description="The globally unique identifier for the integration the instance belongs to.",
    )
