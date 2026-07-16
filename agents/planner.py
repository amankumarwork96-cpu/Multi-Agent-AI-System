"""
Planner Agent
--------------
The first LLM-powered node in the workflow. Reads the user's business
question and the factual dataset profile, then asks Groq to produce a
structured analysis plan.

The LLM never sees anything except the profile we hand it — it cannot
invent columns because it has no other source of dataset information.
"""

import json
from groq import Groq
from config import GROQ_API_KEY
from prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from schemas.planner_schema import AnalysisPlan

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

def create_analysis_plan(user_question: str, dataset_profile: dict) -> AnalysisPlan:
    schema_hint = AnalysisPlan.model_json_schema()

    user_message = f"""
User's business question:
{user_question}

Dataset profile (the ONLY real columns and facts you may use):
{json.dumps(dataset_profile, indent=2)}

Return your analysis plan as JSON matching this exact schema:
{json.dumps(schema_hint, indent=2)}
"""
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format= {"type": "json_object"},
        temperature=0,
    )

    raw_content = response.choices[0].message.content

    try:
        parsed_json = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Planner returned invalid JSON, could not press: {e}\nRaw response: {raw_content}"
        ) from e
    

    try:
        plan = AnalysisPlan(**parsed_json)
    except Exception as e:
        raise ValueError(
            f"Planner's JSON did not match the AnalysisPlan schema: {e}\nParsed JSON: {parsed_json}"
        ) from e
    
    return plan