"""
Optimized persistent memory system for OpenOrchestra.

Uses hierarchical patterns, caching, and compression for efficient
storage and retrieval without exponential growth.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from openorchestra.core.lru_cache import LRUCache
from openorchestra.core.pattern_signature import PatternSignature, PatternMetadata
from openorchestra.core.pattern_cluster import PatternClusterManager
from openorchestra.core.context_compressor import ContextCompressor, CompressedContext


class CompetitionMemory:
    """
    Optimized persistent memory with:
    - LRU cache for hot patterns
    - Hierarchical pattern storage
    - Context compression
    - Automatic cleanup
    """

    def __init__(self, db_path: str = ".openorchestra/memory.db"):
        self.db_path = db_path
        self._ensure_database()
        
        # Performance optimizations
        self._cache = LRUCache(maxsize=500, ttl_seconds=3600)
        self._cluster_manager = PatternClusterManager(max_clusters=50)
        self._compressor = ContextCompressor()
        
        # Statistics
        self._stats = {
            'patterns_stored': 0,
            'cache_hits': 0,
            'db_queries': 0
        }
    
    def _ensure_database(self) -> None:
        """Create optimized database schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Patterns table with compact storage
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
        
        # Create indexes for fast lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON patterns(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signature ON patterns(signature)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON patterns(pattern_type)")
        
        # Competition results table
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
        
        conn.commit()
        conn.close()
    
    def record_pattern(
        self,
        domain: str,
        pattern_type: str,
        description: str,
        solution: str,
        confidence: float = 0.5
    ) -> str:
        """
        Record a learned pattern with optimized storage.
        
        Uses signature-based deduplication and compression.
        """
        # Create compact signature
        sig = PatternSignature.from_context(domain, pattern_type, solution)
        signature = sig.to_compact_vector()
        
        # Check cache first
        cached = self._cache.get(signature)
        if cached:
            self._stats['cache_hits'] += 1
            return signature
        
        # Check if pattern exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM patterns WHERE signature = ?", (signature,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing pattern
            cursor.execute("""
                UPDATE patterns 
                SET confidence = ?, frequency = frequency + 1, updated_at = ?
                WHERE signature = ?
            """, (confidence, datetime.now().isoformat(), signature))
        else:
            # Insert new pattern with compressed storage
            json_data = json.dumps({
                'description': description[:200],  # Limited storage
                'domain_signature': sig.domain_signature,
                'category_signature': sig.category_signature
            })
            
            cursor.execute("""
                INSERT INTO patterns 
                (domain, signature, pattern_type, solution, json_data, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (domain, signature, pattern_type, solution, json_data, confidence))
            
            self._stats['patterns_stored'] += 1
        
        conn.commit()
        conn.close()
        
        # Cache for future lookups
        self._cache.set(signature, {
            'domain': domain,
            'type': pattern_type,
            'solution': solution,
            'confidence': confidence
        })
        
        # Add to cluster manager
        self._cluster_manager.add_pattern(
            pattern_data={'signature': sig.__dict__},
            solution=solution
        )
        
        return signature
    
    def get_context_knowledge(self, domain: str, max_patterns: int = 5) -> str:
        """
        Get contextual knowledge for a domain with optimized retrieval.
        
        Uses caching and hierarchical lookup for performance.
        """
        # Check cache for combined result
        cache_key = f"context_{domain}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        
        # Build knowledge string from patterns
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pattern_type, solution, confidence, frequency
            FROM patterns 
            WHERE domain = ? 
            ORDER BY confidence DESC, frequency DESC
            LIMIT ?
        """, (domain, max_patterns))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Build formatted knowledge string
        parts = []
        for pattern_type, solution, confidence, frequency in rows:
            if solution and confidence > 0.5:
                parts.append(f"\n[{pattern_type}] {solution}")
                if frequency > 1:
                    parts.append(f" (used {frequency} times)")
        
        knowledge = "".join(parts) if parts else "No patterns found for this domain yet."
        
        # Cache for future use (shorter TTL for accuracy)
        self._cache.set(cache_key, knowledge, ttl_seconds=1800)
        
        return knowledge
    
    def record_competition_outcome(
        self,
        domain: str,
        agent_count: int,
        winner_agent: str,
        best_score: float,
        total_cost_usd: float
    ) -> int:
        """Record a competition outcome"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO competitions 
            (domain, agent_count, winner_agent, best_score, total_cost_usd)
            VALUES (?, ?, ?, ?, ?)
        """, (domain, agent_count, winner_agent, best_score, total_cost_usd))
        
        comp_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return comp_id
    
    def get_lessons_for_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all lessons learned for a domain"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pattern_type, solution, frequency, success_count, confidence
            FROM patterns 
            WHERE domain = ? AND confidence > 0.5
            ORDER BY frequency DESC, confidence DESC
            LIMIT 20
        """, (domain,))
        
        lessons = []
        for row in cursor.fetchall():
            lessons.append({
                "pattern_type": row[0],
                "solution": row[1],
                "frequency": row[2],
                "success_count": row[3],
                "confidence": row[4]
            })
        
        conn.close()
        return lessons
    
    def update_lesson_success(self, pattern_signature: str, domain: str, success: bool = True) -> None:
        """Update success count for a pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if success:
            cursor.execute("""
                UPDATE patterns 
                SET success_count = success_count + 1,
                    confidence = MIN(1.0, confidence + 0.1)
                WHERE signature = ? AND domain = ?
            """, (pattern_signature, domain))
        else:
            cursor.execute("""
                UPDATE patterns 
                SET failure_count = failure_count + 1,
                    confidence = MAX(0.1, confidence - 0.1)
                WHERE signature = ? AND domain = ?
            """, (pattern_signature, domain))
        
        conn.commit()
        conn.close()
        
        # Invalidate cache
        self._cache = LRUCache()  # Simple reset for consistency
    
    def cleanup_expired_patterns(self, max_age_days: int = 30) -> int:
        """Remove old patterns to manage storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now().timestamp() - (max_age_days * 86400)
        
        cursor.execute("""
            DELETE FROM patterns 
            WHERE datetime(updated_at) < datetime(?, 'unixepoch')
        """, (str(int(cutoff_date)),))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM patterns")
        pattern_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM competitions")
        competition_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'patterns_stored': pattern_count,
            'competitions_run': competition_count,
            'cache_hit_rate': self._cache.hit_rate if hasattr(self._cache, 'hit_rate') else 0,
            'clusters_active': len(self._cluster_manager.clusters)
        }