"""Unit tests for VoiceManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.voice import (
    CHANNELS,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    RecordingState,
    TranscriptionResult,
    VoiceManager,
)


@pytest.fixture
def mock_settings():
    """Create mock voice settings."""
    settings = MagicMock()
    settings.stt_provider = "openai"
    settings.stt_model = "whisper-1"
    settings.language = "en"
    return settings


@pytest.fixture
def voice_manager(mock_settings):
    """Create VoiceManager instance with mock settings."""
    return VoiceManager(mock_settings)


class TestVoiceManagerInit:
    """Tests for VoiceManager initialization."""

    def test_initial_state_is_idle(self, voice_manager):
        assert voice_manager.state == RecordingState.IDLE

    def test_initial_not_recording(self, voice_manager):
        assert voice_manager.is_recording is False

    def test_settings_stored(self, voice_manager, mock_settings):
        assert voice_manager.settings is mock_settings

    def test_audio_buffer_empty(self, voice_manager):
        assert voice_manager._audio_buffer == []

    def test_stream_is_none(self, voice_manager):
        assert voice_manager._stream is None


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_success_with_text(self):
        result = TranscriptionResult(text="hello world")
        assert result.success is True

    def test_failure_with_error(self):
        result = TranscriptionResult(text="", error="Something went wrong")
        assert result.success is False

    def test_failure_with_empty_text(self):
        result = TranscriptionResult(text="")
        assert result.success is False

    def test_optional_fields(self):
        result = TranscriptionResult(text="hello", language="en", duration=1.5)
        assert result.language == "en"
        assert result.duration == 1.5


class TestIsAvailable:
    """Tests for is_available property."""

    def test_available_when_sounddevice_installed(self, voice_manager):
        with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
            assert voice_manager.is_available is True

    def test_unavailable_when_sounddevice_missing(self, voice_manager):
        with patch.dict("sys.modules", {"sounddevice": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                assert voice_manager.is_available is False


class TestStateCallbacks:
    """Tests for callback functionality."""

    def test_set_state_callback(self, voice_manager):
        callback = MagicMock()
        voice_manager.set_state_callback(callback)
        assert voice_manager._on_state_change is callback

    def test_set_transcription_callback(self, voice_manager):
        callback = MagicMock()
        voice_manager.set_transcription_callback(callback)
        assert voice_manager._on_transcription is callback

    def test_state_change_calls_callback(self, voice_manager):
        callback = MagicMock()
        voice_manager.set_state_callback(callback)
        voice_manager._set_state(RecordingState.RECORDING)
        callback.assert_called_once_with(RecordingState.RECORDING)

    def test_state_change_handles_callback_error(self, voice_manager):
        callback = MagicMock(side_effect=Exception("callback error"))
        voice_manager.set_state_callback(callback)
        # Should not raise
        voice_manager._set_state(RecordingState.RECORDING)
        assert voice_manager.state == RecordingState.RECORDING


class TestStartRecording:
    """Tests for start_recording method."""

    @pytest.mark.asyncio
    async def test_start_recording_success(self, voice_manager):
        mock_stream = MagicMock()
        mock_sounddevice = MagicMock()
        mock_sounddevice.InputStream.return_value = mock_stream

        voice_manager._sounddevice = mock_sounddevice

        result = await voice_manager.start_recording()

        assert result is True
        assert voice_manager.state == RecordingState.RECORDING
        assert voice_manager.is_recording is True
        mock_stream.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_recording_clears_buffer(self, voice_manager):
        voice_manager._audio_buffer = [b"old_data"]
        mock_sounddevice = MagicMock()
        mock_sounddevice.InputStream.return_value = MagicMock()
        voice_manager._sounddevice = mock_sounddevice

        await voice_manager.start_recording()

        assert voice_manager._audio_buffer == []

    @pytest.mark.asyncio
    async def test_start_recording_fails_when_already_recording(self, voice_manager):
        voice_manager._state = RecordingState.RECORDING

        result = await voice_manager.start_recording()

        assert result is False

    @pytest.mark.asyncio
    async def test_start_recording_fails_without_sounddevice(self, voice_manager):
        voice_manager._sounddevice = None
        with patch.object(voice_manager, "_ensure_sounddevice", return_value=False):
            result = await voice_manager.start_recording()

        assert result is False
        assert voice_manager.state == RecordingState.ERROR

    @pytest.mark.asyncio
    async def test_start_recording_handles_stream_error(self, voice_manager):
        mock_sounddevice = MagicMock()
        mock_sounddevice.InputStream.side_effect = Exception("audio error")
        voice_manager._sounddevice = mock_sounddevice

        result = await voice_manager.start_recording()

        assert result is False
        assert voice_manager.state == RecordingState.ERROR


class TestStopRecording:
    """Tests for stop_recording method."""

    @pytest.mark.asyncio
    async def test_stop_recording_not_recording(self, voice_manager):
        result = await voice_manager.stop_recording()

        assert result.success is False
        assert result.error == "Not recording"

    @pytest.mark.asyncio
    async def test_stop_recording_no_audio(self, voice_manager):
        voice_manager._state = RecordingState.RECORDING
        voice_manager._audio_buffer = []
        voice_manager._stream = MagicMock()

        result = await voice_manager.stop_recording()

        assert result.success is False
        assert result.error == "No audio recorded"
        assert voice_manager.state == RecordingState.IDLE

    @pytest.mark.asyncio
    async def test_stop_recording_closes_stream(self, voice_manager):
        mock_stream = MagicMock()
        voice_manager._state = RecordingState.RECORDING
        voice_manager._stream = mock_stream
        voice_manager._audio_buffer = [b"audio_data"]

        with patch.object(
            voice_manager, "_transcribe", new_callable=AsyncMock
        ) as mock_transcribe:
            mock_transcribe.return_value = TranscriptionResult(text="hello")
            await voice_manager.stop_recording()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert voice_manager._stream is None

    @pytest.mark.asyncio
    async def test_stop_recording_transcribes_audio(self, voice_manager):
        voice_manager._state = RecordingState.RECORDING
        voice_manager._stream = MagicMock()
        voice_manager._audio_buffer = [b"\x00\x00" * 100]

        with patch.object(
            voice_manager, "_transcribe", new_callable=AsyncMock
        ) as mock_transcribe:
            mock_transcribe.return_value = TranscriptionResult(text="hello world")
            result = await voice_manager.stop_recording()

        assert result.text == "hello world"
        assert result.success is True
        assert voice_manager.state == RecordingState.IDLE

    @pytest.mark.asyncio
    async def test_stop_recording_calls_transcription_callback(self, voice_manager):
        callback = MagicMock()
        voice_manager.set_transcription_callback(callback)
        voice_manager._state = RecordingState.RECORDING
        voice_manager._stream = MagicMock()
        voice_manager._audio_buffer = [b"\x00\x00" * 100]

        expected_result = TranscriptionResult(text="hello")
        with patch.object(
            voice_manager, "_transcribe", new_callable=AsyncMock
        ) as mock_transcribe:
            mock_transcribe.return_value = expected_result
            await voice_manager.stop_recording()

        callback.assert_called_once_with(expected_result)

    @pytest.mark.asyncio
    async def test_stop_recording_handles_transcription_error(self, voice_manager):
        voice_manager._state = RecordingState.RECORDING
        voice_manager._stream = MagicMock()
        voice_manager._audio_buffer = [b"\x00\x00"]

        with patch.object(
            voice_manager, "_create_wav", side_effect=Exception("wav error")
        ):
            result = await voice_manager.stop_recording()

        assert result.success is False
        assert "wav error" in result.error
        assert voice_manager.state == RecordingState.ERROR


class TestCancelRecording:
    """Tests for cancel_recording method."""

    def test_cancel_recording_stops_stream(self, voice_manager):
        mock_stream = MagicMock()
        voice_manager._stream = mock_stream

        voice_manager.cancel_recording()

        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    def test_cancel_recording_clears_buffer(self, voice_manager):
        voice_manager._audio_buffer = [b"data"]

        voice_manager.cancel_recording()

        assert voice_manager._audio_buffer == []

    def test_cancel_recording_sets_idle_state(self, voice_manager):
        voice_manager._state = RecordingState.RECORDING

        voice_manager.cancel_recording()

        assert voice_manager.state == RecordingState.IDLE

    def test_cancel_recording_handles_stream_error(self, voice_manager):
        mock_stream = MagicMock()
        mock_stream.stop.side_effect = Exception("stop error")
        voice_manager._stream = mock_stream

        # Should not raise
        voice_manager.cancel_recording()

        assert voice_manager._stream is None
        assert voice_manager.state == RecordingState.IDLE


class TestAudioCallback:
    """Tests for audio callback."""

    def test_audio_callback_appends_data(self, voice_manager):
        indata = b"\x00\x01\x02\x03"

        voice_manager._audio_callback(indata, 4, None, None)

        assert len(voice_manager._audio_buffer) == 1
        assert voice_manager._audio_buffer[0] == b"\x00\x01\x02\x03"

    def test_audio_callback_multiple_calls(self, voice_manager):
        voice_manager._audio_callback(b"chunk1", 6, None, None)
        voice_manager._audio_callback(b"chunk2", 6, None, None)

        assert len(voice_manager._audio_buffer) == 2


class TestCreateWav:
    """Tests for WAV file creation."""

    def test_create_wav_returns_bytes(self, voice_manager):
        audio_data = b"\x00\x00" * 1000

        wav_data = voice_manager._create_wav(audio_data)

        assert isinstance(wav_data, bytes)
        assert len(wav_data) > len(audio_data)  # WAV header adds size

    def test_create_wav_has_riff_header(self, voice_manager):
        audio_data = b"\x00\x00" * 100

        wav_data = voice_manager._create_wav(audio_data)

        assert wav_data[:4] == b"RIFF"
        assert wav_data[8:12] == b"WAVE"


class TestTranscribe:
    """Tests for transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_unsupported_provider(self, voice_manager, mock_settings):
        mock_settings.stt_provider = "unsupported"
        wav_data = b"fake_wav_data"

        result = await voice_manager._transcribe(wav_data)

        assert result.success is False
        assert "Unsupported STT provider" in result.error

    @pytest.mark.asyncio
    async def test_transcribe_openai_no_api_key(self, voice_manager):
        wav_data = b"fake_wav_data"

        with patch("config.Config.get", return_value=None):
            result = await voice_manager._transcribe_openai(wav_data)

        assert result.success is False
        assert "API key not configured" in result.error


