import base64
import logging
from typing import Tuple

import openai
from django.conf import settings

logger = logging.getLogger(__name__)


def text_to_speech(text: str) -> Tuple[str, str]:
    """
    Convert text to speech using OpenAI's TTS API.
    Returns a tuple of (audio_format, audio_base64_string)
    """
    try:
        if not text:
            raise ValueError("Text cannot be empty")

        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not configured")

        response = openai.audio.speech.create(
            model="tts-1",
            voice="alloy",  # You can choose from: alloy, echo, fable, onyx, nova, shimmer
            input=text,
        )

        # Get the audio data
        audio_data = response.content

        # Convert to base64 for easy transmission
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        return "audio/mpeg", audio_base64
    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        raise Exception(f"Failed to convert text to speech: {str(e)}")
