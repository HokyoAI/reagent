from reagent.core.models.base import (
    BasementModel,
    PublicModel,
    TenantModel,
    created_at_field,
    labels_field,
    updated_at_field,
    uuid_field,
)


class IlpasModel(BasementModel):
    pass


class IlpasPublicModel(IlpasModel, PublicModel):
    pass


class IlpasTenantModel(IlpasModel, TenantModel):
    pass
