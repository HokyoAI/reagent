import uuid
from abc import ABC
from datetime import datetime
from typing import (
    ClassVar,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Set,
    Type,
    TypedDict,
)

from reagent.core.models.errors import ConflictError, NotFoundError
from reagent.core.models.types import JsonValue
from reagent.core.store import Store, StoreModel


class DataStructure(TypedDict):
    search_data: Dict[str, JsonValue]
    data: Dict[str, JsonValue]
    created_at: datetime
    updated_at: datetime


class InMemoryStore(Store):
    """
    In-memory implementation of the Store interface.

    This implementation uses in-memory data structures (dictionaries) to store data.
    It's suitable for testing or small-scale applications where persistence is not required.
    """

    def __init__(self, *, default_namespace: str = "default"):
        """
        Initialize the in-memory store with a default namespace.

        Args:
            default_namespace: The default namespace to use when none is specified.
        """
        super().__init__(default_namespace=default_namespace)
        self._store_version = 0
        # Structure: {namespace: {collection: {pk: {search_data: dict, data: dict, created_at: datetime, updated_at: datetime}}}}
        self._data: Dict[str, Dict[str, Dict[str, DataStructure]]] = {}
        # Structure: {namespace: {collection: {field_name: field_type}}}
        self._searchable_fields: Dict[str, Dict[str, Dict[str, Type[JsonValue]]]] = {}
        # Structure: {namespace: {collection: {field_name: field_type}}}
        self._data_fields: Dict[str, Dict[str, Dict[str, Type[JsonValue]]]] = {}
        # Structure: {namespace: {collection: model_class}}
        self._model_classes: Dict[str, Dict[str, Type[StoreModel]]] = {}

    async def initialize(self) -> None:
        """
        Initialize the in-memory store.

        This is a no-op for the in-memory implementation.
        """
        pass

    async def close(self) -> None:
        """
        Close the in-memory store.

        This is a no-op for the in-memory implementation.
        """
        pass

    async def get_store_version(self) -> int:
        """
        Get the current version of the store schema.

        Returns:
            The version number.
        """
        return self._store_version

    async def set_store_version(self, *, version: int) -> None:
        """
        Set the current version of the store schema.

        Args:
            version: The new version number.
        """
        self._store_version = version

    async def _create_new_namespace(self, *, namespace: str) -> None:
        """
        Create a new namespace in the database.

        Args:
            namespace: The name of the namespace to create.
        """
        self._data[namespace] = {}
        self._searchable_fields[namespace] = {}
        self._data_fields[namespace] = {}
        self._model_classes[namespace] = {}

    async def list_namespaces(self) -> List[str]:
        """
        List all namespaces in the database.

        Returns:
            A list of namespace names.
        """
        return list(self._data.keys())

    async def check_namespace(self, *, namespace: str) -> bool:
        """
        Check if a namespace exists.

        Args:
            namespace: The name of the namespace to check.

        Returns:
            True if the namespace exists, False otherwise.
        """
        return namespace in self._data

    async def _delete_namespace(self, *, namespace: str) -> None:
        """
        Delete a namespace and all its collections.

        Args:
            namespace: The name of the namespace to delete.
        """
        if namespace in self._data:
            del self._data[namespace]
        if namespace in self._searchable_fields:
            del self._searchable_fields[namespace]
        if namespace in self._data_fields:
            del self._data_fields[namespace]
        if namespace in self._model_classes:
            del self._model_classes[namespace]

    async def _check_collection(self, *, collection: str, namespace: str) -> bool:
        """
        Check if a collection exists in a namespace.

        Args:
            collection: The name of the collection to check.
            namespace: The namespace to check in.

        Returns:
            True if the collection exists, False otherwise.
        """
        return namespace in self._data and collection in self._data[namespace]

    async def _list_collections(self, *, namespace: str) -> List[str]:
        """
        List all collections in a namespace.

        Args:
            namespace: The namespace to list collections from.

        Returns:
            A list of collection names.
        """
        if namespace not in self._data:
            return []
        return list(self._data[namespace].keys())

    async def _delete_collection(self, *, collection: str, namespace: str) -> None:
        """
        Delete a collection and all its data.

        Args:
            collection: The name of the collection to delete.
            namespace: The namespace to delete from.
        """
        if namespace in self._data and collection in self._data[namespace]:
            del self._data[namespace][collection]
        if (
            namespace in self._searchable_fields
            and collection in self._searchable_fields[namespace]
        ):
            del self._searchable_fields[namespace][collection]
        if (
            namespace in self._data_fields
            and collection in self._data_fields[namespace]
        ):
            del self._data_fields[namespace][collection]
        if (
            namespace in self._model_classes
            and collection in self._model_classes[namespace]
        ):
            del self._model_classes[namespace][collection]

    async def _create_nonexistent_collection(
        self, *, collection: str, namespace: str, model_class: Type[StoreModel]
    ) -> None:
        """
        Create a new collection with the given model class's searchable fields.

        Args:
            collection: The name of the collection to create.
            namespace: The namespace to create the collection in.
            model_class: The StoreModel class this collection will store.
        """
        if namespace not in self._data:
            await self._create_new_namespace(namespace=namespace)

        self._data[namespace][collection] = {}
        self._searchable_fields[namespace][collection] = {
            field: type(getattr(model_class, field, None))
            for field in model_class.__search_fields__
        }
        self._data_fields[namespace][collection] = {}
        self._model_classes[namespace][collection] = model_class

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

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection.
        """
        if namespace not in self._searchable_fields:
            self._searchable_fields[namespace] = {}
        if collection not in self._searchable_fields[namespace]:
            self._searchable_fields[namespace][collection] = {}

        self._searchable_fields[namespace][collection][field_name] = field_type

    async def _remove_searchable_field(
        self,
        *,
        collection: str,
        field_name: str,
        namespace: str,
    ) -> None:
        """
        Remove a field from the searchable schema of a collection.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the field to remove.
            namespace: The namespace of the collection.
        """
        if (
            namespace in self._searchable_fields
            and collection in self._searchable_fields[namespace]
            and field_name in self._searchable_fields[namespace][collection]
        ):
            del self._searchable_fields[namespace][collection][field_name]

    async def _add_data_field(
        self,
        *,
        collection: str,
        field_name: str,
        field_type: Type[JsonValue],
        namespace: str,
    ) -> None:
        """
        Add a new field to the regular data of a collection.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the new field.
            field_type: The type of the new field.
            namespace: The namespace of the collection.
        """
        if namespace not in self._data_fields:
            self._data_fields[namespace] = {}
        if collection not in self._data_fields[namespace]:
            self._data_fields[namespace][collection] = {}

        self._data_fields[namespace][collection][field_name] = field_type

    async def _remove_data_field(
        self,
        *,
        collection: str,
        field_name: str,
        namespace: str,
    ) -> None:
        """
        Remove a field from the regular data of a collection.

        Args:
            collection: The name of the collection to modify.
            field_name: The name of the field to remove.
            namespace: The namespace of the collection.
        """
        if (
            namespace in self._data_fields
            and collection in self._data_fields[namespace]
            and field_name in self._data_fields[namespace][collection]
        ):
            del self._data_fields[namespace][collection][field_name]

    async def _check_pks(
        self,
        *,
        collection: str,
        pks: Iterable[str],
        namespace: str,
    ) -> bool:
        """
        Check if the items exist in a collection.

        Args:
            collection: The name of the collection to check.
            pks: The primary keys of the items to check.
            namespace: The namespace of the collection.

        Returns:
            True if all items exist, False otherwise.
        """
        if namespace not in self._data or collection not in self._data[namespace]:
            return False

        for pk in pks:
            if pk not in self._data[namespace][collection]:
                return False

        return True

    async def _search_pks(
        self, *, collection: str, query: Dict[str, JsonValue], namespace: str
    ) -> Set[str]:
        """
        Search for items in a collection by searchable data fields.

        Args:
            collection: The name of the collection to search.
            query: Dictionary mapping field names to values to match.
            namespace: The namespace of the collection.

        Returns:
            A set of primary keys for matching items.
        """
        if namespace not in self._data or collection not in self._data[namespace]:
            return set()

        result = set()
        for pk, item_data in self._data[namespace][collection].items():
            match = True
            for field, value in query.items():
                if (
                    field not in item_data["search_data"]
                    or item_data["search_data"][field] != value
                ):
                    match = False
                    break

            if match:
                result.add(pk)

        return result

    async def _get_pks[T: StoreModel](
        self,
        *,
        collection: str,
        pks: Iterable[str],
        model_cls: Type[T],
        namespace: str,
    ) -> Dict[str, Optional[T]]:
        """
        Retrieve items by their primary keys.

        Args:
            collection: The name of the collection to retrieve from.
            pks: The primary keys of the items to retrieve.
            model_cls: The StoreModel class to deserialize the item into.
            namespace: The namespace of the collection.

        Returns:
            A dictionary of primary keys to StoreModels or None.
        """
        if namespace not in self._data or collection not in self._data[namespace]:
            return {pk: None for pk in pks}

        result = {}
        for pk in pks:
            if pk in self._data[namespace][collection]:
                item_data = self._data[namespace][collection][pk]
                model_data = {**item_data["search_data"], **item_data["data"]}
                result[pk] = model_cls(
                    pk=pk,
                    created_at=item_data["created_at"],
                    updated_at=item_data["updated_at"],
                    **model_data,
                )
            else:
                result[pk] = None

        return result

    async def _create_given_pk(
        self,
        *,
        pk: str,
        collection: str,
        item: StoreModel,
        namespace: str,
    ) -> str:
        """
        Creates a new item with a given primary key.

        Args:
            pk: The primary key of the item to create.
            collection: The name of the collection to add to.
            item: The StoreModel to store.
            namespace: The namespace of the collection.

        Returns:
            The primary key of the created item.
        """
        if namespace not in self._data or collection not in self._data[namespace]:
            raise NotFoundError(f"Collection {namespace}.{collection} not found")

        if pk in self._data[namespace][collection]:
            raise ConflictError(
                f"Item with pk {pk} already exists in {namespace}.{collection}"
            )

        now = datetime.now()
        self._data[namespace][collection][pk] = {
            "search_data": item.get_search_fields(),
            "data": item.get_data_fields(),
            "created_at": now,
            "updated_at": now,
        }
        return pk

    async def _create_new_pk(
        self,
        *,
        collection: str,
        item: StoreModel,
        namespace: str,
    ) -> str:
        """
        Creates a new item with a new (generated by the store) primary key.

        Args:
            collection: The name of the collection to add to.
            item: The StoreModel to store.
            namespace: The namespace of the collection.

        Returns:
            The primary key of the created item.
        """
        if namespace not in self._data or collection not in self._data[namespace]:
            raise NotFoundError(f"Collection {namespace}.{collection} not found")

        pk = str(uuid.uuid4())
        while pk in self._data[namespace][collection]:
            pk = str(uuid.uuid4())

        now = datetime.now()
        self._data[namespace][collection][pk] = {
            "search_data": item.get_search_fields(),
            "data": item.get_data_fields(),
            "created_at": now,
            "updated_at": now,
        }
        return pk

    async def _update_pk(
        self,
        *,
        pk: str,
        collection: str,
        item: StoreModel,
        namespace: str,
    ) -> str:
        """
        Update an item by its primary key.

        Args:
            pk: The primary key of the item to update.
            collection: The name of the collection containing the item.
            item: The updated StoreModel.
            namespace: The namespace of the collection.

        Returns:
            The primary key of the updated item.
        """
        if (
            namespace not in self._data
            or collection not in self._data[namespace]
            or pk not in self._data[namespace][collection]
        ):
            raise NotFoundError(
                f"Item with pk {pk} not found in {namespace}.{collection}"
            )

        created_at = self._data[namespace][collection][pk]["created_at"]
        self._data[namespace][collection][pk] = {
            "search_data": item.get_search_fields(),
            "data": item.get_data_fields(),
            "created_at": created_at,
            "updated_at": datetime.now(),
        }
        return pk

    async def _delete_pk(self, collection: str, pk: str, namespace: str) -> None:
        """
        Delete an item by its primary key.

        Args:
            collection: The name of the collection containing the item.
            pk: The primary key of the item to delete.
            namespace: The namespace of the collection.
        """
        if (
            namespace not in self._data
            or collection not in self._data[namespace]
            or pk not in self._data[namespace][collection]
        ):
            raise NotFoundError(
                f"Item with pk {pk} not found in {namespace}.{collection}"
            )

        del self._data[namespace][collection][pk]
