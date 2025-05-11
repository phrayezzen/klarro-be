import json
import os
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import openai
from asgiref.sync import sync_to_async
from django.conf import settings
from pydantic import BaseModel, Field

from ..models import Company, Flow, Recruiter, Step


class ToolName(Enum):
    REQUEST_MORE_DETAILS = "request_more_details"
    CREATE_FLOW = "create_flow"


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

{additional_context if additional_context else ''}

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
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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

    except Exception as e:
        return [
            "Could you provide more details about the role requirements?",
            "What are the key skills and qualifications needed?",
            "Are there any specific areas you want to focus on in the interview?",
        ]


async def handle_message(
    message: str,
    company: Company,
    recruiter: Recruiter,
) -> Tuple[Optional[str], Optional[Flow], Optional[FlowDetails]]:
    """Handle a general message and let GPT decide what to do."""
    try:
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Prepare the prompt
        prompt = f"""You are an AI assistant for a recruitment platform. The user has sent the following message:
        "{message}"

        Company: {company.name}
        Description: {company.description}

        If the user wants to create an interview flow (e.g., "create a flow", "create an interview flow", "make a flow"), you should:
        1. Use the {ToolName.CREATE_FLOW.value} tool if they specify a role (e.g., "create a flow for a Software Engineer")
        2. Use the {ToolName.REQUEST_MORE_DETAILS.value} tool if they don't specify a role (e.g., "create a flow for me")

        IMPORTANT: When using {ToolName.CREATE_FLOW.value}:
        - The role_name must be a specific job title (e.g., "Software Engineer", "Product Manager", "Data Scientist")
        - DO NOT use the company name as the role_name
        - If no specific role is mentioned, use {ToolName.REQUEST_MORE_DETAILS.value} instead

        For any other messages, provide a helpful response about recruitment and interview processes.

        Remember:
        - Always use the {ToolName.CREATE_FLOW.value} tool when a role is mentioned
        - Always use the {ToolName.REQUEST_MORE_DETAILS.value} tool when a role is not specified
        - Never provide a generic response for flow creation requests"""

        # Get completion from OpenAI
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant for a recruitment platform. You can help create interview flows and answer questions about the recruitment process. You must use the appropriate tools for flow creation requests.",
                },
                {"role": "user", "content": prompt},
            ],
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1000,
        )

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
                    return message.content, flow, details
                elif function_name == ToolName.REQUEST_MORE_DETAILS.value:
                    details = FlowDetails(
                        context=function_args["context"],
                        questions=function_args["questions"],
                    )
                    return message.content, None, details

            except Exception as e:
                raise

        return message.content, None, None

    except Exception as e:
        return f"Error processing message: {str(e)}", None, None
