from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar, Dict, Iterable, List, Literal, Optional, Set, Type

from pydantic import BaseModel

from .models.errors import ConflictError, NotFoundError
from .models.types import JsonValue

ALL_NAMESPACES = Literal["*"]


class StoreModel(BaseModel):
    """
    Base class for models that can be stored in a Store.

    Each StoreModel has tabular fields that can be queried efficiently
    and non-tabular fields for arbitrary data.
    """

    # Class variables defining the schema
    __search_fields__: ClassVar[Set[str]] = set()
    __version__: ClassVar[str] = "1.0.0"

    pk: Optional[str] = None  # The primary key, set by the store
    created_at: Optional[datetime] = None  # Creation timestamp
    updated_at: Optional[datetime] = None  # Last update timestamp

    class Config:
        """Pydantic configuration for StoreModel."""

        arbitrary_types_allowed = True

    def get_search_fields(self) -> Dict[str, JsonValue]:
        """
        Get the tabular data from this model.

        Returns:
            A dictionary of tabular data fields.
        """
        data = {}
        for field in self.__search_fields__:
            if hasattr(self, field):
                data[field] = getattr(self, field)
        return data

    def get_data_fields(self) -> Dict[str, JsonValue]:
        """
        Get the regular data fields from this model.

        Returns:
            A dictionary representation of the regular data fields.
        """
        data = self.model_dump(exclude={"pk", "created_at", "updated_at"})
        for field in self.__search_fields__:
            if field in data:
                del data[field]
        return data


