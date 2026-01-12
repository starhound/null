"""Voice input manager for recording and transcribing audio."""

import asyncio
import io
import tempfile
import wave
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.settings import VoiceSettings

# Audio recording parameters
SAMPLE_RATE = 16000  # 16kHz - good balance for speech
CHANNELS = 1  # Mono
SAMPLE_WIDTH = 2  # 16-bit


class RecordingState(Enum):
    """Current state of voice recording."""

    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""

    text: str
    language: str | None = None
    duration: float | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.text)


class VoiceManager:
    """Manages voice recording and speech-to-text transcription.

    Supports push-to-talk (hold hotkey) or toggle (press to start/stop) modes.
    Uses sounddevice for cross-platform audio recording.
    """

    def __init__(self, settings: "VoiceSettings"):
        self.settings = settings
        self._state = RecordingState.IDLE
        self._audio_buffer: list[bytes] = []
        self._stream = None
        self._recording_task: asyncio.Task | None = None
        self._on_state_change: Callable[[RecordingState], None] | None = None
        self._on_transcription: Callable[[TranscriptionResult], None] | None = None
        self._sounddevice = None

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == RecordingState.RECORDING

    @property
    def is_available(self) -> bool:
        """Check if voice input is available (sounddevice installed)."""
        try:
            import sounddevice  # noqa: F401

            return True
        except ImportError:
            return False

    def set_state_callback(self, callback: Callable[[RecordingState], None]) -> None:
        """Set callback for state changes (for UI updates)."""
        self._on_state_change = callback

    def set_transcription_callback(
        self, callback: Callable[[TranscriptionResult], None]
    ) -> None:
        """Set callback for transcription results."""
        self._on_transcription = callback

    def _set_state(self, state: RecordingState) -> None:
        """Update state and notify callback."""
        self._state = state
        if self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception:
                pass

    def _ensure_sounddevice(self) -> bool:
        """Lazy import sounddevice."""
        if self._sounddevice is not None:
            return True
        try:
            import sounddevice

            self._sounddevice = sounddevice
            return True
        except ImportError:
            return False

    async def start_recording(self) -> bool:
        """Start recording audio.

        Returns:
            True if recording started successfully, False otherwise.
        """
        if self._state != RecordingState.IDLE:
            return False

        if not self._ensure_sounddevice():
            self._set_state(RecordingState.ERROR)
            return False

        try:
            self._audio_buffer = []
            self._set_state(RecordingState.RECORDING)

            self._stream = self._sounddevice.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=self._audio_callback,
            )
            self._stream.start()
            return True

        except Exception:
            self._set_state(RecordingState.ERROR)
            return False

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback - runs in audio thread."""
        self._audio_buffer.append(bytes(indata))

    async def stop_recording(self) -> TranscriptionResult:
        """Stop recording and transcribe the audio.

        Returns:
            TranscriptionResult with transcribed text or error.
        """
        if self._state != RecordingState.RECORDING:
            return TranscriptionResult(text="", error="Not recording")

        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._set_state(RecordingState.PROCESSING)

            if not self._audio_buffer:
                self._set_state(RecordingState.IDLE)
                return TranscriptionResult(text="", error="No audio recorded")

            audio_data = b"".join(self._audio_buffer)
            wav_data = self._create_wav(audio_data)
            result = await self._transcribe(wav_data)

            self._set_state(RecordingState.IDLE)

            if self._on_transcription:
                try:
                    self._on_transcription(result)
                except Exception:
                    pass

            return result

        except Exception as e:
            self._set_state(RecordingState.ERROR)
            return TranscriptionResult(text="", error=str(e))

    def cancel_recording(self) -> None:
        """Cancel recording without transcribing."""
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self._audio_buffer = []
        self._set_state(RecordingState.IDLE)

    def _create_wav(self, audio_data: bytes) -> bytes:
        """Convert raw PCM audio data to WAV format."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_data)
        return buffer.getvalue()

    async def _transcribe(self, wav_data: bytes) -> TranscriptionResult:
        """Transcribe audio using configured STT provider."""
        provider = self.settings.stt_provider.lower()

        if provider == "openai":
            return await self._transcribe_openai(wav_data)
        else:
            return TranscriptionResult(
                text="", error=f"Unsupported STT provider: {provider}"
            )

    async def _transcribe_openai(self, wav_data: bytes) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API."""
        try:
            from config import Config

            api_key = Config.get("openai_api_key")
            if not api_key:
                return TranscriptionResult(
                    text="", error="OpenAI API key not configured"
                )

            import openai

            client = openai.AsyncOpenAI(api_key=api_key)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_data)
                temp_path = Path(f.name)

            try:
                audio_bytes = await asyncio.to_thread(temp_path.read_bytes)
                response = await client.audio.transcriptions.create(
                    model=self.settings.stt_model,
                    file=("audio.wav", audio_bytes, "audio/wav"),
                    language=self.settings.language or None,
                )

                return TranscriptionResult(
                    text=response.text,
                    language=self.settings.language,
                )
            finally:
                await asyncio.to_thread(temp_path.unlink, missing_ok=True)

        except Exception as e:
            return TranscriptionResult(text="", error=f"Transcription failed: {e}")

    async def toggle_recording(self) -> TranscriptionResult | None:
        """Toggle recording on/off.

        Returns:
            TranscriptionResult if stopping recording, None if starting.
        """
        if self.is_recording:
            return await self.stop_recording()
        else:
            await self.start_recording()
            return None
