from datetime import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field

from reagent.core.ledger import Ledger, TimeStampedEntry


class LocalLedger(Ledger):
    id: str
    entries: List[TimeStampedEntry] = Field(default_factory=list)

    def add_entry(self, entry_type: str, source: str, data: BaseModel) -> None:
        """
        Add an entry to the ledger for a specific task.

        Args:
            task_id: The ID of the task this entry belongs to
            entry_type: Type of the entry (e.g., "plan", "execution", "result")
            data: The data to store in the entry
        """

        timestamped_entry = TimeStampedEntry(
            timestamp=dt.now().isoformat(),
            source=source,
            type=entry_type,
            data=data,
        )

        self.entries.append(timestamped_entry)

    def get_entries(self, entry_type: Optional[str] = None) -> List[TimeStampedEntry]:
        """
        Retrieve entries for a task, optionally filtered by entry type.

        Args:
            task_id: The ID of the task
            entry_type: Optional filter for entry type

        Returns:
            List of entries for the task
        """

        if entry_type is None:
            return self.entries

        return [entry for entry in self.entries if entry.type == entry_type]

    def get_latest_entry(
        self, entry_type: Optional[str] = None
    ) -> Optional[TimeStampedEntry]:
        """
        Get the most recent entry for a task, optionally filtered by type.

        Args:
            task_id: The ID of the task
            entry_type: Optional filter for entry type

        Returns:
            The latest entry or None if no entries exist
        """
        entries = self.get_entries(entry_type)
        if not entries:
            return None
        return entries[-1]
