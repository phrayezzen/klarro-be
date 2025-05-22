import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import Q
from openai import AsyncOpenAI, OpenAI

from ..models import Flow, Step
from .tts_service import text_to_speech

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

logger = logging.getLogger(__name__)


def get_current_step(flow: Flow, conversation_history: List[Dict]) -> Optional[Step]:
    """Get the current step based on conversation history."""
    if not conversation_history:
        return flow.steps.first()

    # Get the last assistant message
    last_assistant_msg = next(
        (msg for msg in reversed(conversation_history) if msg["role"] == "assistant"),
        None,
    )

    if not last_assistant_msg:
        return flow.steps.first()

    # Find the step that matches the last assistant message
    return flow.steps.filter(
        Q(name__icontains=last_assistant_msg["content"])
        | Q(description__icontains=last_assistant_msg["content"])
    ).first()


async def generate_interview_response(
    user_message: str, flow: Flow, conversation_history: List[Dict]
) -> Dict[str, Any]:
    """Generate an interview response using OpenAI."""
    try:
        # Get current step
        current_step = get_current_step(flow, conversation_history)

        # Prepare system message
        system_message = {
            "role": "system",
            "content": f"""You are an AI interviewer for the role of {flow.role_name} at {flow.company.name}.
            Your goal is to assess the candidate's qualifications and fit for this position.
            Current step: {current_step.name if current_step else "Introduction"}
            Step description: {current_step.description if current_step else "Begin the interview"}
            Role description: {flow.role_description}
            Company: {flow.company.name}
            Location: {flow.location if flow.location else "Remote"}
            Remote allowed: {"Yes" if flow.is_remote_allowed else "No"}""",
        }

        # Prepare conversation history
        messages = [system_message]
        messages.extend(
            [
                {"role": msg["role"], "content": msg["content"]}
                for msg in conversation_history
            ]
        )

        # Add user message
        messages.append({"role": "user", "content": user_message})

        # Call OpenAI API
        try:
            response = await client.chat.completions.create(
                model="gpt-4",
                temperature=0.7,
                max_tokens=500,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as api_error:
            logger.error(f"OpenAI API Error: {str(api_error)}")
            raise

        # Get response text
        response_text = response.choices[0].message.content

        # Convert to speech
        audio_format, audio_base64 = text_to_speech(response_text)

        return {
            "text": response_text,
            "audio": {"format": audio_format, "data": audio_base64},
        }

    except Exception as e:
        raise Exception(f"Error generating interview response: {str(e)}")


async def get_ai_response(messages: List[Dict[str, Any]]) -> str:
    """Get response from OpenAI API."""
    client = AsyncOpenAI()
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            temperature=0.7,
            max_tokens=500,
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as api_error:
        logger.error(f"OpenAI API Error: {str(api_error)}")
        raise
