"""Unit tests for GPU detection utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aegis.utils.gpu import (
    GPUInfo,
    ModelRecommendation,
    check_gpu_availability,
    detect_nvidia_gpu,
    get_recommended_model,
    list_ollama_models,
)


class TestGPUDetection:
    """Tests for GPU detection functions."""

    def test_detect_nvidia_gpu_success(self) -> None:
        """Test successful NVIDIA GPU detection."""
        mock_output = "NVIDIA GeForce RTX 3080, 10240, 8500, 535.86.05"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            gpus = detect_nvidia_gpu()

            assert len(gpus) == 1
            assert gpus[0].name == "NVIDIA GeForce RTX 3080"
            assert gpus[0].memory_total_mb == 10240
            assert gpus[0].memory_free_mb == 8500
            assert gpus[0].driver_version == "535.86.05"

    def test_detect_nvidia_gpu_not_found(self) -> None:
        """Test when nvidia-smi is not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            gpus = detect_nvidia_gpu()

            assert gpus == []

    def test_detect_nvidia_gpu_timeout(self) -> None:
        """Test timeout during GPU detection."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 10)

            gpus = detect_nvidia_gpu()

            assert gpus == []

    def test_detect_nvidia_gpu_multiple(self) -> None:
        """Test detection of multiple GPUs."""
        mock_output = (
            "NVIDIA GeForce RTX 3080, 10240, 8500, 535.86.05\n"
            "NVIDIA GeForce RTX 3070, 8192, 6000, 535.86.05"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            gpus = detect_nvidia_gpu()

            assert len(gpus) == 2
            assert gpus[0].name == "NVIDIA GeForce RTX 3080"
            assert gpus[1].name == "NVIDIA GeForce RTX 3070"


class TestModelRecommendation:
    """Tests for model recommendation logic."""

    def test_recommendation_16gb_plus(self) -> None:
        """Test recommendation for 16GB+ VRAM."""
        recommendation = get_recommended_model(vram_mb=16000)

        assert recommendation.model_name == "llama3.2:8b"
        assert recommendation.min_vram_mb >= 12000

    def test_recommendation_8gb(self) -> None:
        """Test recommendation for 8GB VRAM."""
        recommendation = get_recommended_model(vram_mb=8000)

        assert recommendation.model_name == "llama3.2:3b"

    def test_recommendation_6gb(self) -> None:
        """Test recommendation for 6GB VRAM."""
        recommendation = get_recommended_model(vram_mb=6000)

        assert recommendation.model_name == "tinyllama:1b"

    def test_recommendation_4gb(self) -> None:
        """Test recommendation for 4GB VRAM."""
        recommendation = get_recommended_model(vram_mb=4000)

        assert recommendation.model_name == "tinyllama:1b"

    def test_recommendation_no_gpu(self) -> None:
        """Test recommendation for no GPU (CPU only)."""
        recommendation = get_recommended_model(vram_mb=0)

        assert recommendation.model_name == "tinyllama:1b"
        assert recommendation.performance == "slow"

    def test_recommendation_auto_detect(self) -> None:
        """Test recommendation with auto-detection."""
        with patch("aegis.utils.gpu.detect_nvidia_gpu") as mock_detect:
            mock_detect.return_value = [
                GPUInfo(
                    name="Test GPU",
                    memory_total_mb=8192,
                    memory_free_mb=6000,
                    driver_version="535.0",
                )
            ]

            recommendation = get_recommended_model()

            assert recommendation.model_name == "llama3.2:3b"


class TestOllamaUtils:
    """Tests for Ollama utility functions."""

    def test_list_ollama_models_success(self) -> None:
        """Test listing installed Ollama models."""
        mock_output = (
            "NAME                ID              SIZE      MODIFIED\n"
            "llama3.2:3b         abc123          2.0 GB    2 days ago\n"
            "mistral:7b          def456          4.1 GB    5 days ago"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            models = list_ollama_models()

            assert len(models) == 2
            assert "llama3.2:3b" in models
            assert "mistral:7b" in models

    def test_list_ollama_models_not_installed(self) -> None:
        """Test when Ollama is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            models = list_ollama_models()

            assert models == []

    def test_list_ollama_models_empty(self) -> None:
        """Test when no models are installed."""
        mock_output = "NAME                ID              SIZE      MODIFIED\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
            )

            models = list_ollama_models()

            assert models == []


class TestGPUCheck:
    """Tests for GPU check CLI function."""

    def test_check_gpu_availability_with_nvidia(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test GPU check with NVIDIA GPU present."""
        with patch("aegis.utils.gpu.detect_nvidia_gpu") as mock_detect:
            mock_detect.return_value = [
                GPUInfo(
                    name="NVIDIA GeForce RTX 3080",
                    memory_total_mb=10240,
                    memory_free_mb=8500,
                    driver_version="535.86.05",
                )
            ]

            result = check_gpu_availability()

            assert result == 0
            captured = capsys.readouterr()
            assert "NVIDIA GPU" in captured.out
            assert "RTX 3080" in captured.out

    def test_check_gpu_availability_no_gpu(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test GPU check with no GPU."""
        with (
            patch("aegis.utils.gpu.detect_nvidia_gpu") as mock_nvidia,
            patch("aegis.utils.gpu.detect_intel_gpu") as mock_intel,
        ):
            mock_nvidia.return_value = []
            mock_intel.return_value = False

            result = check_gpu_availability()

            assert result == 0
            captured = capsys.readouterr()
            assert "No dedicated GPU detected" in captured.out
