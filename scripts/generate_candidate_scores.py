import os
import random
from datetime import datetime

import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_interview_backend.settings")
django.setup()

from interviews.models import Candidate


def generate_evaluation(score, category):
    """Generate a realistic evaluation based on the score and category."""
    if score >= 90:
        return f"Exceptional {category.lower()} demonstrated. Shows outstanding capabilities and deep understanding."
    elif score >= 80:
        return f"Strong {category.lower()} with notable achievements. Shows good potential for growth."
    elif score >= 70:
        return f"Solid {category.lower()} with room for improvement. Shows basic competence."
    elif score >= 60:
        return f"Developing {category.lower()}. Needs more experience and training."
    else:
        return f"Limited {category.lower()}. Significant improvement needed."


def generate_scores_and_evaluations():
    """Generate random scores and evaluations for all candidates."""
    candidates = Candidate.objects.all()

    for candidate in candidates:
        # Generate random scores between 20 and 100 for individual categories
        individual_scores = {
            "experience_score": random.randint(20, 100),
            "education_score": random.randint(20, 100),
            "behavioral_score": random.randint(20, 100),
            "technical_score": random.randint(20, 100),
            "preferences_score": random.randint(20, 100),
        }

        # Calculate job match score as average of other scores
        job_match_score = round(
            sum(individual_scores.values()) / len(individual_scores)
        )

        # Combine all scores
        scores = {"job_match_score": job_match_score, **individual_scores}

        # Generate evaluations based on scores
        evaluations = {
            "experience_evaluation": generate_evaluation(
                scores["experience_score"], "Experience"
            ),
            "education_evaluation": generate_evaluation(
                scores["education_score"], "Education"
            ),
            "behavioral_evaluation": generate_evaluation(
                scores["behavioral_score"], "Behavioral"
            ),
            "technical_evaluation": generate_evaluation(
                scores["technical_score"], "Technical"
            ),
            "preferences_evaluation": generate_evaluation(
                scores["preferences_score"], "Preferences"
            ),
        }

        # Update candidate with new scores and evaluations
        for field, value in {**scores, **evaluations}.items():
            setattr(candidate, field, value)

        candidate.save()
        print(
            f"Updated scores and evaluations for {candidate.first_name} {candidate.last_name}"
        )


if __name__ == "__main__":
    print("Starting to generate random scores and evaluations...")
    generate_scores_and_evaluations()
    print("Finished generating scores and evaluations!")
