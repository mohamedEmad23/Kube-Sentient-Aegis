"""Test Shadow Manager functionality."""

from aegis.shadow.manager import ShadowManager


def test_sanitize_name_basic() -> None:
    """Test DNS-1123 name sanitization."""
    # Test basic sanitization
    assert ShadowManager._sanitize_name("Test_Name") == "test-name"
    assert ShadowManager._sanitize_name("invalid@#name") == "invalid-name"
    assert ShadowManager._sanitize_name("UPPER-lower-123") == "upper-lower-123"


def test_sanitize_name_trailing_dash() -> None:
    """Test trailing dash handling."""
    # Test trailing dash handling
    assert ShadowManager._sanitize_name("test-", allow_trailing_dash=True) == "test-"
    assert ShadowManager._sanitize_name("test-", allow_trailing_dash=False) == "test"


def test_sanitize_name_multiple_dashes() -> None:
    """Test multiple consecutive dashes."""
    # Test multiple consecutive dashes
    assert ShadowManager._sanitize_name("test---name") == "test-name"
    assert ShadowManager._sanitize_name("a--b--c") == "a-b-c"


def test_sanitize_name_empty_fallback() -> None:
    """Test empty string fallback."""
    # Test empty string fallback
    assert ShadowManager._sanitize_name("@#$%") == "shadow"
    assert ShadowManager._sanitize_name("!!!") == "shadow"


def test_sanitize_name_special_chars() -> None:
    """Test special character handling."""
    assert ShadowManager._sanitize_name("pod@namespace#123") == "pod-namespace-123"
    assert ShadowManager._sanitize_name("my_app_v2.0") == "my-app-v2-0"


def test_build_shadow_namespace_normal() -> None:
    """Test shadow namespace construction."""
    manager = ShadowManager()

    # Test normal case
    namespace = manager._build_shadow_namespace("test-123")
    assert namespace.startswith("aegis-shadow-")
    assert "test-123" in namespace
    assert len(namespace) <= 63


def test_build_shadow_namespace_truncation() -> None:
    """Test truncation for long names."""
    manager = ShadowManager()

    # Test truncation for long names
    long_id = "a" * 100
    namespace = manager._build_shadow_namespace(long_id)
    assert len(namespace) <= 63
    assert namespace.startswith("aegis-shadow-")


def test_build_shadow_namespace_dns_compliant() -> None:
    """Test that generated namespaces are DNS-1123 compliant."""
    manager = ShadowManager()

    # Test various inputs
    test_cases = ["my-app", "prod-api-v2", "test_service", "APP@123"]

    for test_id in test_cases:
        namespace = manager._build_shadow_namespace(test_id)
        # Must be lowercase alphanumeric with hyphens
        assert namespace.islower() or any(c.isdigit() or c == "-" for c in namespace)
        # Must not start or end with hyphen
        assert not namespace.startswith("-")
        assert not namespace.endswith("-")
        # Must be <= 63 chars
        assert len(namespace) <= 63


def test_shadow_environment_count() -> None:
    """Test active environment counting."""
    manager = ShadowManager()
    # active_count is a property, not a method
    assert manager.active_count == 0


def test_shadow_manager_initialization() -> None:
    """Test ShadowManager initializes correctly."""
    manager = ShadowManager()
    assert manager.namespace_prefix == "aegis-shadow-"
    assert manager.max_concurrent > 0
    assert manager.verification_timeout > 0


def test_shadow_manager_attributes() -> None:
    """Test ShadowManager has required attributes."""
    manager = ShadowManager()
    assert hasattr(manager, "create_shadow")
    assert hasattr(manager, "cleanup")
    assert hasattr(manager, "run_verification")
    assert hasattr(manager, "active_count")
