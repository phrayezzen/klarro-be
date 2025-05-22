import json
from enum import Enum
from typing import Dict, List, Optional, Tuple

import openai
from asgiref.sync import sync_to_async
from django.conf import settings
from pydantic import BaseModel, Field

from ..models import Candidate, Company, Flow, Recruiter, Step


class ToolName(Enum):
    REQUEST_MORE_DETAILS = "request_more_details"
    CREATE_FLOW = "create_flow"
    RECOMMEND_CANDIDATES = "recommend_candidates"
    SUMMARIZE_CANDIDATE = "summarize_candidate"


class InterviewStep(BaseModel):
    name: str = Field(..., description="Name of the interview step")
    description: str = Field(
        ..., description="Detailed description of what happens in this step"
    )
    step_type: str = Field(
        ..., description="Type of interview (technical, behavioral, project)"
    )
    duration_minutes: int = Field(
        ..., ge=1, le=480, description="Duration of the step in minutes"
    )
    order: int = Field(..., description="Order of the step in the interview flow")
    interviewer_tone: str = Field(
        default="professional",
        description="Tone of the interviewer (friendly, professional, challenging, casual)",
    )
    assessed_skills: List[str] = Field(
        default_factory=list, description="List of skills to assess"
    )
    custom_questions: List[str] = Field(
        default_factory=list, description="List of custom questions"
    )


class InterviewFlow(BaseModel):
    role_name: str = Field(..., description="Name of the role being interviewed for")
    role_function: str = Field(
        ...,
        description="Function/department of the role (must be one of: business_ops, sales_cs, marketing_growth, product_design, engineering_data, people_hr, finance_legal, support_services, science_research, executive_leadership)",
    )
    role_description: str = Field(..., description="Detailed description of the role")
    location: str = Field(None, description="Location of the role")
    is_remote_allowed: bool = Field(
        default=False, description="Whether remote work is allowed"
    )
    steps: List[InterviewStep] = Field(..., description="List of interview steps")


class FlowDetails(BaseModel):
    context: str = Field(..., description="Context for why more details are needed")
    questions: List[str] = Field(..., description="List of questions to ask the user")


class CandidateRecommendation(BaseModel):
    candidate_id: int = Field(..., description="ID of the candidate")
    first_name: str = Field(..., description="First name of the candidate")
    last_name: str = Field(..., description="Last name of the candidate")
    email: str = Field(..., description="Email of the candidate")
    overall_score: float = Field(..., description="Overall match score for the role")
    strengths: List[str] = Field(..., description="List of candidate's key strengths")
    areas_for_improvement: List[str] = Field(
        ..., description="List of areas where the candidate could improve"
    )
    recommendation_reason: str = Field(
        ..., description="Detailed explanation of why this candidate is recommended"
    )


class CandidateData(BaseModel):
    id: int = Field(..., description="ID of the candidate")
    name: str = Field(..., description="Full name of the candidate")
    email: str = Field(..., description="Email of the candidate")
    scores: Dict[str, float] = Field(
        ...,
        description="Dictionary of scores for different aspects",
        example={
            "job_match": 0.85,
            "experience": 0.90,
            "education": 0.95,
            "behavioral": 0.88,
            "technical": 0.92,
            "preferences": 0.87,
        },
    )
    evaluations: Dict[str, str] = Field(
        ...,
        description="Dictionary of evaluations for different aspects",
        example={
            "experience": "Strong background in leadership roles",
            "education": "MBA from top university",
            "behavioral": "Excellent communication skills",
            "technical": "Strong strategic thinking",
            "preferences": "Prefers hybrid work model",
        },
    )


