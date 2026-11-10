"""Tests for context compression."""

from openorchestra.core.context_compressor import ContextCompressor, compress_conversation


def test_extracts_errors_and_solutions() -> None:
    text = (
        "We found an error: database timeout\n"
        "Fix: use a connection pool\n"
        "Another error: missing index\n"
    )
    compressed = ContextCompressor().compress_context(text, domain="backend")

    assert len(compressed.technical_patterns) == 2
    assert compressed.technical_patterns[0]["type"] == "error"
    assert compressed.technical_patterns[0]["signature"]["code_hash"] != ""
    assert compressed.verified_solutions
    assert "connection pool" in compressed.verified_solutions[0]
    assert compressed.domain_tags == ["backend"]


def test_extracts_metrics_with_colon_and_space() -> None:
    compressed = ContextCompressor().compress_context("coverage: 85 accuracy 0.91 performance: 12")
    assert compressed.critical_metrics["coverage"] == "85"
    assert compressed.critical_metrics["accuracy"] == "0.91"
    assert compressed.critical_metrics["performance"] == "12"


def test_outputs_are_capped() -> None:
    text = "\n".join(f"error: boom {i}" for i in range(50))
    compressed = ContextCompressor().compress_context(text)

    assert len(compressed.technical_patterns) == 10


def test_storage_dict_is_small() -> None:
    compressed = ContextCompressor().compress_context("error: boom", "backend")
    data = compressed.to_storage_dict()

    assert data["patterns"] == 1
    assert data["tags"] == "backend"
    assert len(data["metrics"]) <= 200


def test_convenience_function() -> None:
    compressed = compress_conversation("issue: crash\nsolution: add guard", "qa_testing")
    assert compressed.domain_tags == ["qa_testing"]
    assert compressed.technical_patterns
    assert compressed.verified_solutions
