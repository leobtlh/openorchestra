"""
Optimised persistent memory system for OpenOrchestra.

Stores hierarchical patterns in SQLite with an LRU cache, deduplication and
context compression so storage grows linearly instead of exponentially.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from openorchestra.core.lru_cache import LRUCache
from openorchestra.core.pattern_cluster import PatternClusterManager
from openorchestra.core.pattern_signature import PatternSignature

CONTEXT_TTL_SECONDS = 1800
PATTERN_CACHE_SIZE = 500


class CompetitionMemory:
    """
    Persistent memory with:

    - LRU cache for hot patterns
    - Hierarchical pattern storage and deduplication
    - Context compression and automatic cleanup
    """

    def __init__(self, db_path: str = ".openorchestra/memory.db"):
        self.db_path = db_path
        self._ensure_database()

        self._cache: LRUCache[Any] = LRUCache(maxsize=PATTERN_CACHE_SIZE, ttl_seconds=3600)
        self._cluster_manager = PatternClusterManager(max_clusters=50)

        self._stats = {"patterns_stored": 0, "cache_hits": 0, "db_queries": 0}

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _ensure_database(self) -> None:
        """Create the database schema if it does not exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    signature TEXT NOT NULL UNIQUE,
                    pattern_type TEXT NOT NULL,
                    solution TEXT,
                    json_data TEXT,
                    confidence REAL DEFAULT 0.5,
                    frequency INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON patterns(domain)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signature ON patterns(signature)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON patterns(pattern_type)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS competitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    agent_count INTEGER,
                    winner_agent TEXT,
                    best_score REAL,
                    total_cost_usd REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """)
            connection.commit()
        finally:
            connection.close()

    def record_pattern(
        self,
        domain: str,
        pattern_type: str,
        description: str,
        solution: str,
        confidence: float = 0.5,
    ) -> str:
        """Record a learned pattern with signature-based deduplication."""
        signature = PatternSignature.from_context(domain, pattern_type, solution)
        compact = signature.to_compact_vector()
        json_data = json.dumps(
            {
                "description": description[:200],
                "domain_signature": signature.domain_signature,
                "category_signature": signature.category_signature,
            }
        )

        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM patterns WHERE signature = ?", (compact,))
            existing = cursor.fetchone()

            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO patterns
                    (domain, signature, pattern_type, solution, json_data, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (domain, compact, pattern_type, solution, json_data, confidence),
                )
                self._stats["patterns_stored"] += 1
            else:
                cursor.execute(
                    """
                    UPDATE patterns
                    SET confidence = ?, frequency = frequency + 1, updated_at = ?
                    WHERE signature = ?
                    """,
                    (confidence, datetime.now().isoformat(), compact),
                )

            connection.commit()
        finally:
            connection.close()

        self._cache.set(
            compact,
            {
                "domain": domain,
                "type": pattern_type,
                "solution": solution,
                "confidence": confidence,
            },
        )
        self._invalidate_context(domain)
        self._cluster_manager.add_pattern(
            pattern_data={"signature": signature.__dict__}, solution=solution
        )
        return compact

    def _invalidate_context(self, domain: str) -> None:
        self._cache.delete(f"context_{domain}")

    def get_context_knowledge(self, domain: str, max_patterns: int = 5) -> str:
        """Return formatted learned context for a domain (empty when unknown)."""
        cache_key = f"context_{domain}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._stats["cache_hits"] += 1
            return str(cached)

        self._stats["db_queries"] += 1
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT pattern_type, solution, confidence, frequency
                FROM patterns
                WHERE domain = ? AND confidence > 0.5
                ORDER BY confidence DESC, frequency DESC
                LIMIT ?
                """,
                (domain, max_patterns),
            )
            rows = cursor.fetchall()
        finally:
            connection.close()

        knowledge = self._format_knowledge(rows)
        self._cache.set(cache_key, knowledge, ttl_seconds=CONTEXT_TTL_SECONDS)
        return knowledge

    @staticmethod
    def _format_knowledge(rows: List[tuple]) -> str:
        parts = []
        for pattern_type, solution, _confidence, frequency in rows:
            if not solution:
                continue
            parts.append(f"\n[{pattern_type}] {solution}")
            if frequency > 1:
                parts.append(f" (used {frequency} times)")
        return "".join(parts)

    def record_competition_outcome(
        self,
        domain: str,
        agent_count: int,
        winner_agent: str,
        best_score: float,
        total_cost_usd: float,
    ) -> int:
        """Record a competition outcome and return its database id."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO competitions
                (domain, agent_count, winner_agent, best_score, total_cost_usd)
                VALUES (?, ?, ?, ?, ?)
                """,
                (domain, agent_count, winner_agent, best_score, total_cost_usd),
            )
            competition_id = cursor.lastrowid or 0
            connection.commit()
        finally:
            connection.close()
        return int(competition_id)

    def get_lessons_for_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all high-confidence lessons learned for a domain."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT pattern_type, solution, frequency, success_count, confidence
                FROM patterns
                WHERE domain = ? AND confidence > 0.5
                ORDER BY frequency DESC, confidence DESC
                LIMIT 20
                """,
                (domain,),
            )
            rows = cursor.fetchall()
        finally:
            connection.close()

        return [
            {
                "pattern_type": row[0],
                "solution": row[1],
                "frequency": row[2],
                "success_count": row[3],
                "confidence": row[4],
            }
            for row in rows
        ]

    def update_lesson_success(
        self, pattern_signature: str, domain: str, success: bool = True
    ) -> None:
        """Update the success or failure count of a stored pattern."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            if success:
                cursor.execute(
                    """
                    UPDATE patterns
                    SET success_count = success_count + 1,
                        confidence = MIN(1.0, confidence + 0.1)
                    WHERE signature = ? AND domain = ?
                    """,
                    (pattern_signature, domain),
                )
            else:
                cursor.execute(
                    """
                    UPDATE patterns
                    SET failure_count = failure_count + 1,
                        confidence = MAX(0.1, confidence - 0.1)
                    WHERE signature = ? AND domain = ?
                    """,
                    (pattern_signature, domain),
                )
            connection.commit()
        finally:
            connection.close()

        self._invalidate_context(domain)
        self._cache.delete(pattern_signature)

    def cleanup_expired_patterns(self, max_age_days: int = 30) -> int:
        """Delete patterns that have not been updated for max_age_days."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                DELETE FROM patterns
                WHERE datetime(updated_at) < datetime('now', ?)
                """,
                (f"-{int(max_age_days)} days",),
            )
            deleted = cursor.rowcount
            connection.commit()
        finally:
            connection.close()
        return int(deleted)

    def get_stats(self) -> Dict[str, Any]:
        """Return memory usage statistics."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM patterns")
            pattern_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM competitions")
            competition_count = cursor.fetchone()[0]
        finally:
            connection.close()

        return {
            "patterns_stored": pattern_count,
            "competitions_run": competition_count,
            "cache_hit_rate": self._cache.hit_rate,
            "clusters_active": len(self._cluster_manager.clusters),
        }
