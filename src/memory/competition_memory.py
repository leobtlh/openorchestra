"""
Persistent memory system for OpenOrchestra.

Tracks lessons learned from competitions to improve future agent performance.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json


@dataclass
class CompetitionPattern:
    """A learned pattern from a competition"""
    domain: str
    pattern_type: str  # error, solution, improvement, anti-pattern
    description: str
    solution: str
    confidence: float
    timestamp: str


@dataclass
class AgentPerformance:
    """Performance record for an agent in a competition"""
    competition_id: str
    agent_id: str
    domain: str
    score: float
    solution_summary: str
    errors: List[str]
    improvements: List[str]


class CompetitionMemory:
    """
    Persistent memory for learning from competitions.
    
    Stores patterns, anti-patterns, and solutions to improve
    future agent performance.
    """

    def __init__(self, db_path: str = ".openorchestra/memory.db"):
        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self) -> None:
        """Create database and tables if they don't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                solution TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                score REAL NOT NULL,
                solution_summary TEXT,
                errors TEXT,
                improvements TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                pattern TEXT NOT NULL,
                solution TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

    def record_pattern(
        self,
        domain: str,
        pattern_type: str,
        description: str,
        solution: str,
        confidence: float = 1.0
    ) -> int:
        """
        Record a learned pattern from a competition.
        
        Args:
            domain: The competency domain
            pattern_type: error, solution, improvement, or anti-pattern
            description: Description of the pattern
            solution: How to address or replicate it
            confidence: Confidence level in the pattern
            
        Returns:
            ID of the recorded pattern
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO patterns (domain, pattern_type, description, solution, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (domain, pattern_type, description, solution, confidence, datetime.now().isoformat()))
        
        pattern_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return pattern_id

    def record_agent_performance(
        self,
        competition_id: str,
        agent_id: str,
        domain: str,
        score: float,
        solution_summary: str = "",
        errors: Optional[List[str]] = None,
        improvements: Optional[List[str]] = None
    ) -> int:
        """
        Record an agent's performance in a competition.
        
        Returns:
            ID of the recorded performance
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_performance 
            (competition_id, agent_id, domain, score, solution_summary, errors, improvements)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            competition_id,
            agent_id,
            domain,
            score,
            solution_summary,
            json.dumps(errors or []),
            json.dumps(improvements or [])
        ))
        
        performance_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return performance_id

    def get_relevant_patterns(
        self,
        domain: str,
        pattern_type: Optional[str] = None,
        limit: int = 10
    ) -> List[CompetitionPattern]:
        """
        Get patterns relevant to a domain.
        
        Args:
            domain: The competency domain
            pattern_type: Optional filter by pattern type
            limit: Maximum number of patterns to return
            
        Returns:
            List of relevant patterns
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT domain, pattern_type, description, solution, confidence, timestamp
            FROM patterns WHERE domain = ?
        """
        params = [domain]
        
        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)
        
        query += " ORDER BY confidence DESC, timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append(CompetitionPattern(
                domain=row[0],
                pattern_type=row[1],
                description=row[2],
                solution=row[3],
                confidence=row[4],
                timestamp=row[5]
            ))
        
        conn.close()
        return patterns

    def get_lessons_for_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all lessons learned for a domain.
        
        Returns:
            List of lesson dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pattern, solution, usage_count, success_count, last_used
            FROM lessons WHERE domain = ? ORDER BY success_count DESC
        """, (domain,))
        
        lessons = []
        for row in cursor.fetchall():
            lessons.append({
                "pattern": row[0],
                "solution": row[1],
                "usage_count": row[2],
                "success_count": row[3],
                "last_used": row[4]
            })
        
        conn.close()
        return lessons

    def update_lesson_success(self, pattern: str, domain: str, success: bool = True) -> None:
        """Update the success count for a pattern/lesson"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO lessons (domain, pattern, solution, usage_count, success_count, last_used)
            VALUES (?, ?, ?, 0, 0, ?)
        """, (domain, pattern, "Learned pattern", datetime.now().isoformat()))
        
        if success:
            cursor.execute("""
                UPDATE lessons 
                SET usage_count = usage_count + 1,
                    success_count = success_count + 1,
                    last_used = ?
                WHERE pattern = ? AND domain = ?
            """, (datetime.now().isoformat(), pattern, domain))
        else:
            cursor.execute("""
                UPDATE lessons 
                SET usage_count = usage_count + 1,
                    last_used = ?
                WHERE pattern = ? AND domain = ?
            """, (datetime.now().isoformat(), pattern, domain))
        
        conn.commit()
        conn.close()

    def get_context_knowledge(self, domain: str, limit: int = 5) -> str:
        """
        Get contextual knowledge to inject into agent prompts.
        
        Returns:
            Formatted string with learned patterns and lessons
        """
        patterns = self.get_relevant_patterns(domain, limit=limit)
        lessons = self.get_lessons_for_domain(domain)
        
        parts = []
        
        if lessons:
            parts.append("=== LEARNED PATTERNS ===")
            for lesson in lessons[:3]:
                parts.append(f"\nPattern: {lesson['pattern']}")
                parts.append(f"Solution: {lesson['solution']}")
                if lesson['success_count'] > 0:
                    parts.append(f"Success rate: {lesson['success_count']}/{lesson['usage_count']}")
        
        if patterns:
            parts.append("\n=== RECENT PATTERNS ===")
            for pattern in patterns[:3]:
                parts.append(f"\n[{pattern.pattern_type}] {pattern.description}")
                parts.append(f"Solution: {pattern.solution}")
        
        return "\n".join(parts) if parts else "No contextual knowledge available yet."