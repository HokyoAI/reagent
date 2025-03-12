import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from hatchet_sdk import Hatchet
from pydantic import ValidationError

from reagent.core.dependencies.hatchet import get_hatchet

logger = logging.getLogger(__name__)


class Catalog:

    def __init__(self):
        self.finalized: bool = False
        self._taskable_registry: dict[str, Taskable] = {}

    def add_taskable(self, *, taskable: Taskable):
        if self.finalized:
            raise RuntimeError("Catalog is finalized, cannot add more taskables")
        if integration.spec.guid in self._integration_registry:
            raise ValueError(f"Integration {integration.spec.guid} already exists")

        self._integration_registry[integration.spec.guid] = integration

    def finalize(self):
        if self.finalized:
            raise RuntimeError("Catalog is already finalized")
        self.finalized = True

    def router(
        self,
        *,
        http_authenticate: Callable[..., Awaitable[tuple[str, Labels] | None]],
        include_info: bool = True,
        include_connect: bool = True,
    ) -> APIRouter:
        if not self.finalized:
            raise RuntimeError("Catalog is not finalized, cannot create router")

        # order matters !
        self._http_authenticate = http_authenticate
        self._create_enabled_integrations_enum()
        self._create_dependency_functions()

        catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])
        if include_info:
            catalog_router.include_router(self._build_info_router())
        if include_connect:
            catalog_router.include_router(self._build_connect_router())

        return catalog_router

    def worker(self):
        if not self.finalized:
            raise RuntimeError("Catalog is not finalized, cannot create worker")

    def _create_enabled_integrations_enum(self):
        members = {key.upper(): key for key in self._integration_registry.keys()}
        self._enabled_integrations_enum = StrEnum("EnabledIntegrations", members)

    def _create_dependency_functions(self):
        self._require_authentication_dep = (
            self._build_require_authentication_dependency()
        )
        self._validate_guid_dep = self._build_validate_guid_dependency()
        self._try_load_instance_dep = self._build_try_load_instance_dependency()
        self._require_instance_dep = self._build_require_instance_dependency()

    def _build_require_authentication_dependency(self):

        async def require_authentication(
            identity: Annotated[
                tuple[str, Labels] | None, Depends(self._http_authenticate)
            ],
        ):
            if identity is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return identity

        return require_authentication

    def _build_validate_guid_dependency(self):
        async def validate_guid(guid: self._enabled_integrations_enum):  # type: ignore
            if guid not in self._integration_registry:
                raise HTTPException(status_code=404, detail="Integration not found")
            return guid

        return validate_guid

    def _build_try_load_instance_dependency(self):

        async def try_load_instance(
            guid: Annotated[str, Depends(self._validate_guid_dep)],
            identity: Annotated[
                tuple[str, Labels], Depends(self._require_authentication_dep)
            ],
        ) -> Instance | None:
            """Load an instance from the store. If not found, return None"""
            try:
                integration = self._integration_registry[guid]
                instance = await Instance.restore_by_labels(
                    store=self._store,
                    integration=integration,
                    namespace=identity[0],
                    labels=identity[1],
                )  # will raise NotFoundException if not found
                return instance
            except NotFoundException:
                return None

        return try_load_instance

    def _build_require_instance_dependency(self):
        async def require_instance(
            instance: Annotated[Instance | None, Depends(self._try_load_instance_dep)],
        ) -> Instance:
            """Load an instance from the store. If not found, raise an error."""
            if instance is None:
                raise HTTPException(status_code=404, detail="Instance not found")
            return instance

        return require_instance

    def _build_get_catalog_info_handler(self):
        async def get_catalog_handler():
            return [
                {
                    "guid": guid,
                    "display": self._integration_registry[
                        guid
                    ].spec.display.model_dump(),
                }
                for guid in self._integration_registry
            ]

        return get_catalog_handler

    def _build_get_enabled_integrations_handler(self):
        async def get_enabled_integrations():
            return list(self._integration_registry.keys())

        return get_enabled_integrations

    def _build_get_integration_info_handler(self):
        async def get_integration(
            guid: Annotated[str, Depends(self._validate_guid_dep)],
        ):
            return self._integration_registry[guid].spec.display

        return get_integration

    def _build_get_integration_schema_handler(self):
        """
        Uses a temporary instance to avoid loading the configuration through the _load_instance_dep dependency.
        """

        async def get_integration_schema(
            guid: Annotated[str, Depends(self._validate_guid_dep)],
        ):
            return self._integration_registry[
                guid
            ].spec.user_config_model.model_json_schema()

        return get_integration_schema

    def _build_info_router(self) -> APIRouter:
        info_router = APIRouter(tags=["info"])

        get_catalog_info_handler = self._build_get_catalog_info_handler()
        get_enabled_integrations_handler = (
            self._build_get_enabled_integrations_handler()
        )
        get_integration_info_handler = self._build_get_integration_info_handler()
        get_integration_schema_handler = self._build_get_integration_schema_handler()
        info_router.get("/info/")(get_catalog_info_handler)
        info_router.get("/enabled/")(get_enabled_integrations_handler)
        info_router.get("/{guid}/info/")(get_integration_info_handler)
        info_router.get("/{guid}/schema/")(get_integration_schema_handler)

        return info_router