class TestToggleRecording:
    """Tests for toggle_recording method."""

    @pytest.mark.asyncio
    async def test_toggle_starts_when_idle(self, voice_manager):
        mock_sounddevice = MagicMock()
        mock_sounddevice.InputStream.return_value = MagicMock()
        voice_manager._sounddevice = mock_sounddevice

        result = await voice_manager.toggle_recording()

        assert result is None
        assert voice_manager.is_recording is True

    @pytest.mark.asyncio
    async def test_toggle_stops_when_recording(self, voice_manager):
        voice_manager._state = RecordingState.RECORDING
        voice_manager._stream = MagicMock()
        voice_manager._audio_buffer = [b"\x00\x00"]

        with patch.object(
            voice_manager, "_transcribe", new_callable=AsyncMock
        ) as mock_transcribe:
            mock_transcribe.return_value = TranscriptionResult(text="hello")
            result = await voice_manager.toggle_recording()

        assert result is not None
        assert result.text == "hello"


class TestEnsureSounddevice:
    """Tests for _ensure_sounddevice method."""

    def test_ensure_sounddevice_already_loaded(self, voice_manager):
        voice_manager._sounddevice = MagicMock()

        result = voice_manager._ensure_sounddevice()

        assert result is True

    def test_ensure_sounddevice_import_success(self, voice_manager):
        with patch.dict("sys.modules", {"sounddevice": MagicMock()}):
            result = voice_manager._ensure_sounddevice()

        assert result is True
        assert voice_manager._sounddevice is not None

    def test_ensure_sounddevice_import_failure(self, voice_manager):
        voice_manager._sounddevice = None

        with patch("builtins.__import__", side_effect=ImportError("No sounddevice")):
            result = voice_manager._ensure_sounddevice()

        assert result is False