class Store(ABC):
    """
    Abstract base class for database storage backends.

    This class defines the interface that all database implementations must adhere to.
    It provides methods for storing, retrieving, updating, and querying data across
    different namespaces and collections.
    """

    def __init__(
        self,
        *,
        default_namespace: str = "default",
    ):
        """
        Initialize the store with a default namespace.

        Args:
            default_namespace: The default namespace to use when none is specified.
        """
        self.default_namespace = default_namespace

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the database connection and setup.

        This method should be called before any other methods are used.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the database connection and release resources.

        This method should be called when the store is no longer needed.
        """
        pass

    @abstractmethod
    async def get_store_version(self) -> int:
        """
        Get the current version of the store schema.

        Returns:
            The version number.
        """
        pass

    @abstractmethod
    async def set_store_version(self, *, version: int) -> None:
        """
        Set the current version of the store schema.

        Args:
            version: The new version number.
        """
        pass

    @abstractmethod
    async def _create_new_namespace(self, *, namespace: str) -> None:
        """
        Create a new namespace in the database. Guaranteed to be called only if the namespace does not exist.

        Args:
            namespace: The name of the namespace to create.
        """
        pass

    @abstractmethod
    async def list_namespaces(self) -> List[str]:
        """
        List all namespaces in the database.

        Returns:
            A list of namespace names.
        """
        pass

    @abstractmethod
    async def check_namespace(self, *, namespace: str) -> bool:
        """
        Check if a namespace exists.

        Args:
            namespace: The name of the namespace to check.

        Returns:
            True if the namespace exists, False otherwise.
        """
        pass

    @abstractmethod
    async def _delete_namespace(self, *, namespace: str) -> None:
        """
        Delete a namespace and all its collections. Will only be called if the namespace exists.

        Args:
            namespace: The name of the namespace to delete.
        """
        pass

    @abstractmethod
    async def _check_collection(self, *, collection: str, namespace: str) -> bool:
        """
        Check if a collection exists in a namespace. Namespace has been checked.

        Args:
            collection: The name of the collection to check.
            namespace: The namespace to check in.

        Returns:
            True if the collection exists, False otherwise.
        """
        pass

    @abstractmethod
    async def _list_collections(self, *, namespace: str) -> List[str]:
        """
        List all collections in a namespace. Namespace exists.

        Args:
            namespace: The namespace to list collections from. If None, uses the default namespace.

        Returns:
            A list of collection names.
        """
        pass

    @abstractmethod
    async def _delete_collection(self, *, collection: str, namespace: str) -> None:
        """
        Delete a collection and all its data. Namespace exists and collection exists.

        Args:
            collection: The name of the collection to delete.
            namespace: The namespace to delete from. If None, uses the default namespace.
        """
        pass

    @abstractmethod
    async def _create_nonexistent_collection(
        self, *, collection: str, namespace: str, model_class: Type[StoreModel]
    ) -> None:
        """
        Checks done, namespace exists, collection doesn't.
        Should add a collection with the given model classes searchable fields and other fields.

        Args:
            collection: The name of the collection to create.
            namespace: The namespace to create the collection in.
            model_class: The StoreModel class this collection will store.

        """
        pass

    @abstractmethod
    async def _add_searchable_field(
        self,
        *,
        collection: str,
        field_name: str,
        field_type: Type[JsonValue],
        namespace: str,
    ) -> None:
        """
        Add a new field to the searchable schema of a collection.
        Collection and namespace already exist.
        field_name may or may not already exist.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection.
        """
        pass

    @abstractmethod
    async def _remove_searchable_field(
        self,
        *,
        collection: str,
        field_name: str,
        namespace: str,
    ) -> None:
        """
        Remove a field from the searchable schema of a collection. Collection and namespace exist.
        field_name may or may not exist.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the field to remove.
            namespace: The namespace of the collection.
        """
        pass

    @abstractmethod
    async def _add_data_field(
        self,
        *,
        collection: str,
        field_name: str,
        field_type: Type[JsonValue],
        namespace: str,
    ) -> None:
        """
        Add a new field to the regular data of a collection. Collection and namespace exist.
        field_name may or may not already exist.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection.
        """
        pass

    @abstractmethod
    async def _remove_data_field(
        self,
        *,
        collection: str,
        field_name: str,
        namespace: str,
    ) -> None:
        """
        Remove a field from the regular data of a collection. collection and namespace exist.
        field_name may or may not exist.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the field to remove.
            namespace: The namespace of the collection.
        """
        pass

    @abstractmethod
    async def _check_pks(
        self,
        *,
        collection: str,
        pks: Iterable[str],
        namespace: str,
    ) -> bool:
        """
        Check if the items exist in a collection. Collection and namespace exist.

        Args:
            collection: The name of the collection to check.
            pks: The primary keys of the items to check.
            namespace: The namespace of the collection.

        Returns:
            True if all items exist, False otherwise.
        """
        pass

    @abstractmethod
    async def _search_pks(
        self, *, collection: str, query: Dict[str, JsonValue], namespace: str
    ) -> Set[str]:
        """
        Search for items in a collection by searchable data fields. namespace and collection exist.

        Args:
            collection: The name of the collection to search.
            query: Dictionary mapping field names to values to match.
            namespace: The namespace of the collection.

        Returns:
            A set of primary keys for matching items.
        """
        pass

    @abstractmethod
    async def _get_pks[T: StoreModel](
        self,
        *,
        collection: str,
        pks: Iterable[str],
        model_cls: Type[T],
        namespace: str,
    ) -> Dict[str, Optional[T]]:
        """
        Retrieve items by their primary keys. Collection and namespace exist.

        Args:
            collection: The name of the collection to retrieve from.
            pks: The primary keys of the items to retrieve.
            model_cls: The StoreModel class to deserialize the item into.
            namespace: The namespace of the collection.

        Returns:
            A dictionary of primary keys to StoreModels or None.
        """
        pass

    @abstractmethod
    async def _create_given_pk(
        self,
        *,
        pk: str,
        collection: str,
        item: StoreModel,
        namespace: str,
    ) -> str:
        """
        Creates a new item with a given primary key. Assume all checks have been done.

        Args:
            pk: The primary key of the item to create.
            collection: The name of the collection to add to.
            item: The StoreModel to store.
            namespace: The namespace of the collection.

        Returns:
            The primary key of the created item.
        """
        pass

    @abstractmethod
    async def _create_new_pk(
        self,
        *,
        collection: str,
        item: StoreModel,
        namespace: str,
    ) -> str:
        """
        Creates a new item with a new (generated by the store) primary key. Assume all checks have been done.

        Args:
            collection: The name of the collection to add to.
            item: The StoreModel to store.
            namespace: The namespace of the collection.

        Returns:
            The primary key of the created item.
        """
        pass

    @abstractmethod
    async def _update_pk(
        self,
        *,
        pk: str,
        collection: str,
        item: StoreModel,
        namespace: str,
    ) -> str:
        """
        Update an item by its primary key. Assume all checks have been done.

        Args:
            pk: The primary key of the item to update.
            collection: The name of the collection containing the item.
            item: The updated StoreModel.
            namespace: The namespace of the collection.

        Returns:
            The primary key of the updated item.
        """
        pass

    @abstractmethod
    async def _delete_pk(self, collection: str, pk: str, namespace: str) -> None:
        """
        Delete an item by its primary key. Assume all checks have been done.

        Args:
            collection: The name of the collection containing the item.
            pk: The primary key of the item to delete.
            namespace: The namespace of the collection.
        """
        pass

    async def create_namespace(self, *, namespace: str) -> None:
        """
        Create a new namespace in the database.
        """
        exists = await self.check_namespace(namespace=namespace)
        if not exists:
            await self._create_new_namespace(namespace=namespace)
        else:
            raise ConflictError(f"Namespace {namespace} already exists")

    async def delete_namespace(self, *, namespace: str) -> None:
        """
        Delete a namespace and all its collections.

        Args:
            namespace: The name of the namespace to delete.
        """
        exists = await self.check_namespace(namespace=namespace)
        if exists:
            await self._delete_namespace(namespace=namespace)
        else:
            raise NotFoundError(f"Namespace {namespace} does not exist")

    def _default_namespace_helper(self, namespace: Optional[str]) -> str:
        """
        Resolve a namespace to use.

        Args:
            namespace: The namespace to use, or None to use the default.

        Returns:
            The resolved namespace.
        """
        return namespace if namespace is not None else self.default_namespace

    async def resolve_namespace(self, *, namespace: Optional[str]) -> str:
        """
        Helper to get the actual namespace or default, and check if it exists.

        Args:
            namespace: The namespace to check

        Returns:
            Guaranteed to return a valid namespace

        Raises:
            NotFoundException: If the namespace does not exist
        """

        ns = self._default_namespace_helper(namespace=namespace)
        exists = await self.check_namespace(namespace=ns)
        if exists:
            return ns
        else:
            raise NotFoundError(f"Namespace {ns} does not exist")

    async def ensure_namespace(self, namespace: Optional[str]) -> str:
        """Ensure namespace structures exists, creating if necessary.

        Args:
            namespace: The namespace to check

        Returns:
            Guaranteed to return a valid namespace
        """
        try:
            return await self.resolve_namespace(namespace=namespace)
        except NotFoundError:
            ns = self._default_namespace_helper(namespace=namespace)
            await self.create_namespace(namespace=ns)
            return ns

    async def check_collection(
        self, *, collection: str, namespace: Optional[str] = None
    ) -> bool:
        """
        Check if a collection exists in a namespace.

        Args:
            collection: The name of the collection to check.
            namespace: The namespace to check in. If None, uses the default namespace.

        Returns:
            True if the collection exists, False otherwise.
        """
        ns = await self.resolve_namespace(namespace=namespace)
        return await self._check_collection(collection=collection, namespace=ns)

    async def list_collections(self, *, namespace: Optional[str] = None) -> List[str]:
        """
        List all collections in a namespace.

        Args:
            namespace: The namespace to list collections from. If None, uses the default namespace.

        Returns:
            A list of collection names.
        """
        ns = await self.resolve_namespace(namespace=namespace)
        return await self._list_collections(namespace=ns)

    async def create_collection(
        self,
        *,
        collection: str,
        model_class: Type[StoreModel],
        namespace: Optional[str | ALL_NAMESPACES] = None,
    ) -> None:
        """
        Create a new collection for a model class.

        Args:
            collection: The name of the collection to create.
            model_class: The StoreModel class this collection will store.
            namespace: The namespace to create the collection in. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.create_collection(
                    collection=collection, model_class=model_class, namespace=ns
                )
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            exists = await self._check_collection(collection=collection, namespace=ns)
            if not exists:
                await self._create_nonexistent_collection(
                    collection=collection,
                    namespace=ns,
                    model_class=model_class,
                )
            else:
                raise ConflictError(f"Collection {collection} already exists")

    async def delete_collection(
        self, *, collection: str, namespace: Optional[str | ALL_NAMESPACES] = None
    ) -> None:
        """
        Delete a collection and all its data.

        Args:
            collection: The name of the collection to delete.
            namespace: The namespace to delete from. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.delete_collection(collection=collection, namespace=ns)
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            exists = await self._check_collection(collection=collection, namespace=ns)
            if exists:
                await self._delete_collection(collection=collection, namespace=ns)
            else:
                raise NotFoundError(f"Collection {collection} does not exist")

    async def add_searchable_field(
        self,
        *,
        collection: str,
        field_name: str,
        field_type: Type[JsonValue],
        namespace: Optional[str | ALL_NAMESPACES] = None,
    ) -> None:
        """
        Add a new field to the searchable schema of a collection.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.add_searchable_field(
                    collection=collection,
                    field_name=field_name,
                    field_type=field_type,
                    namespace=ns,
                )
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            exists = await self._check_collection(collection=collection, namespace=ns)
            if not exists:
                raise NotFoundError(f"Collection {collection} does not exist")
            else:
                await self._add_searchable_field(
                    collection=collection,
                    field_name=field_name,
                    field_type=field_type,
                    namespace=ns,
                )

    async def remove_searchable_field(
        self,
        *,
        collection: str,
        field_name: str,
        namespace: Optional[str | ALL_NAMESPACES] = None,
    ) -> None:
        """
        Add a new field to the searchable schema of a collection.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.remove_searchable_field(
                    collection=collection,
                    field_name=field_name,
                    namespace=ns,
                )
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            exists = await self._check_collection(collection=collection, namespace=ns)
            if not exists:
                raise NotFoundError(f"Collection {collection} does not exist")
            else:
                await self._remove_searchable_field(
                    collection=collection,
                    field_name=field_name,
                    namespace=ns,
                )

    async def add_data_field(
        self,
        *,
        collection: str,
        field_name: str,
        field_type: Type[JsonValue],
        namespace: Optional[str | ALL_NAMESPACES] = None,
    ) -> None:
        """
        Add a new field to the searchable schema of a collection.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.add_data_field(
                    collection=collection,
                    field_name=field_name,
                    field_type=field_type,
                    namespace=ns,
                )
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            exists = await self._check_collection(collection=collection, namespace=ns)
            if not exists:
                raise NotFoundError(f"Collection {collection} does not exist")
            else:
                await self._add_data_field(
                    collection=collection,
                    field_name=field_name,
                    field_type=field_type,
                    namespace=ns,
                )

    async def remove_data_field(
        self,
        *,
        collection: str,
        field_name: str,
        namespace: Optional[str | ALL_NAMESPACES] = None,
    ) -> None:
        """
        Add a new field to the searchable schema of a collection.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.remove_data_field(
                    collection=collection,
                    field_name=field_name,
                    namespace=ns,
                )
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            exists = await self._check_collection(collection=collection, namespace=ns)
            if not exists:
                raise NotFoundError(f"Collection {collection} does not exist")
            else:
                await self._remove_data_field(
                    collection=collection,
                    field_name=field_name,
                    namespace=ns,
                )

    async def create_model_collection(
        self,
        name: str,
        model_cls: Type[StoreModel],
        namespace: Optional[str | ALL_NAMESPACES] = None,
    ) -> None:
        """
        Create a new collection for a model class.

        Args:
            model_cls: The StoreModel class this collection will store.
            namespace: The namespace to create the collection in. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.create_model_collection(
                    name=name,
                    model_cls=model_cls,
                    namespace=ns,
                )
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            await self.create_collection(
                collection=name,
                model_class=model_cls,
                namespace=namespace,
            )
            for field in model_cls.__search_fields__:
                field_type = model_cls.__annotations__.get(field)
                if field_type is None:
                    raise ValueError(
                        f"Field {field} in {model_cls.__name__} has no type annotation"
                    )
                await self._add_searchable_field(
                    collection=name,
                    field_name=field,
                    field_type=field_type,
                    namespace=ns,
                )
            for field_name, field_info in model_cls.model_fields.items():
                if field_name not in model_cls.__search_fields__:
                    if field_info.annotation is None:
                        raise ValueError(
                            f"Field {field_name} in {model_cls.__name__} has no type annotation"
                        )
                    await self._add_data_field(
                        collection=name,
                        field_name=field_name,
                        field_type=field_info.annotation,
                        namespace=ns,
                    )

    async def migrate_model_collection(
        self,
        name: str,
        old_model_cls: Type[StoreModel],
        new_model_cls: Type[StoreModel],
        namespace: Optional[str | ALL_NAMESPACES] = None,
    ) -> None:
        """
        Migrate a collection from one model class to another.

        Args:
            old_model_cls: The old StoreModel class this collection is storing.
            new_model_cls: The new StoreModel class this collection will store.
            namespace: The namespace to create the collection in. If None, uses the default namespace.
        """
        if namespace == ALL_NAMESPACES:
            for ns in await self.list_namespaces():
                await self.migrate_model_collection(
                    name=name,
                    old_model_cls=old_model_cls,
                    new_model_cls=new_model_cls,
                    namespace=ns,
                )
        else:
            ns = await self.resolve_namespace(namespace=namespace)
            exists = await self._check_collection(collection=name, namespace=ns)
            if not exists:
                raise NotFoundError(
                    f"Collection {old_model_cls.__name__} does not exist"
                )
            else:
                searchable_fields_added = (
                    new_model_cls.__search_fields__ - old_model_cls.__search_fields__
                )
                data_fields_added = (
                    new_model_cls.model_fields.keys()
                    - old_model_cls.model_fields.keys()
                )
                searchable_fields_deleted = (
                    old_model_cls.__search_fields__ - new_model_cls.__search_fields__
                )
                data_fields_deleted = (
                    old_model_cls.model_fields.keys()
                    - new_model_cls.model_fields.keys()
                )

                for field in searchable_fields_added:
                    field_type = new_model_cls.__annotations__.get(field)
                    if field_type is None:
                        raise ValueError(
                            f"Field {field} in {new_model_cls.__name__} has no type annotation"
                        )
                    await self._add_searchable_field(
                        collection=name,
                        field_name=field,
                        field_type=field_type,
                        namespace=ns,
                    )
                for field in data_fields_added:
                    field_type = new_model_cls.__annotations__.get(field)
                    if field_type is None:
                        raise ValueError(
                            f"Field {field} in {new_model_cls.__name__} has no type annotation"
                        )
                    await self._add_data_field(
                        collection=name,
                        field_name=field,
                        field_type=field_type,
                        namespace=ns,
                    )

                for field in searchable_fields_deleted:
                    await self._remove_searchable_field(
                        collection=name,
                        field_name=field,
                        namespace=ns,
                    )
                for field in data_fields_deleted:
                    await self._remove_data_field(
                        collection=name,
                        field_name=field,
                        namespace=ns,
                    )

    async def _ns_and_col_helper(self, namespace: Optional[str], collection: str):
        ns = await self.resolve_namespace(namespace=namespace)
        col_exists = await self.check_collection(collection=collection, namespace=ns)
        if not col_exists:
            raise NotFoundError(f"Collection {collection} does not exist")
        return ns

    async def check_items(
        self,
        *,
        collection: str,
        pks: Iterable[str],
        namespace: Optional[str] = None,
    ) -> bool:
        """
        Check if the items exist in a collection.

        Args:
            collection: The name of the collection to check.
            pks: The primary keys of the items to check.
            namespace: The namespace of the collection. If None, uses the default namespace.

        Returns:
            True if all items exist, False otherwise.
        """
        ns = await self._ns_and_col_helper(namespace=namespace, collection=collection)
        return await self._check_pks(collection=collection, pks=pks, namespace=ns)

    async def get_items[T: StoreModel](
        self,
        *,
        collection: str,
        pks: Iterable[str],
        model_cls: Type[T],
        namespace: Optional[str] = None,
    ) -> Dict[str, Optional[T]]:
        """
        Retrieve items by their primary keys.

        Args:
            collection: The name of the collection to retrieve from.
            pks: The primary keys of the items to retrieve.
            model_cls: The StoreModel class to deserialize the item into.
            namespace: The namespace of the collection. If None, uses the default namespace.

        Returns:
            A dictionary of primary keys to StoreModels or None. Store models should have pk set.
        """
        ns = await self._ns_and_col_helper(namespace=namespace, collection=collection)
        return await self._get_pks(
            collection=collection, pks=pks, model_cls=model_cls, namespace=ns
        )

    async def create_item(
        self,
        *,
        collection: str,
        item: StoreModel,
        namespace: Optional[str] = None,
    ) -> str:
        """
        Create a new item in a collection.

        Args:
            collection: The name of the collection to add to.
            item: The StoreModel to store.
            namespace: The namespace of the collection. If None, uses the default namespace.

        Returns:
            The primary key (str) of the created item.
        """
        ns = await self._ns_and_col_helper(namespace=namespace, collection=collection)
        if item.pk is not None:
            pk_exists = self._check_pks(
                collection=collection, pks=[item.pk], namespace=ns
            )
            if pk_exists:
                raise ConflictError(f"Item with pk {item.pk} already exists")
            else:
                return await self._create_given_pk(
                    pk=item.pk, collection=collection, item=item, namespace=ns
                )
        else:
            pk = await self._create_new_pk(
                collection=collection, item=item, namespace=ns
            )
            item.pk = pk
            return pk

    async def update_item(
        self,
        *,
        collection: str,
        item: StoreModel,
        namespace: Optional[str] = None,
    ) -> str:
        """
        Update an existing item.

        Args:
            collection: The name of the collection containing the item.
            pk: The primary key of the item to update.
            item: The updated StoreModel.
            namespace: The namespace of the collection. If None, uses the default namespace.

        Returns:
            True if the item was updated, False if it wasn't found.
        """
        ns = await self._ns_and_col_helper(namespace=namespace, collection=collection)
        if item.pk is None:
            raise ValueError("Item must have a primary key to update")
        pk_exists = self._check_pks(collection=collection, pks=[item.pk], namespace=ns)
        if pk_exists:
            return await self._update_pk(
                pk=item.pk, collection=collection, item=item, namespace=ns
            )
        else:
            raise NotFoundError(f"Item with pk {item.pk} not found")

    async def delete_item(
        self, collection: str, pk: str, namespace: Optional[str] = None
    ) -> None:
        """
        Delete an item by its primary key.

        Args:
            collection: The name of the collection containing the item.
            pk: The primary key of the item to delete.
            namespace: The namespace of the collection. If None, uses the default namespace.

        Returns:
            True if the item was deleted, False if it wasn't found.
        """
        ns = await self._ns_and_col_helper(namespace=namespace, collection=collection)
        pk_exists = self._check_pks(collection=collection, pks=[pk], namespace=ns)
        if pk_exists:
            await self._delete_pk(collection=collection, pk=pk, namespace=ns)
        else:
            raise NotFoundError(f"Item with pk {pk} not found")

    @staticmethod
    def ensure_single_match(pks: Set[str]) -> str:
        """Ensure there is exactly one match, raising an exception otherwise."""
        if len(pks) > 1:
            raise ConflictError(f"Multiple records found matching the provided labels")
        elif len(pks) == 0:
            raise NotFoundError(f"No record found matching the provided labels")
        else:
            return next(iter(pks))

    @staticmethod
    def _ensure_single_or_no_match(pks: Set[str]) -> Optional[str]:
        """Ensure there is at most one match, raising an exception if there are multiple."""
        if len(pks) > 1:
            raise ConflictError(f"Multiple records found matching the provided labels")
        elif len(pks) == 0:
            return None
        else:
            return next(iter(pks))

    async def search_items[T: StoreModel](
        self,
        collection: str,
        query: Dict[str, JsonValue],
        model_cls: Type[T],
        namespace: Optional[str] = None,
    ) -> List[T]:
        """
        Query items by tabular data fields.

        Args:
            collection: The name of the collection to query.
            query: Dictionary mapping field names to values to match,
                or a list of QueryCondition objects for complex queries.
            model_cls: The StoreModel class to deserialize items into.
            namespace: The namespace of the collection. If None, uses the default namespace.
            limit: Maximum number of items to return.
            offset: Number of items to skip.

        Returns:
            A list of matching items as StoreModels.
        """
        ns = await self._ns_and_col_helper(namespace=namespace, collection=collection)
        pks = await self._search_pks(collection=collection, query=query, namespace=ns)
        result = []

        for pk in pks:
            result.append(
                (
                    await self._get_pks(
                        collection=collection,
                        pks=[pk],
                        model_cls=model_cls,
                        namespace=ns,
                    )
                )[pk]
            )

        return result

    async def search_for_item[T: StoreModel](
        self,
        *,
        collection: str,
        query: Dict[str, JsonValue],
        model_cls: Type[T],
        namespace: Optional[str] = None,
    ) -> Optional[T]:
        ns = await self._ns_and_col_helper(namespace=namespace, collection=collection)
        pks = await self._search_pks(collection=collection, query=query, namespace=ns)
        pk = self._ensure_single_or_no_match(pks)
        if pk is None:
            return None
        else:
            return (
                await self._get_pks(
                    collection=collection, pks=[pk], model_cls=model_cls, namespace=ns
                )
            )[pk]
