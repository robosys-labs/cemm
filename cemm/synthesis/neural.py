# CEMM-ARCH: Refer to cemm_architecture_gap_trace.md and AGENTS.md before modifying.
# Fix 5: Neural synthesis strategy using llama.cpp subprocess as local LLM fallback.

from __future__ import annotations
import subprocess
import shutil
from ..types.context_kernel import ContextKernel
from ..store.store import Store
from ..registry import Registry
from .result import SynthesisResult


class NeuralStrategy:
    """Local neural inference via llama.cpp. Falls back to "neural unavailable"
    when the llama-cli binary is not found.
    """

    def __init__(self, model_path: str = "models/llama-2-7b.gguf", binary: str = "llama-cli") -> None:
        self._model_path = model_path
        self._binary = binary
        self._available = shutil.which(binary) is not None

    def can_handle(self, params: dict) -> bool:
        return self._available and bool(params.get("prompt"))

    def render(
        self,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
        params: dict,
    ) -> SynthesisResult:
        if not self._available:
            return SynthesisResult(
                success=False,
                output="Neural strategy unavailable: llama-cli not found on PATH",
                strategy="neural",
                cost_ms=0.0,
                verified=False,
            )
        prompt = params.get("prompt", "")
        max_tokens = params.get("max_tokens", 128)
        temperature = params.get("temperature", 0.7)
        try:
            result = subprocess.run(
                [
                    self._binary,
                    "-m", self._model_path,
                    "--prompt", prompt,
                    "-n", str(max_tokens),
                    "--temp", str(temperature),
                    "--no-display-prompt",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return SynthesisResult(
                    success=False,
                    output=f"llama-cli error (rc={result.returncode}): {result.stderr.strip()}",
                    strategy="neural",
                    cost_ms=0.0,
                    verified=False,
                )
            output = result.stdout.strip()
            return SynthesisResult(
                success=True,
                output=output,
                strategy="neural",
                cost_ms=30.0,
                verified=False,
            )
        except FileNotFoundError:
            return SynthesisResult(
                success=False,
                output="Neural strategy unavailable: llama-cli binary not found",
                strategy="neural",
                cost_ms=0.0,
                verified=False,
            )
        except subprocess.TimeoutExpired:
            return SynthesisResult(
                success=False,
                output="Neural strategy timed out after 30s",
                strategy="neural",
                cost_ms=30.0,
            )