# Tools that GPT can use
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": ToolName.REQUEST_MORE_DETAILS.value,
            "description": "Request more details from the user about the role or interview process",
            "parameters": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specific questions to ask the user",
                    },
                    "context": {
                        "type": "string",
                        "description": "Context for why these details are needed",
                    },
                },
                "required": ["questions", "context"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.CREATE_FLOW.value,
            "description": "Create an interview flow for a specific role",
            "parameters": {
                "type": "object",
                "properties": {
                    "role_name": {
                        "type": "string",
                        "description": "Name of the role to create a flow for",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the role and requirements",
                    },
                },
                "required": ["role_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.RECOMMEND_CANDIDATES.value,
            "description": "Get AI-powered recommendations for top candidates in a flow",
            "parameters": {
                "type": "object",
                "properties": {
                    "role_name": {
                        "type": "string",
                        "description": "Name of the role/flow to get recommendations for",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top candidates to recommend (default: 3)",
                    },
                },
                "required": ["role_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ToolName.SUMMARIZE_CANDIDATE.value,
            "description": "Generate a comprehensive summary of a candidate's profile and qualifications",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_id": {
                        "type": "integer",
                        "description": "ID of the candidate to summarize",
                    },
                },
                "required": ["candidate_id"],
            },
        },
    },
]


def create_flow_prompt(role_name: str, additional_context: str = None) -> str:
    """Create a prompt for generating an interview flow."""
    role_functions = [
        "business_ops - Business & Operations roles like Business Analyst, Operations Manager",
        "sales_cs - Sales & Customer Success roles like Sales Representative, Customer Success Manager",
        "marketing_growth - Marketing & Growth roles like Marketing Manager, Growth Hacker",
        "product_design - Product & Design roles like Product Manager, UX Designer",
        "engineering_data - Engineering & Data roles like Software Engineer, Data Scientist",
        "people_hr - People & HR roles like HR Manager, Recruiter",
        "finance_legal - Finance & Legal roles like Financial Analyst, Legal Counsel",
        "support_services - Support & Services roles like Customer Support, IT Support",
        "science_research - Science & Research roles like Research Scientist, Lab Technician",
        "executive_leadership - Executive & Leadership roles like CEO, Director",
    ]

    # Get the JSON schema from our Pydantic models
    flow_schema = InterviewFlow.model_json_schema()

    prompt = f"""Create an interview flow for the role: {role_name}

First, determine the most appropriate role function from these options:
{chr(10).join(role_functions)}

Then, create a comprehensive interview flow with the following structure:
1. Each step should be a separate interview stage
2. For each step, include:
   - Name of the step
   - Description of what will be assessed
   - Type of step (technical, behavioral, or project)
   - Duration in minutes (between 1 and 480)
   - Order in the process
   - Interviewer tone (friendly, professional, challenging, or casual)
   - List of skills to assess
   - List of custom questions

The flow should be comprehensive and cover all aspects of the role.

{additional_context if additional_context else ""}

Important constraints:
- Step durations must be between 1 and 480 minutes
- Step types must be: technical, behavioral, or project
- Interviewer tones must be: friendly, professional, challenging, or casual
- Role function must match one of the provided options exactly
- Each step must have a unique order number
- Each step must have at least one skill to assess
- Each step must have at least one custom question

IMPORTANT: Your response must be a valid JSON object that matches this schema:
{json.dumps(flow_schema, indent=2)}

CRITICAL: 
- Return ONLY the raw JSON object
- Do NOT include any markdown formatting (no ```json or ```)
- Do NOT include any text before or after the JSON
- The response must be parseable by json.loads()"""
    return prompt


def get_flow_details_prompt(role_name: str) -> str:
    """Create a prompt for getting more details about a role."""
    return f"""You are an expert recruiter. What additional information would you need to create a comprehensive interview flow for a {role_name} position?

Please ask 3-5 specific questions about:
1. Required skills and experience
2. Team structure and reporting
3. Project scope and responsibilities
4. Company culture and values
5. Technical requirements

Use the available tools to understand typical requirements for this role.
If you need more specific information, use the request_more_details tool."""


