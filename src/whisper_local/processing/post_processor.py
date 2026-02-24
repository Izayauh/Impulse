"""
Post-processing pipeline for WhisperLocal.

Pipeline order:
1) numeric_formatter
2) punctuation_restorer
3) domain_corrections
4) code_mode (optional)
5) homophone_corrector (optional, slowest)
6) final_sanitizer (regex guardrail)
7) text_stylizer (optional, LLM-powered, full-text)
"""

from __future__ import annotations

import argparse
import difflib
import logging
import re
import time
from dataclasses import dataclass, field

from whisper_local.processing.code_mode import CodeModeCorrector
from whisper_local.processing.domain_corrections import DomainCorrector
from whisper_local.processing.homophone_corrector import HomophoneCorrector
from whisper_local.processing.text_stylizer import TextStylizer
from whisper_local.processing.numeric_formatter import format_numbers
from whisper_local.processing.final_sanitizer import sanitize_final_glitches
from whisper_local.processing.punctuation_restorer import restore_punctuation

logger = logging.getLogger(__name__)

try:
    from whisper_local.processing.domain_corrections import _PROFILES as _DOMAIN_PROFILES  # type: ignore
except Exception:
    _DOMAIN_PROFILES = {}


@dataclass
class PipelineConfig:
    """Configuration for PostProcessingPipeline."""

    enable_numeric: bool = True
    enable_punctuation: bool = True
    enable_domain: bool = True
    enable_code_mode: bool = False
    enable_homophone: bool = True
    enable_final_sanitizer: bool = True
    domains: list[str] = field(default_factory=list)
    homophone_model: str = "llama3.2:3b"
    stylization_profile: str = "off"
    ollama_model: str = "llama3.2:3b"
    ollama_endpoint: str = "http://127.0.0.1:11434"
    max_chunk_chars: int = 6000


@dataclass
class PipelineResult:
    """Detailed processing result."""

    text: str
    diff: str
    step_times_ms: dict[str, float]


