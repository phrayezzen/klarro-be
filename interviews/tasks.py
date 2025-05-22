from celery import shared_task
from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from .models import Candidate, Interview
from .services.ai_service import summarize_candidate


@shared_task
def evaluate_resume_task(candidate_id: int):
    """Evaluate a candidate's resume for education and experience scores."""
    try:
        # Get the candidate
        candidate = Candidate.objects.get(id=candidate_id)

        # Initialize OpenAI client
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Prepare the evaluation prompt
        prompt = f"""Please evaluate this resume for the role of {candidate.flow.role_name}:

Role Description:
{candidate.flow.role_description}

Please analyze the resume and provide:
1. Education score (0-100)
2. Experience score (0-100)
3. Detailed evaluation for each category

Format the response as a JSON object with the following structure:
{{
    "education": {{
        "score": float,
        "evaluation": string
    }},
    "experience": {{
        "score": float,
        "evaluation": string
    }}
}}"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume evaluator and recruiter.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        # Parse the response
        evaluation = response.choices[0].message.content
        import json

        evaluation_data = json.loads(evaluation)

        # Update the candidate with evaluation results
        candidate.education_score = evaluation_data["education"]["score"]
        candidate.experience_score = evaluation_data["experience"]["score"]
        candidate.education_evaluation = evaluation_data["education"]["evaluation"]
        candidate.experience_evaluation = evaluation_data["experience"]["evaluation"]
        candidate.save()

        return {
            "status": "success",
            "candidate_id": candidate_id,
            "education_score": evaluation_data["education"]["score"],
            "experience_score": evaluation_data["experience"]["score"],
        }

    except Exception as e:
        print(f"Error in evaluate_resume_task: {str(e)}")
        raise


@shared_task
def evaluate_interview_task(interview_id: int):
    """Evaluate an interview asynchronously."""
    try:
        # Get the interview
        interview = Interview.objects.get(id=interview_id)

        # Initialize OpenAI client
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Determine if this is a technical or behavioral interview
        is_technical = "technical" in interview.flow.role_function.lower()
        is_behavioral = "behavioral" in interview.flow.role_function.lower()

        if not (is_technical or is_behavioral):
            raise ValueError("Interview must be either technical or behavioral")

        # Prepare the evaluation prompt
        prompt = f"""Please evaluate this interview transcript for the role of {interview.flow.role_name}:

Transcript:
{interview.transcript}

Please provide:
1. Overall score (0-100)
2. Key strengths
3. Areas for improvement
4. Specific examples from the transcript
5. Cheating detection (true/false)
6. Detailed evaluation for {"technical" if is_technical else "behavioral"} aspects

Format the response as a JSON object with the following structure:
{{
    "overall_score": float,
    "cheating_flag": boolean,
    "strengths": [string],
    "improvements": [string],
    "examples": [string],
    "evaluation": {{
        "score": float,
        "evaluation": string
    }}
}}"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert interviewer and evaluator.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        # Parse the response
        evaluation = response.choices[0].message.content
        import json

        evaluation_data = json.loads(evaluation)

        # Update the interview with evaluation results
        interview.overall_score = evaluation_data["overall_score"]
        interview.cheating_flag = evaluation_data["cheating_flag"]
        interview.save()

        # Update the candidate with only the relevant score
        candidate = interview.flow.candidate
        candidate.job_match_score = evaluation_data["overall_score"]

        if is_technical:
            candidate.technical_score = evaluation_data["evaluation"]["score"]
            candidate.technical_evaluation = evaluation_data["evaluation"]["evaluation"]
        elif is_behavioral:
            candidate.behavioral_score = evaluation_data["evaluation"]["score"]
            candidate.behavioral_evaluation = evaluation_data["evaluation"][
                "evaluation"
            ]

        candidate.save()

    except Exception as e:
        print(f"Error in evaluate_interview_task: {str(e)}")
        raise