async def generate_flow(
    role_name: str,
    company: Company,
    recruiter: Recruiter,
    additional_context: Optional[str] = None,
) -> Tuple[Optional[Flow], Optional[FlowDetails]]:
    """Generate an interview flow for a role."""
    try:
        # Clean the API key
        cleaned_key = (
            settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else None
        )

        # Initialize OpenAI client with cleaned key
        client = openai.AsyncOpenAI(api_key=cleaned_key)

        # Test the API key with a simple request
        try:
            test_response = await client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
        except Exception:
            raise

        # Prepare the prompt
        prompt = create_flow_prompt(role_name, additional_context)

        # Get completion from OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at creating interview flows. Return ONLY a valid JSON object that matches the schema. Do not include any markdown formatting or additional text.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        # Parse the response
        message = response.choices[0].message

        # Handle tool calls (e.g., request_more_details)
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                function = getattr(tool_call, "function", None)
                if (
                    function
                    and getattr(function, "name", None) == "request_more_details"
                ):
                    args = json.loads(function.arguments)
                    return None, FlowDetails(
                        context=args["context"], questions=args["questions"]
                    )

        try:
            # Parse the response into an InterviewFlow object
            flow_data = json.loads(message.content)
            flow_model = InterviewFlow(**flow_data)

            # Create the flow with the determined role function
            flow = await sync_to_async(Flow.objects.create)(
                role_name=flow_model.role_name,
                company=company,
                recruiter=recruiter,
                role_description=flow_model.role_description,
                role_function=flow_model.role_function,
                location=flow_model.location,
                is_remote_allowed=flow_model.is_remote_allowed,
            )

            # Create all steps
            for step_data in flow_model.steps:
                await sync_to_async(Step.objects.create)(
                    flow=flow,
                    name=step_data.name,
                    description=step_data.description,
                    step_type=step_data.step_type,
                    duration_minutes=step_data.duration_minutes,
                    order=step_data.order,
                    interviewer_tone=step_data.interviewer_tone,
                    assessed_skills=step_data.assessed_skills,
                    custom_questions=step_data.custom_questions,
                )

            return flow, None

        except json.JSONDecodeError as e:
            return None, FlowDetails(
                context="I had trouble creating the flow. Let me try again with a different format.",
                questions=[
                    "Would you like me to try creating the flow again?",
                    "Or would you prefer to provide more details about the role first?",
                ],
            )
        except Exception as e:
            # If flow creation fails, clean up and return None
            if "flow" in locals():
                await sync_to_async(flow.delete)()
            return None, FlowDetails(
                context=f"I encountered an error while creating the flow: {str(e)}",
                questions=[
                    "Would you like me to try creating the flow again?",
                    "Or would you prefer to provide more details about the role first?",
                ],
            )

    except Exception as e:
        return None, FlowDetails(
            context=f"I encountered an error while creating the flow: {str(e)}",
            questions=[
                "Would you like me to try creating the flow again?",
                "Or would you prefer to provide more details about the role first?",
            ],
        )


async def get_flow_details(role_name: str) -> List[str]:
    """Get additional details needed for flow creation."""
    try:
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Prepare the prompt
        prompt = f"""What additional details do you need to create a comprehensive interview flow for a {role_name} position?"""

        # Get completion from OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at creating interview flows.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        # Parse the response into questions
        questions = response.choices[0].message.content.split("\n")
        return [q.strip() for q in questions if q.strip()]

    except Exception:
        return [
            "Could you provide more details about the role requirements?",
            "What are the key skills and qualifications needed?",
            "Are there any specific areas you want to focus on in the interview?",
        ]


