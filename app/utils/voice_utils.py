"""Voice helpers that work on cloud deployments.

Speech-to-text takes audio recorded *in the browser* (st.audio_input) as WAV bytes,
so no server-side microphone is needed. Both directions still call Google services
(speech recognition API / gTTS), so they need internet access.
"""
import io

from app.errors import VoiceError

MAX_TTS_CHARS = 1500


def transcribe_audio_bytes(wav_bytes: bytes, language="en-US") -> str:
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise VoiceError("SpeechRecognition is not installed.") from exc

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError as exc:
        raise VoiceError("Could not understand the audio. Please try again.") from exc
    except sr.RequestError as exc:
        raise VoiceError("Speech recognition service is unavailable (check your internet).") from exc
    except Exception as exc:
        raise VoiceError(f"Could not read the recording: {exc}") from exc


def text_to_speech_bytes(text: str) -> bytes:
    text = (text or "").strip()
    if not text:
        raise VoiceError("There is no text to read aloud.")
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise VoiceError("gTTS is not installed.") from exc
    try:
        buf = io.BytesIO()
        gTTS(text[:MAX_TTS_CHARS]).write_to_fp(buf)
        return buf.getvalue()
    except Exception as exc:
        raise VoiceError(f"Text-to-speech failed (check your internet): {exc}") from exc
