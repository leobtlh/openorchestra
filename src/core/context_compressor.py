"""
Intelligent context compression for memory efficiency.

Compresses conversation context while preserving technical patterns
and solutions without exponential storage growth.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class CompressedContext:
    """
    Compressed context containing only essential pattern information.
    
    Stores patterns, solutions, and metrics without full conversation history.
    """
    technical_patterns: List[Dict] = field(default_factory=list)
    verified_solutions: List[str] = field(default_factory=list)
    critical_metrics: Dict = field(default_factory=dict)
    domain_tags: List[str] = field(default_factory=list)
    
    def to_storage_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'patterns': len(self.technical_patterns),
            'solutions': len(self.verified_solutions),
            'metrics': str(self.critical_metrics)[:200],  # Keep small
            'tags': ','.join(self.domain_tags)
        }


class ContextCompressor:
    """
    Intelligent compression of conversation context.
    
    Extracts patterns and solutions while discarding conversational fluff.
    """
    
    # Patterns indicating technical content
    ERROR_PATTERNS = [
        r'error[:\s]*',
        r'exception[:\s]*',
        r'fail[:\s]*',
        r'issue[:\s]*',
        r'bug[:\s]*'
    ]
    
    SOLUTION_PATTERNS = [
        r'fix[:\s]*',
        r'solution[:\s]*',
        r'recommendation[:\s]*',
        r'approach[:\s]*'
    ]
    
    METRIC_PATTERNS = [
        r'accuracy[:\s]*[\d.]+',
        r'coverage[:\s]*[\d.]+',
        r'performance[:\s]*[\d.]+',
        r'score[:\s]*[\d.]+'
    ]
    
    def compress_context(self, conversation: str, domain: str = "") -> CompressedContext:
        """
        Compress a conversation into essential patterns.
        
        Args:
            conversation: Full conversation text
            domain: Competency domain
            
        Returns:
            CompressedContext with essential information only
        """
        return CompressedContext(
            technical_patterns=self._extract_patterns(conversation),
            verified_solutions=self._extract_solutions(conversation),
            critical_metrics=self._extract_metrics(conversation),
            domain_tags=[domain] if domain else []
        )
    
    def _extract_patterns(self, text: str) -> List[Dict]:
        """Extract technical patterns from conversation"""
        patterns = []
        
        for pattern in self.ERROR_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 200)
                context = text[start:end].strip()
                
                patterns.append({
                    'type': 'error',
                    'signature': {'domain': '', 'category': '', 'code_hash': ''[:8]},
                    'context': context[:100],  # Keep small
                    'source_line': match.start()
                })
        
        return patterns[:10]  # Cap at 10 patterns
    
    def _extract_solutions(self, text: str) -> List[str]:
        """Extract verified solutions"""
        solutions = []
        
        for pattern in self.SOLUTION_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start = match.end()
                end = min(len(text), start + 150)
                solution = text[start:end].strip()
                
                # Clean up solution text
                if solution and solution not in solutions:
                    solutions.append(solution.split('\n')[0])  # First line only
        
        return solutions[:5]  # Top 5 solutions
    
    def _extract_metrics(self, text: str) -> Dict:
        """Extract performance/quality metrics"""
        metrics = {}
        
        for pattern in self.METRIC_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                metric_name = match.group(0).split(':')[0].strip()
                metric_value = match.group(0).split(':')[-1].strip()
                metrics[metric_name] = metric_value
        
        return metrics


def compress_conversation(conversation: str, domain: str = "") -> CompressedContext:
    """Convenience function for compressing conversation"""
    compressor = ContextCompressor()
    return compressor.compress_context(conversation, domain)