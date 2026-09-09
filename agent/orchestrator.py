import os
import json
from pydantic import BaseModel, Field, ValidationError
from typing import List
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cast-506804")
PARALLEL_API_KEY = os.getenv("PARALLEL_API_KEY")

DELTA_THRESHOLD = 15
CRISIS_FLOOR = 25

# Pydantic schema for structured output
class ReportSchema(BaseModel):
    sentiment_score: int = Field(description="Overall sentiment score 0-100")
    critic_sentiment_score: int = Field(description="Critic sentiment score 0-100")
    audience_sentiment_score: int = Field(description="Audience sentiment score 0-100")
    key_narratives: List[str] = Field(description="2-4 storylines that matter")
    controversies_detected: List[str] = Field(description="Any controversies found")
    confidence: str = Field(description="'high', 'medium', or 'low'")
    summary: str = Field(description="Narrative summary")
    recommended_pivot: str = Field(description="Actionable PR pivot recommendation")
    sources: List[str] = Field(description="Sources cited")

SYSTEM_PROMPT = """You are a PR & Release Strategy Analyst for a film studio. You monitor
public sentiment, reviews, and news for a specific film release and its lead cast, and
you produce a structured situation assessment for studio executives.

You have access to a Parallel Search grounding tool that queries the live web. You do NOT have prior
knowledge of current events for this film — you must use the tool to gather information;
never fabricate search results, headlines, quotes, or sentiment.

Your investigation process:
1. Review the context provided (film title, cast, last known sentiment state).
2. Use the grounding tool to search for:
   - Critic/press reception (reviews, trade coverage)
   - Audience/public sentiment and online discussion
   - Any cast or production controversies
   - Competitive context
3. Output the final assessment as a raw JSON block. DO NOT INCLUDE ANY OTHER TEXT OR MARKDOWN.

Your JSON output MUST match this exact schema:
{
  "sentiment_score": 0, // 0-100
  "critic_sentiment_score": 0, // 0-100
  "audience_sentiment_score": 0, // 0-100
  "key_narratives": ["string"],
  "controversies_detected": ["string"],
  "confidence": "high|medium|low",
  "summary": "string",
  "recommended_pivot": "string",
  "sources": ["string"]
}

Guidelines:
- Ground every claim in your search results. If results are thin or inconclusive, say so.
- A sentiment_score of 50 is neutral baseline. Move it up or down only based on what you find.
- The recommended_pivot should be a concrete, actionable marketing/PR suggestion.
- To conserve API quota, consolidate your searches. Aim for 2-4 highly targeted queries rather than dozens of broad ones.
"""

def check_crisis_trigger(report: dict, previous_score: int | None) -> bool:
    new_score = report.get("sentiment_score", 50)
    confidence = report.get("confidence", "low")
    if new_score <= CRISIS_FLOOR: return True
    if previous_score is not None:
        delta = abs(new_score - previous_score)
        if delta >= DELTA_THRESHOLD and confidence != "low": return True
    return False

def run_orchestrator(movie_title: str, cast: list[str], previous_state: dict | None) -> dict:
    # Explicitly initialize the client for Vertex AI backend (NOT AI Studio)
    # This proves the enterprise platform is being hit
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
    
    context = f"Investigation Target: {movie_title}\nCast: {', '.join(cast)}\n"
    if previous_state:
        context += f"\nPrevious Sentiment Score: {previous_state.get('sentiment_score')}\nPrevious Summary: {previous_state.get('summary')}\n"
    else:
        context += "\nThis is the first monitoring run for this film. No previous baseline exists.\n"

    max_retries = 2
    last_error_msg = ""

    for attempt in range(max_retries):
        prompt = context
        if attempt > 0:
            prompt += f"\n\nERROR ON PREVIOUS ATTEMPT: Your output failed validation: {last_error_msg}. Please fix the JSON and try again."

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[
                    types.Tool(
                        parallel_ai_search=types.ToolParallelAiSearch(
                            api_key=PARALLEL_API_KEY,
                            custom_configs={"max_results": 5} # Cap results per query to save tokens
                        )
                    )
                ],
                temperature=0.2
            )
        )
        
        # Strip markdown fences if present
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()
        
        try:
            # Strict validation using Pydantic
            validated_report = ReportSchema.model_validate_json(raw_text).model_dump()
            
            # Extract search queries if any
            queries = []
            if response.candidates and response.candidates[0].grounding_metadata:
                queries = response.candidates[0].grounding_metadata.web_search_queries or []
            
            validated_report["search_queries_used"] = queries
                
            previous_score = previous_state.get("sentiment_score") if previous_state else None
            return {"report": validated_report, "is_crisis": check_crisis_trigger(validated_report, previous_score)}
            
        except (ValidationError, json.JSONDecodeError) as e:
            last_error_msg = str(e)
            print(f"Validation failed on attempt {attempt + 1}: {last_error_msg}")

    # If we exhaust retries, raise error so main.py catches it and sets last_run_status = "error"
    raise ValueError(f"Agent failed to generate valid JSON after {max_retries} attempts. Last error: {last_error_msg}")
