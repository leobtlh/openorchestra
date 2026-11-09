"""
Basic tests for CompetitionOrchestrator.

These tests verify the core functionality without requiring external services.
"""

import pytest


class TestCompetitionOrchestrator:
    """Test competition orchestration functionality"""

    @pytest.mark.asyncio
    async def test_basic_competition_run(self, memory):
        """Test a basic competition run with mocked adapters"""
        # This will test the workflow without actual OpenCode
        # by checking that components initialize correctly

        from openorchestra.core import CompetitionConfig, CompetitionOrchestrator

        # Create orchestrator
        orchestrator = CompetitionOrchestrator(memory=memory)

        # Create test config
        config = CompetitionConfig(
            domain="backend",
            task_description="Create a simple REST API endpoint",
            agent_count=2,  # Small for testing
            use_opencode=True,
            simulate=True,
            record_memory=False,  # Skip memory recording in tests
            dry_run=False,
        )

        # Run competition - this will use simulated agents
        result = await orchestrator.run_competition(config)

        # Verify result structure
        assert result is not None
        assert hasattr(result, "winner")
        assert hasattr(result, "total_score")
        assert hasattr(result, "agent_results")
        assert hasattr(result, "competition_id")

    def test_pattern_signature_creation(self):
        """Test pattern signature generation"""
        from openorchestra.core import PatternSignature

        sig = PatternSignature.from_context("backend", "security", "SELECT * FROM users")

        assert sig.domain == "backend"
        assert sig.category == "security"
        assert sig.code_hash is not None
        assert len(sig.pattern_fingerprint) == 12  # 12 char fingerprint

    def test_lru_cache_operations(self):
        """Test LRU cache functionality"""
        from openorchestra.core import LRUCache

        cache = LRUCache(maxsize=10)

        # Test set and get
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")

        assert result == {"data": "value"}
        assert "test_key" in cache

        # Test cache miss
        miss = cache.get("nonexistent")
        assert miss is None

    def test_domain_manager(self):
        """Test domain management"""
        from openorchestra.core import DomainManager

        dm = DomainManager()
        domains = dm.list_domains()

        assert len(domains) > 0
        assert any(d.id == "backend" for d in domains)
        assert any(d.id == "frontend_ui_ux" for d in domains)

        # Test domain retrieval
        backend = dm.get_domain("backend")
        assert backend is not None
        assert backend.id == "backend"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
