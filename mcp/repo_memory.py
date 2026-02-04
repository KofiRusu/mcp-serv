"""
Repo Memory - Append-only MEMORY.md and decision log with timestamps

Provides project memory storage in markdown files.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional


class RepoMemory:
    """Append-only project memory in markdown files"""

    def __init__(self, memory_file: str, decision_file: str):
        self.memory_file = Path(memory_file)
        self.decision_file = Path(decision_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.decision_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize memory file if it doesn't exist
        if not self.memory_file.exists():
            self.memory_file.write_text("# Project Memory\n\nThis file stores important project context and decisions.\n\n")

        # Initialize decision file if it doesn't exist
        if not self.decision_file.exists():
            self.decision_file.write_text(
                "# Decision Log\n\n"
                "| Timestamp | Decision | Tags | Context |\n"
                "|-----------|----------|------|---------|\n"
            )

    def append_memory(self, content: str, tags: Optional[List[str]] = None) -> str:
        """
        Append a memory entry to MEMORY.md.

        Args:
            content: The memory content
            tags: Optional list of tags

        Returns:
            Timestamp of the entry
        """
        timestamp = datetime.utcnow().isoformat()
        tag_str = " ".join(tags or [])
        entry = f"\n---\n\n## {timestamp}\n"
        if tag_str:
            entry += f"**Tags:** {tag_str}\n\n"
        entry += f"{content}\n"

        with open(self.memory_file, "a") as f:
            f.write(entry)

        return timestamp

    def search_memory(self, query: str) -> List[str]:
        """
        Search memory entries for a query.

        Args:
            query: Search query

        Returns:
            List of matching entries
        """
        content = self.memory_file.read_text(encoding="utf-8", errors="ignore")
        entries = content.split("\n---\n")

        results = []
        for entry in entries:
            if query.lower() in entry.lower():
                # Clean up the entry for display
                entry = entry.strip()
                if entry:
                    results.append(entry)

        return results

    def add_decision(self, decision: str, tags: List[str], context: str = "") -> str:
        """
        Add a decision to the decision log.

        Args:
            decision: The decision made
            tags: List of tags for categorization
            context: Additional context about the decision

        Returns:
            Timestamp of the entry
        """
        timestamp = datetime.utcnow().isoformat()
        tag_str = " ".join(tags)
        row = f"| {timestamp} | {decision} | {tag_str} | {context} |\n"

        with open(self.decision_file, "a") as f:
            f.write(row)

        return timestamp

    def search_decisions(self, query: str) -> List[str]:
        """
        Search decision log for a query.

        Args:
            query: Search query

        Returns:
            List of matching rows
        """
        content = self.decision_file.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        results = []
        for line in lines:
            if query.lower() in line.lower():
                results.append(line.strip())

        return results
