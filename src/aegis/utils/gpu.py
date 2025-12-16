"""GPU detection and model recommendation utilities.

Provides functions to detect GPU availability and recommend
appropriate Ollama models based on available VRAM.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class GPUInfo:
    """Information about a detected GPU."""

    name: str
    memory_total_mb: int
    memory_free_mb: int
    driver_version: str
    cuda_version: str | None = None


@dataclass
class ModelRecommendation:
    """Recommended model based on GPU capabilities."""

    model_name: str
    model_size: str
    description: str
    min_vram_mb: int
    performance: str  # "fast", "balanced", "slow"


# Model recommendations by VRAM tier
MODEL_RECOMMENDATIONS: dict[str, list[ModelRecommendation]] = {
    "16gb+": [
        ModelRecommendation(
            model_name="llama3.2:8b",
            model_size="4.9GB",
            description="Excellent reasoning, fast inference",
            min_vram_mb=14000,
            performance="fast",
        ),
        ModelRecommendation(
            model_name="mistral:7b",
            model_size="4.1GB",
            description="Great for code and analysis",
            min_vram_mb=12000,
            performance="fast",
        ),
        ModelRecommendation(
            model_name="codellama:13b",
            model_size="7.4GB",
            description="Best for code generation",
            min_vram_mb=14000,
            performance="balanced",
        ),
    ],
    "8gb": [
        ModelRecommendation(
            model_name="llama3.2:3b",
            model_size="2.0GB",
            description="Good balance of speed and quality",
            min_vram_mb=6000,
            performance="fast",
        ),
        ModelRecommendation(
            model_name="phi3:mini",
            model_size="2.2GB",
            description="Fast, good for structured tasks",
            min_vram_mb=5000,
            performance="fast",
        ),
        ModelRecommendation(
            model_name="qwen2:7b",
            model_size="4.4GB",
            description="Strong multilingual support",
            min_vram_mb=7000,
            performance="balanced",
        ),
    ],
    "6gb": [
        ModelRecommendation(
            model_name="tinyllama:1b",
            model_size="637MB",
            description="Fast, lightweight model",
            min_vram_mb=2000,
            performance="fast",
        ),
        ModelRecommendation(
            model_name="phi3:mini",
            model_size="2.2GB",
            description="Good for structured output",
            min_vram_mb=4000,
            performance="balanced",
        ),
        ModelRecommendation(
            model_name="qwen2:1.5b",
            model_size="935MB",
            description="Efficient small model",
            min_vram_mb=3000,
            performance="fast",
        ),
    ],
    "4gb": [
        ModelRecommendation(
            model_name="tinyllama:1b",
            model_size="637MB",
            description="Best option for low VRAM",
            min_vram_mb=2000,
            performance="balanced",
        ),
        ModelRecommendation(
            model_name="phi3:mini",
            model_size="2.2GB",
            description="May be slow on 4GB",
            min_vram_mb=3500,
            performance="slow",
        ),
    ],
    "cpu_only": [
        ModelRecommendation(
            model_name="tinyllama:1b",
            model_size="637MB",
            description="CPU-friendly, may be slow",
            min_vram_mb=0,
            performance="slow",
        ),
    ],
}


def detect_nvidia_gpu() -> list[GPUInfo]:
    """Detect NVIDIA GPUs using nvidia-smi.

    Returns:
        List of detected GPUs with their information.
    """
    gpus: list[GPUInfo] = []

    try:
        # Query nvidia-smi for GPU information
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode != 0:
            return gpus

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                gpus.append(
                    GPUInfo(
                        name=parts[0],
                        memory_total_mb=int(float(parts[1])),
                        memory_free_mb=int(float(parts[2])),
                        driver_version=parts[3],
                    )
                )

    except FileNotFoundError:
        # nvidia-smi not found, no NVIDIA GPU
        pass
    except subprocess.TimeoutExpired:
        pass
    except (ValueError, IndexError):
        pass

    return gpus


def detect_intel_gpu() -> bool:
    """Detect Intel integrated GPU.

    Returns:
        True if Intel GPU is detected.
    """
    try:
        result = subprocess.run(
            ["lspci", "-v"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return "Intel" in result.stdout and "VGA" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_recommended_model(vram_mb: int | None = None) -> ModelRecommendation:
    """Get recommended Ollama model based on available VRAM.

    Args:
        vram_mb: Available VRAM in MB. If None, will auto-detect.

    Returns:
        Recommended model configuration.
    """
    if vram_mb is None:
        gpus = detect_nvidia_gpu()
        if gpus:
            vram_mb = gpus[0].memory_total_mb
        else:
            vram_mb = 0

    # Select appropriate tier
    if vram_mb >= 16000:
        tier = "16gb+"
    elif vram_mb >= 8000:
        tier = "8gb"
    elif vram_mb >= 6000:
        tier = "6gb"
    elif vram_mb >= 4000:
        tier = "4gb"
    else:
        tier = "cpu_only"

    recommendations = MODEL_RECOMMENDATIONS[tier]
    return recommendations[0]  # Return top recommendation


def check_gpu_availability() -> int:
    """Check GPU availability and print recommendations.

    This is called by the CLI gpu-check command.

    Returns:
        Exit code (0 for success).
    """
    print("=" * 60)
    print("AEGIS GPU Detection")
    print("=" * 60)
    print()

    # Detect NVIDIA GPUs
    gpus = detect_nvidia_gpu()

    if gpus:
        print("✓ NVIDIA GPU(s) detected:")
        print()
        for i, gpu in enumerate(gpus):
            print(f"  GPU {i}: {gpu.name}")
            print(f"    Total VRAM: {gpu.memory_total_mb} MB")
            print(f"    Free VRAM:  {gpu.memory_free_mb} MB")
            print(f"    Driver:     {gpu.driver_version}")
            print()

        # Get recommendation for first GPU
        recommendation = get_recommended_model(gpus[0].memory_total_mb)
        print("Recommended Ollama models for your GPU:")
        print()

        # Get tier based on VRAM
        vram = gpus[0].memory_total_mb
        if vram >= 16000:
            tier = "16gb+"
        elif vram >= 8000:
            tier = "8gb"
        elif vram >= 6000:
            tier = "6gb"
        elif vram >= 4000:
            tier = "4gb"
        else:
            tier = "cpu_only"

        for rec in MODEL_RECOMMENDATIONS[tier]:
            perf_indicator = {
                "fast": "⚡",
                "balanced": "⚖️",
                "slow": "🐢",
            }.get(rec.performance, "")
            print(f"  {perf_indicator} {rec.model_name} ({rec.model_size})")
            print(f"     {rec.description}")
            print()

        print("To install recommended model:")
        print(f"  ollama pull {recommendation.model_name}")

    else:
        # Check for Intel GPU
        if detect_intel_gpu():
            print("⚠ Intel integrated GPU detected")
            print()
            print("Intel GPUs have limited LLM support.")
            print("Options:")
            print("  1. Use CPU mode (slow but works)")
            print("  2. Use cloud APIs (Groq, Gemini, Together AI)")
            print()
        else:
            print("✗ No dedicated GPU detected")
            print()

        print("Recommendations without GPU:")
        print()
        print("  1. Use cloud LLM providers:")
        print("     - Groq (free tier, very fast)")
        print("     - Google Gemini (free tier)")
        print("     - Together AI (free tier)")
        print()
        print("  2. Use remote Ollama server:")
        print("     export AEGIS_LLM_OLLAMA_HOST=http://gpu-server:11434")
        print()
        print("  3. Use CPU mode (slow):")
        print("     ollama pull tinyllama:1b")

    print()
    print("=" * 60)
    return 0


def check_ollama_installed() -> tuple[bool, str | None]:
    """Check if Ollama is installed and get version.

    Returns:
        Tuple of (is_installed, version_string).
    """
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        return False, None
    except FileNotFoundError:
        return False, None
    except subprocess.TimeoutExpired:
        return False, None


def list_ollama_models() -> list[str]:
    """List installed Ollama models.

    Returns:
        List of installed model names.
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return []

        models = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            if line:
                parts = line.split()
                if parts:
                    models.append(parts[0])
        return models

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
