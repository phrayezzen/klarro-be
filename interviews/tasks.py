import json

import openai
from celery import shared_task


@shared_task
def evaluate_resume_task(candidate_id):
    from .models import Candidate

    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return "Candidate not found"

    # Prepare the prompt for GPT-4
    prompt = f"""
    Evaluate the following candidate's resume for the role of {candidate.flow.role_name}:
    
    Name: {candidate.first_name} {candidate.last_name}
    Email: {candidate.email}
    Role: {candidate.flow.role_name}
    Role Description: {candidate.flow.role_description}
    
    Please provide a detailed evaluation in the following JSON format:
    {{
        "education": {{
            "score": <score from 0-100>,
            "evaluation": "<detailed evaluation>"
        }},
        "experience": {{
            "score": <score from 0-100>,
            "evaluation": "<detailed evaluation>"
        }}
    }}
    """

    try:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )

        # Parse the response
        evaluation = json.loads(response.choices[0].message.content)

        # Update candidate scores
        candidate.education_score = evaluation["education"]["score"]
        candidate.experience_score = evaluation["experience"]["score"]
        candidate.save()

        return "Resume evaluation completed"

    except Exception as e:
        return f"Error in evaluate_resume_task: {str(e)}"


@shared_task
def evaluate_interview_task(interview_id):
    from .models import Interview

    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return "Interview not found"

    # Determine if this is a technical or behavioral interview
    is_technical = interview.step.step_type == "technical"
    is_behavioral = interview.step.step_type == "behavioral"

    # Prepare the prompt for GPT-4
    prompt = f"""
    Evaluate the following interview transcript for the role of {interview.candidate.flow.role_name}:
    
    Candidate: {interview.candidate.first_name} {interview.candidate.last_name}
    Role: {interview.candidate.flow.role_name}
    Role Description: {interview.candidate.flow.role_description}
    Interview Type: {interview.step.step_type}
    Transcript: {interview.transcript}
    
    Please provide a detailed evaluation in the following JSON format:
    {{
        "overall_score": <score from 0-100>,
        "education": {{
            "score": <score from 0-100>,
            "evaluation": "<detailed evaluation>"
        }},
        "experience": {{
            "score": <score from 0-100>,
            "evaluation": "<detailed evaluation>"
        }},
        {f'"technical": {{"score": <score from 0-100>, "evaluation": "<detailed evaluation>"}},' if is_technical else ""}
        {f'"behavioral": {{"score": <score from 0-100>, "evaluation": "<detailed evaluation>"}},' if is_behavioral else ""}
        "cheating_flag": <true/false>
    }}
    """

    try:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )

        # Parse the response
        evaluation = json.loads(response.choices[0].message.content)

        # Update interview scores
        interview.overall_score = evaluation["overall_score"]
        if "technical" in evaluation:
            interview.technical_score = evaluation["technical"]["score"]
        if "behavioral" in evaluation:
            interview.behavioral_score = evaluation["behavioral"]["score"]
        interview.cheating_flag = evaluation["cheating_flag"]
        interview.save()

        return "Interview evaluation completed"

    except Exception as e:
        return f"Error in evaluate_interview_task: {str(e)}"