async def summarize_candidate(candidate_id: int, company: Company) -> Tuple[str, str]:
    """Generate a comprehensive summary of a candidate's profile."""
    try:
        # Get the candidate using sync_to_async
        candidate = await sync_to_async(Candidate.objects.select_related("flow").get)(
            id=candidate_id, flow__company=company
        )

        # Initialize OpenAI client
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Create prompt for GPT
        prompt = f"""Generate a comprehensive summary of this candidate's profile:

Candidate Information:
- Name: {candidate.first_name} {candidate.last_name}
- Email: {candidate.email}
- Role: {candidate.flow.role_name}
- Status: {candidate.status}

Scores:
- Job Match: {candidate.job_match_score}
- Experience: {candidate.experience_score}
- Education: {candidate.education_score}
- Behavioral: {candidate.behavioral_score}
- Technical: {candidate.technical_score}
- Preferences: {candidate.preferences_score}

Evaluations:
- Experience: {candidate.experience_evaluation}
- Education: {candidate.education_evaluation}
- Behavioral: {candidate.behavioral_evaluation}
- Technical: {candidate.technical_evaluation}
- Preferences: {candidate.preferences_evaluation}

Please provide a concise but comprehensive summary that includes:
1. Overall assessment of the candidate's fit for the role
2. Key strengths and areas for improvement
3. Notable achievements or qualifications
4. Recommendations for next steps in the interview process

Format the response in a clear, professional manner suitable for a recruiter."""

        # Get completion from OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert recruiter. Provide clear, professional summaries of candidate profiles.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        summary = response.choices[0].message.content
        redirect_url = f"/candidates/{candidate_id}"
        return summary, redirect_url

    except Candidate.DoesNotExist:
        return "Candidate not found.", None
    except Exception as e:
        return f"Error generating summary: {str(e)}", None


async def handle_message(
    message: str,
    company: Company,
    recruiter: Recruiter,
) -> Tuple[Optional[str], Optional[Flow], Optional[FlowDetails], Optional[str]]:
    """Handle a general message and let GPT decide what to do."""
    try:
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Prepare the prompt
        prompt = f"""You are an AI assistant for a recruitment platform. The user has sent the following message:
        "{message}"

        Company: {company.name}
        Description: {company.description}

        You can help with the following tasks:
        1. Get candidate recommendations (e.g., "recommend candidates", "who are the top candidates", "show me the best candidates", "what are the best candidates for flow X")
        2. Create interview flows (e.g., "create a flow", "create an interview flow", "make a flow")
        3. Generate candidate summaries (e.g., "summarize candidate", "give me a summary of candidate", "tell me about candidate")"""

        # Define system message
        system_message = {
            "role": "system",
            "content": """You are Taylor, a member of the recruiting team. You have a friendly and professional demeanor, with a focus on building relationships and finding the best talent. You're knowledgeable about recruitment processes and always maintain a positive, encouraging tone while being thorough in your assessments. You can help create interview flows, provide candidate recommendations, and generate candidate summaries. You must use the appropriate tools for each request.""",
        }

        # Get completion from OpenAI
        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[system_message, {"role": "user", "content": prompt}],
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000,
            )
        except Exception:
            raise

        # Parse the response
        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            try:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                if function_name == ToolName.CREATE_FLOW.value:
                    flow, details = await generate_flow(
                        role_name=function_args["role_name"],
                        company=company,
                        recruiter=recruiter,
                        additional_context=function_args.get("context"),
                    )
                    return message.content, flow, details, None
                elif function_name == ToolName.REQUEST_MORE_DETAILS.value:
                    details = FlowDetails(
                        context=function_args["context"],
                        questions=function_args["questions"],
                    )
                    return message.content, None, details, None
                elif function_name == ToolName.RECOMMEND_CANDIDATES.value:
                    role_name = function_args["role_name"]
                    top_n = function_args.get("top_n", 3)

                    # Get the flow by role name
                    try:
                        flow = await sync_to_async(Flow.objects.get)(
                            role_name=role_name, company=company
                        )

                        # Get recommendations
                        recommendations = await recommend_candidates(flow, top_n)

                        # Format recommendations as a response
                        if not recommendations:
                            return (
                                f"No candidates found for the {role_name} role.",
                                None,
                                None,
                                None,
                            )

                        # Create a response that includes both the recommendations and navigation data
                        response_text = f"Here are the top {len(recommendations)} candidates for {role_name}:\n\n"
                        for i, rec in enumerate(recommendations, 1):
                            response_text += f"{i}. {rec.first_name} {rec.last_name} (ID: {rec.candidate_id}, Score: {rec.overall_score})\n"
                            response_text += (
                                f"   Strengths: {', '.join(rec.strengths)}\n"
                            )
                            response_text += f"   Areas for improvement: {', '.join(rec.areas_for_improvement)}\n"
                            response_text += f"   {rec.recommendation_reason}\n\n"

                        # Return response with redirect_to using flowId
                        return (
                            response_text,
                            None,
                            None,
                            f"/candidates?flowId={flow.id}",
                        )
                    except Flow.DoesNotExist:
                        return (
                            f"I couldn't find an interview flow for the {role_name} role. Would you like me to create one?",
                            None,
                            None,
                            None,
                        )
                elif function_name == ToolName.SUMMARIZE_CANDIDATE.value:
                    candidate_id = function_args["candidate_id"]
                    summary, redirect_url = await summarize_candidate(
                        candidate_id, company
                    )
                    return summary, None, None, redirect_url

            except Exception:
                raise

        return message.content, None, None, None

    except Exception as e:
        return f"Error processing message: {str(e)}", None, None, None


