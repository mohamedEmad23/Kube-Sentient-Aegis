#!/usr/bin/env python3
"""Diagnostic script to verify AEGIS environment configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx


def check_env_vars() -> dict[str, bool]:
    """Check if required environment variables are set."""
    print("=" * 80)
    print("ENVIRONMENT VARIABLES")
    print("=" * 80)

    results = {}

    # Groq
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API")
    results["GROQ_API_KEY"] = bool(groq_key)
    print(f"GROQ_API_KEY: {'✓ SET' if groq_key else '✗ MISSING'}")
    if groq_key:
        print(f"  Value: {groq_key[:10]}...")

    # Gemini
    gemini_key = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API") or os.getenv("GOOGLE_API_KEY")
    )
    results["GEMINI_API_KEY"] = bool(gemini_key)
    print(f"GEMINI_API_KEY: {'✓ SET' if gemini_key else '✗ MISSING'}")
    if gemini_key:
        print(f"  Value: {gemini_key[:10]}...")

    print()
    return results


def check_groq_api() -> bool:
    """Test Groq API connectivity."""
    print("=" * 80)
    print("GROQ API CONNECTIVITY")
    print("=" * 80)

    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API")
    if not api_key:
        print("✗ SKIP: No API key found")
        print()
        return False

    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5,
            },
            timeout=10,
        )

        if resp.status_code == 200:
            print("✓ SUCCESS: Groq API is accessible")
            print(f"  Status: {resp.status_code}")
            print()
            return True
        print(f"✗ FAILED: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
        print()
        return False

    except Exception as exc:
        print(f"✗ ERROR: {exc}")
        print()
        return False


def check_gemini_api() -> bool:
    """Test Gemini API connectivity."""
    print("=" * 80)
    print("GEMINI API CONNECTIVITY")
    print("=" * 80)

    api_key = (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API") or os.getenv("GOOGLE_API_KEY")
    )
    if not api_key:
        print("✗ SKIP: No API key found")
        print()
        return False

    try:
        resp = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            params={"key": api_key},
            json={
                "contents": [{"role": "user", "parts": [{"text": "test"}]}],
                "generationConfig": {"maxOutputTokens": 5},
            },
            timeout=10,
        )

        if resp.status_code == 200:
            print("✓ SUCCESS: Gemini API is accessible")
            print(f"  Status: {resp.status_code}")
            print()
            return True
        print(f"✗ FAILED: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
        print()
        return False

    except Exception as exc:
        print(f"✗ ERROR: {exc}")
        print()
        return False


def check_ollama() -> bool:
    """Test Ollama connectivity."""
    print("=" * 80)
    print("OLLAMA CONNECTIVITY")
    print("=" * 80)

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    try:
        resp = httpx.get(f"{ollama_url}/api/tags", timeout=5)

        if resp.status_code == 200:
            models = resp.json().get("models", [])
            print("✓ SUCCESS: Ollama is accessible")
            print(f"  URL: {ollama_url}")
            print(f"  Models: {len(models)} available")
            print()
            return True
        print(f"✗ FAILED: HTTP {resp.status_code}")
        print()
        return False

    except Exception as exc:
        print(f"✗ ERROR: {exc}")
        print()
        return False


def check_prometheus() -> bool:
    """Test Prometheus connectivity."""
    print("=" * 80)
    print("PROMETHEUS CONNECTIVITY")
    print("=" * 80)

    prom_url = os.getenv("OBS_PROMETHEUS_URL", "http://localhost:9090")

    try:
        resp = httpx.get(f"{prom_url}/-/healthy", timeout=5)

        if resp.status_code == 200:
            print("✓ SUCCESS: Prometheus is accessible")
            print(f"  URL: {prom_url}")
            print()
            return True
        print(f"✗ FAILED: HTTP {resp.status_code}")
        print()
        return False

    except Exception as exc:
        print(f"✗ ERROR: {exc}")
        print()
        return False


def check_grafana() -> bool:
    """Test Grafana connectivity."""
    print("=" * 80)
    print("GRAFANA CONNECTIVITY")
    print("=" * 80)

    grafana_url = os.getenv("OBS_GRAFANA_URL", "http://localhost:3000")

    try:
        resp = httpx.get(f"{grafana_url}/api/health", timeout=5)

        if resp.status_code == 200:
            print("✓ SUCCESS: Grafana is accessible")
            print(f"  URL: {grafana_url}")
            print()
            return True
        print(f"✗ FAILED: HTTP {resp.status_code}")
        print()
        return False

    except Exception as exc:
        print(f"✗ ERROR: {exc}")
        print()
        return False


def check_settings_loading() -> bool:
    """Test if settings load correctly."""
    print("=" * 80)
    print("SETTINGS LOADING")
    print("=" * 80)

    try:
        # Add src to path
        repo_root = Path(__file__).parent.parent
        sys.path.insert(0, str(repo_root / "src"))

        from aegis.config.settings import settings

        print("✓ Settings loaded successfully")
        print(f"  Environment: {settings.environment}")
        print(f"  Groq enabled: {settings.groq.enabled}")
        print(f"  Groq API key set: {bool(settings.groq.api_key)}")
        print(f"  Gemini enabled: {settings.gemini.enabled}")
        print(f"  Gemini API key set: {bool(settings.gemini.api_key)}")
        print(f"  Ollama enabled: {settings.ollama.enabled}")
        print(f"  LLM providers enabled: {settings.llm_providers_enabled}")
        print(f"  Security Trivy: {settings.security.trivy_enabled}")
        print(f"  Security Kubesec: {settings.security.kubesec_enabled}")
        print(f"  Security Falco: {settings.security.falco_enabled}")
        print()
        return True

    except Exception as exc:
        print(f"✗ ERROR: {exc}")
        print()
        return False


def main() -> int:
    """Run all diagnostic checks."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "AEGIS ENVIRONMENT DIAGNOSTICS" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    results = {}

    # Check environment variables
    env_results = check_env_vars()

    # Check settings loading
    results["settings"] = check_settings_loading()

    # Check LLM providers
    results["groq"] = check_groq_api()
    results["gemini"] = check_gemini_api()
    results["ollama"] = check_ollama()

    # Check observability stack
    results["prometheus"] = check_prometheus()
    results["grafana"] = check_grafana()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for name, status in results.items():
        symbol = "✓" if status else "✗"
        print(f"  {symbol} {name.upper()}")

    print()
    print(f"Total: {passed}/{total} checks passed")
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
