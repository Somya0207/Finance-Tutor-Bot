import speech_recognition as sr
from gtts import gTTS
import tempfile

# -------------------------
# SPEECH TO TEXT
# -------------------------
def speech_to_text():

    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source)

        text = recognizer.recognize_google(audio)
        return text

    except sr.UnknownValueError:
        return "❌ Could not understand audio"

    except sr.RequestError:
        return "❌ Speech service unavailable"


# -------------------------
# TEXT TO SPEECH
# -------------------------
def text_to_speech(text):

    tts = gTTS(text)

    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_audio.name)

    return temp_audio.name