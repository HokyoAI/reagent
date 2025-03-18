from typing import Optional


class SimpleCache:
    """
    A simple cache implementation using a set with a maximum size limit.
    Only tracks whether strings have been seen before.
    """

    def __init__(self, max_size=128):
        """
        Initialize the cache with a maximum size.

        Args:
            max_size (int): Maximum number of items the cache can hold.
        """
        self.cache = set()
        self.max_size = max_size
        self.access_order = []  # To track which items to remove when full

    def add(self, key):
        """
        Add a key to the cache.

        Args:
            key (str): The key to add to the cache

        Returns:
            bool: True if added, False if already exists
        """
        if key in self.cache:
            # Move to end of access order if already exists
            self.access_order.remove(key)
            self.access_order.append(key)
            return False

        # If cache is full, remove oldest item
        if len(self.cache) >= self.max_size:
            oldest_key = self.access_order.pop(0)
            self.cache.remove(oldest_key)

        # Add new item
        self.cache.add(key)
        self.access_order.append(key)
        return True

    def contains(self, key):
        """
        Check if a key exists in the cache.

        Args:
            key (str): The key to check

        Returns:
            bool: True if the key exists, False otherwise
        """
        return key in self.cache

    def size(self):
        """
        Return the current size of the cache.

        Returns:
            int: Number of items in the cache
        """
        return len(self.cache)


NAMESPACE_SCHEMA_PREFIX = "ns_"


def add_quotes(value: str) -> str:
    """
    Add quotes to a string to allow for case sensitivity.
    """
    return f'"{value}"' if value else value


def namespace_to_schema(namespace: Optional[str]) -> str:
    """
    Convert a namespace to a schema name.
    Adds ns_ prefix and adds quotes to allow for case sensitivity.
    Case sensitivity is desired in case tenant names are case sensitive.
    If no namespace is provided, defaults to '"ns_default"'.
    Not to be confused with the shared schema, which is just 'shared' (no quotes).
    No namespace may take the name default
    """
    if namespace == "default":
        raise ValueError("Namespace 'default' is reserved and cannot be used.")
    if namespace is None:
        return add_quotes(f"{NAMESPACE_SCHEMA_PREFIX}default")
    return add_quotes(f"{NAMESPACE_SCHEMA_PREFIX}{namespace}")


def is_schema_namespace(schema: str) -> bool:
    """
    Check if a schema name is a namespace.
    A schema is considered a namespace if it starts with '"ns_' and ends with '"'.
    """
    return schema.startswith(f'"{NAMESPACE_SCHEMA_PREFIX}') and schema.endswith('"')


def schema_to_namespace(schema: str) -> Optional[str]:
    """
    Convert a schema name to a namespace.
    Removes the ns_ prefix and quotes.
    If the schema is '"ns_default"', returns None.
    """
    if schema == f'"{NAMESPACE_SCHEMA_PREFIX}default"':
        return None
    if not is_schema_namespace(schema):
        raise ValueError(f"Invalid schema name: {schema}")
    return schema[
        len(NAMESPACE_SCHEMA_PREFIX) + 1 : -1
    ]  # Remove "ns_" prefix and quotes