async def recommend_candidates(
    flow: Flow, top_n: int = 5
) -> List[CandidateRecommendation]:
    """Recommend top candidates for a specific flow based on their scores and evaluations."""
    try:
        # Get all candidates for this flow
        candidates = await sync_to_async(list)(flow.candidates.all())

        if not candidates:
            return []

        # Initialize OpenAI client
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Prepare candidate data for analysis using Pydantic model
        candidate_data = []
        for candidate in candidates:
            candidate_data.append(
                CandidateData(
                    id=candidate.id,
                    name=f"{candidate.first_name} {candidate.last_name}",
                    email=candidate.email,
                    scores={
                        "job_match": candidate.job_match_score,
                        "experience": candidate.experience_score,
                        "education": candidate.education_score,
                        "behavioral": candidate.behavioral_score,
                        "technical": candidate.technical_score,
                        "preferences": candidate.preferences_score,
                    },
                    evaluations={
                        "experience": candidate.experience_evaluation,
                        "education": candidate.education_evaluation,
                        "behavioral": candidate.behavioral_evaluation,
                        "technical": candidate.technical_evaluation,
                        "preferences": candidate.preferences_evaluation,
                    },
                ).model_dump()
            )

        # Create prompt for GPT
        prompt = f"""Analyze these candidates for the role of {flow.role_name} ({flow.role_function}).

Role Description:
{flow.role_description}

Candidate Data:
{json.dumps(candidate_data, indent=2)}

Please analyze each candidate and provide:
1. An overall match score (0-100)
2. Key strengths that make them a good fit
3. Areas where they could improve
4. A detailed explanation of why they are recommended (or not)

Return the top {top_n} candidates in order of best match.

IMPORTANT: Return ONLY a JSON array of candidate recommendations with this structure:
[
    {{
        "candidate_id": <id>,
        "first_name": "<first_name>",
        "last_name": "<last_name>",
        "email": "<email>",
        "overall_score": <score>,
        "strengths": ["strength1", "strength2", ...],
        "areas_for_improvement": ["area1", "area2", ...],
        "recommendation_reason": "<detailed explanation>"
    }},
    ...
]"""

        # Get completion from OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert recruiter. Analyze candidates and provide detailed recommendations based on their scores and evaluations. Return ONLY a valid JSON array of recommendations.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        # Parse the response
        message = response.choices[0].message

        try:
            # Clean up the response content by removing markdown code block markers
            content = message.content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove ```
            content = content.strip()

            recommendations = json.loads(content)

            # Convert to CandidateRecommendation objects
            return [CandidateRecommendation(**rec) for rec in recommendations]
        except json.JSONDecodeError:
            return []

    except Exception:
        return []
