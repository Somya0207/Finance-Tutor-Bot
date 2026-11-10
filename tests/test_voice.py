import unittest
from unittest.mock import patch

from app.errors import VoiceError
from app.utils import voice_utils


class VoiceTests(unittest.TestCase):
    def test_tts_rejects_empty_text(self):
        for bad in ["", "   ", None]:
            with self.assertRaises(VoiceError):
                voice_utils.text_to_speech_bytes(bad)

    def test_missing_libraries_give_friendly_error(self):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **k):
            if name in ("speech_recognition", "gtts"):
                raise ImportError(name)
            return real_import(name, *a, **k)

        with patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(VoiceError):
                voice_utils.transcribe_audio_bytes(b"x")
            with self.assertRaises(VoiceError):
                voice_utils.text_to_speech_bytes("hello")


if __name__ == "__main__":
    unittest.main()