class PostProcessingPipeline:
    """Composable text post-processing pipeline."""

    def __init__(self, config: PipelineConfig | dict | None = None, domains: list[str] | None = None):
        if config is None:
            cfg = PipelineConfig()
        elif isinstance(config, dict):
            cfg = PipelineConfig(**config)
        else:
            cfg = config

        if domains is not None:
            cfg.domains = list(domains)

        self.config = cfg
        self.last_result: PipelineResult | None = None

        valid_domains = self._filter_domains(self.config.domains)
        self.domain_corrector = DomainCorrector(valid_domains) if self.config.enable_domain else DomainCorrector([])

        self.code_corrector = CodeModeCorrector(enabled=self.config.enable_code_mode)
        self.homophone_corrector = HomophoneCorrector(model=self.config.homophone_model)
        self.homophone_corrector.set_enabled(self.config.enable_homophone)
        self.text_stylizer = TextStylizer(
            model=self.config.ollama_model,
            endpoint=self.config.ollama_endpoint,
        )

    def process(self, text: str) -> tuple[str, str]:
        """
        Process text through the configured pipeline.

        Returns:
            Tuple(final_text, unified_diff)
        """
        result = self.process_with_details(text)
        self.last_result = result
        return result.text, result.diff

    def process_with_details(self, text: str) -> PipelineResult:
        """Process text and return output + diff + per-step timings."""
        if not text:
            empty_timings = {
                "numeric_formatter": 0.0,
                "punctuation_restorer": 0.0,
                "domain_corrections": 0.0,
                "code_mode": 0.0,
                "homophone_corrector": 0.0,
                "final_sanitizer": 0.0,
                "text_stylizer": 0.0,
            }
            return PipelineResult(text="", diff="", step_times_ms=empty_timings)

        original = text
        chunks = self._chunk_text(text, self.config.max_chunk_chars)

        step_times = {
            "numeric_formatter": 0.0,
            "punctuation_restorer": 0.0,
            "domain_corrections": 0.0,
            "code_mode": 0.0,
            "homophone_corrector": 0.0,
            "final_sanitizer": 0.0,
            "text_stylizer": 0.0,
        }

        steps: list[tuple[str, bool, callable]] = [
            ("numeric_formatter", self.config.enable_numeric, self._apply_numeric),
            ("punctuation_restorer", self.config.enable_punctuation, self._apply_punctuation),
            ("domain_corrections", self.config.enable_domain, self._apply_domain),
            ("code_mode", self.config.enable_code_mode, self._apply_code),
            ("homophone_corrector", self.config.enable_homophone, self._apply_homophone),
            ("final_sanitizer", self.config.enable_final_sanitizer, self._apply_final_sanitizer),
        ]

        processed_chunks = []
        for chunk in chunks:
            current = chunk
            for step_name, enabled, step_fn in steps:
                if not enabled:
                    continue
                start = time.perf_counter()
                try:
                    updated = step_fn(current)
                    if updated is None:
                        updated = current
                except Exception as exc:
                    logger.warning("Step '%s' failed; keeping current text: %s", step_name, exc)
                    updated = current
                elapsed = (time.perf_counter() - start) * 1000.0
                step_times[step_name] += elapsed
                current = updated
            processed_chunks.append(current)

        final_text = "".join(processed_chunks)

        # Full-text stylization (runs on joined output, not per-chunk).
        if self.config.stylization_profile != "off":
            start = time.perf_counter()
            try:
                styled = self.text_stylizer.stylize(final_text, self.config.stylization_profile)
                if styled:
                    final_text = styled
            except Exception as exc:
                logger.warning("Text stylization failed; keeping plain text: %s", exc)
            step_times["text_stylizer"] = (time.perf_counter() - start) * 1000.0

        diff = self._make_diff(original, final_text)

        for step_name, ms in step_times.items():
            logger.info("Step %s took %.2f ms", step_name, ms)

        return PipelineResult(text=final_text, diff=diff, step_times_ms=step_times)

    def _apply_numeric(self, text: str) -> str:
        return format_numbers(text)

    def _apply_punctuation(self, text: str) -> str:
        return restore_punctuation(text)

    def _apply_domain(self, text: str) -> str:
        return self.domain_corrector.correct(text)

    def _apply_code(self, text: str) -> str:
        return self.code_corrector.correct(text)

    def _apply_homophone(self, text: str) -> str:
        return self.homophone_corrector.correct(text)

    def _apply_final_sanitizer(self, text: str) -> str:
        return sanitize_final_glitches(text)

    def _filter_domains(self, domains: list[str]) -> list[str]:
        if not domains:
            return []
        available = set(_DOMAIN_PROFILES.keys()) if isinstance(_DOMAIN_PROFILES, dict) else set()
        if not available:
            return domains

        valid = [d for d in domains if d in available]
        invalid = [d for d in domains if d not in available]
        if invalid:
            logger.warning("Ignoring unknown domain profiles: %s", ", ".join(invalid))
        return valid

    @staticmethod
    def _chunk_text(text: str, max_chunk_chars: int) -> list[str]:
        """Chunk long transcripts into sentence-ish windows."""
        if len(text) <= max_chunk_chars:
            return [text]

        # Split into sentence-like segments while preserving separators/spacing.
        segments = re.findall(r".+?(?:[.!?\n]+(?:\s+|$)|$)", text, flags=re.S)
        if not segments:
            return [text]

        chunks: list[str] = []
        current = ""

        for seg in segments:
            if not seg:
                continue

            if len(seg) > max_chunk_chars:
                if current:
                    chunks.append(current)
                    current = ""
                for i in range(0, len(seg), max_chunk_chars):
                    chunks.append(seg[i:i + max_chunk_chars])
                continue

            if len(current) + len(seg) <= max_chunk_chars:
                current += seg
            else:
                if current:
                    chunks.append(current)
                current = seg

        if current:
            chunks.append(current)

        return chunks or [text]

    @staticmethod
    def _make_diff(before: str, after: str) -> str:
        if before == after:
            return ""

        diff_lines = difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="original",
            tofile="processed",
            lineterm="",
        )
        return "\n".join(diff_lines)


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WhisperLocal post-processing pipeline")
    parser.add_argument("--input", required=True, help="Raw transcript text")
    parser.add_argument("--domains", nargs="*", default=[], help="Domain profiles (e.g., audio_engineering)")
    parser.add_argument("--code-mode", action="store_true", help="Enable code mode corrections")
    parser.add_argument("--no-homophone", action="store_true", help="Disable homophone correction")
    parser.add_argument("--no-punctuation", action="store_true", help="Disable punctuation restoration")
    parser.add_argument("--no-domain", action="store_true", help="Disable domain corrections")
    parser.add_argument("--no-numeric", action="store_true", help="Disable numeric formatting")
    parser.add_argument("--no-final-sanitizer", action="store_true", help="Disable final regex sanitizer")
    parser.add_argument("--stylize", choices=["off", "clean", "polished"], default="clean", help="Stylization profile")
    parser.add_argument("--homophone-model", default="llama3.2:3b", help="Ollama model for homophone correction")
    parser.add_argument("--ollama-model", default="llama3.2:3b", help="Ollama model for stylization")
    parser.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434", help="Ollama API endpoint")
    parser.add_argument("--max-chunk-chars", type=int, default=6000, help="Chunk size for long transcripts")
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _build_cli_parser().parse_args()

    cfg = PipelineConfig(
        enable_numeric=not args.no_numeric,
        enable_punctuation=not args.no_punctuation,
        enable_domain=not args.no_domain,
        enable_code_mode=args.code_mode,
        enable_homophone=not args.no_homophone,
        enable_final_sanitizer=not args.no_final_sanitizer,
        domains=list(args.domains),
        homophone_model=args.homophone_model,
        stylization_profile=args.stylize,
        ollama_model=args.ollama_model,
        ollama_endpoint=args.ollama_endpoint,
        max_chunk_chars=max(500, args.max_chunk_chars),
    )

    pipeline = PostProcessingPipeline(cfg)
    final_text, diff = pipeline.process(args.input)

    print("Processed Text:")
    print(final_text)
    print()
    print("Diff:")
    print(diff if diff else "(no changes)")
    print()
    print("Step Timings (ms):")
    if pipeline.last_result:
        for name, ms in pipeline.last_result.step_times_ms.items():
            print(f"  {name}: {ms:.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
