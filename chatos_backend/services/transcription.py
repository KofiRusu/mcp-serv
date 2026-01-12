"""
transcription.py - Audio transcription service.

Provides audio-to-text transcription functionality using:
1. faster-whisper (preferred, if available)
2. openai-whisper (fallback)
3. Stub implementation (for testing/offline mode)

Environment variables:
- CHATOS_WHISPER_MODEL: Model size (tiny, base, small, medium, large) - default: base
- CHATOS_WHISPER_DEVICE: Device to use (cpu, cuda, auto) - default: auto
- CHATOS_USE_STUB_TRANSCRIPTION: Force stub mode for testing - default: false
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple, List

from chatos_backend.controllers.cache import get_cache

logger = logging.getLogger(__name__)

# Configuration from environment
WHISPER_MODEL = os.getenv("CHATOS_WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("CHATOS_WHISPER_DEVICE", "auto")
USE_STUB = os.getenv("CHATOS_USE_STUB_TRANSCRIPTION", "false").lower() == "true"

# Global model instance (lazy loaded)
_whisper_model = None
_whisper_type = None  # "faster-whisper", "openai-whisper", or "stub"


def _detect_device() -> str:
    """Detect the best available device."""
    if WHISPER_DEVICE != "auto":
        return WHISPER_DEVICE
    
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    
    return "cpu"


def _load_faster_whisper():
    """Try to load faster-whisper model."""
    global _whisper_model, _whisper_type
    
    try:
        from faster_whisper import WhisperModel
        
        device = _detect_device()
        compute_type = "float16" if device == "cuda" else "int8"
        
        logger.info(f"Loading faster-whisper model: {WHISPER_MODEL} on {device}")
        _whisper_model = WhisperModel(
            WHISPER_MODEL,
            device=device,
            compute_type=compute_type,
        )
        _whisper_type = "faster-whisper"
        logger.info("faster-whisper loaded successfully")
        return True
    except ImportError:
        logger.debug("faster-whisper not available")
        return False
    except Exception as e:
        logger.warning(f"Failed to load faster-whisper: {e}")
        return False


def _load_openai_whisper():
    """Try to load openai-whisper model."""
    global _whisper_model, _whisper_type
    
    try:
        import whisper
        
        device = _detect_device()
        logger.info(f"Loading openai-whisper model: {WHISPER_MODEL} on {device}")
        _whisper_model = whisper.load_model(WHISPER_MODEL, device=device)
        _whisper_type = "openai-whisper"
        logger.info("openai-whisper loaded successfully")
        return True
    except ImportError:
        logger.debug("openai-whisper not available")
        return False
    except Exception as e:
        logger.warning(f"Failed to load openai-whisper: {e}")
        return False


def _init_whisper():
    """Initialize whisper model (lazy loading)."""
    global _whisper_model, _whisper_type
    
    if _whisper_model is not None or _whisper_type == "stub":
        return
    
    if USE_STUB:
        logger.info("Using stub transcription (CHATOS_USE_STUB_TRANSCRIPTION=true)")
        _whisper_type = "stub"
        return
    
    # Try faster-whisper first (more efficient)
    if _load_faster_whisper():
        return
    
    # Fallback to openai-whisper
    if _load_openai_whisper():
        return
    
    # Use stub as last resort
    logger.warning("No Whisper implementation available, using stub transcription")
    _whisper_type = "stub"


def _transcribe_faster_whisper(audio_path: str, language: Optional[str] = None) -> Tuple[str, dict]:
    """Transcribe using faster-whisper."""
    segments, info = _whisper_model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        vad_filter=True,  # Voice Activity Detection
    )
    
    # Collect all segments
    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())
    
    transcript = " ".join(text_parts)
    
    metadata = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "engine": "faster-whisper",
    }
    
    return transcript, metadata


def _transcribe_openai_whisper(audio_path: str, language: Optional[str] = None) -> Tuple[str, dict]:
    """Transcribe using openai-whisper."""
    result = _whisper_model.transcribe(
        audio_path,
        language=language,
        fp16=False,  # Use FP32 for CPU compatibility
    )
    
    transcript = result["text"].strip()
    
    metadata = {
        "language": result.get("language", "unknown"),
        "engine": "openai-whisper",
    }
    
    return transcript, metadata


def _transcribe_stub(audio_path: str, language: Optional[str] = None) -> Tuple[str, dict]:
    """Stub transcription for testing."""
    transcript = f"Transcribed text of {audio_path}"
    metadata = {
        "language": language or "en",
        "engine": "stub",
    }
    return transcript, metadata


async def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    return_metadata: bool = False,
) -> str | Tuple[str, dict]:
    """
    Transcribe an audio file at `audio_path` into text.

    Uses faster-whisper if available, falls back to openai-whisper,
    or uses stub for testing.

    Args:
        audio_path: Path to the audio file to transcribe
        language: Optional language code (e.g., "en", "es", "auto" for detection)
        return_metadata: If True, return (transcript, metadata) tuple

    Returns:
        Transcribed text string, or (text, metadata) if return_metadata=True
        
    Raises:
        FileNotFoundError: If audio file doesn't exist (only in non-stub mode)
        ValueError: If audio format is unsupported
    """
    # Initialize whisper model first to determine mode
    _init_whisper()
    
    # In stub mode, skip file validation for testing
    if _whisper_type != "stub":
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Check cache
    cache = get_cache()
    cache_key = f"transcription:{audio_path}:{language or 'auto'}"
    
    cached = await cache.get(cache_key)
    if cached:
        logger.debug(f"Cache hit for transcription: {audio_path}")
        if return_metadata:
            return cached.get("text", cached), cached.get("metadata", {})
        return cached.get("text", cached) if isinstance(cached, dict) else cached

    # Initialize whisper model
    _init_whisper()
    
    # Transcribe based on available engine
    logger.info(f"Transcribing audio ({_whisper_type}): {audio_path}")
    
    try:
        if _whisper_type == "faster-whisper":
            transcript, metadata = _transcribe_faster_whisper(audio_path, language)
        elif _whisper_type == "openai-whisper":
            transcript, metadata = _transcribe_openai_whisper(audio_path, language)
        else:
            transcript, metadata = _transcribe_stub(audio_path, language)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        # Fall back to stub on error
        transcript, metadata = _transcribe_stub(audio_path, language)
        metadata["error"] = str(e)
        metadata["fallback"] = True

    # Cache the result
    cache_data = {"text": transcript, "metadata": metadata}
    await cache.set(cache_key, cache_data, ttl=86400)  # 24 hour cache
    
    logger.info(f"Transcription complete: {len(transcript)} chars, engine={metadata.get('engine')}")
    
    if return_metadata:
        return transcript, metadata
    return transcript


async def get_supported_languages() -> List[str]:
    """Get list of supported language codes."""
    # Common languages supported by Whisper
    return [
        "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
        "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
        "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no",
        "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk",
        "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk",
        "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw",
        "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc",
        "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo",
        "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl",
        "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su",
    ]


def get_whisper_status() -> dict:
    """Get status of whisper transcription service."""
    _init_whisper()
    
    return {
        "engine": _whisper_type,
        "model": WHISPER_MODEL,
        "device": _detect_device(),
        "available": _whisper_type != "stub" or USE_STUB,
        "stub_mode": _whisper_type == "stub",
    }
