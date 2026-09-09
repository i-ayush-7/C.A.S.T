from vertexai.generative_models import FunctionDeclaration, Tool

SYSTEM_PROMPT = """You are a PR & Release Strategy Analyst for a film studio. You monitor
public sentiment, reviews, and news for a specific film release and its lead cast, and
you produce a structured situation assessment for studio executives.

You have access to a `search_web` tool that queries the live web. You do NOT have prior
knowledge of current events for this film — you must use the tool to gather information;
never fabricate search results, headlines, quotes, or sentiment.

Your investigation process:
1. Review the context provided (film title, cast, last known sentiment state, and a
   summary of what was found in the previous monitoring run, if any).
2. Decide what to search for. At minimum, cover:
   - Critic/press reception (reviews, trade coverage)
   - Audience/public sentiment and online discussion
   - Any cast or production controversies
   - Competitive context (other releases, comparable films) if relevant
   You decide how many searches this requires — usually 2 to 5. Simple, quiet weeks
   may need fewer searches; a fast-moving story may need follow-up searches to
   confirm or clarify what you find in the first round. Do not search redundantly.
3. Once you have enough information to form a confident assessment, call
   `report_generator` exactly once with your final structured output. Do not call
   report_generator until you have stopped searching.

Guidelines:
- Ground every claim in your search results. If results are thin or inconclusive,
  say so in your narrative rather than guessing.
- Distinguish critic sentiment from audience/public sentiment when they diverge —
  this is often the most useful signal for a studio.
- A sentiment_score of 50 is neutral baseline. Move it up or down only based on
  what your searches actually show, not on the topic's inherent volatility.
- The recommended_pivot should be a concrete, actionable marketing/PR suggestion,
  not a vague platitude (e.g. "shift ad creative toward practical effects footage
  and de-emphasize the trailer's dialogue-heavy scenes" rather than "improve
  messaging").
- Keep key_narratives to the 2-4 storylines that actually matter this run, not an
  exhaustive list of everything you read.
"""

search_web_func = FunctionDeclaration(
    name="search_web",
    description="Search the live web via Parallel Search API for current news, reviews, social/discussion content, or trade coverage.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "category": {"type": "string", "enum": ["critic_review", "audience_sentiment", "controversy", "competitive", "general"]},
            "recency_days": {"type": "integer"},
        },
        "required": ["query", "category"],
    },
)

SEARCH_WEB_TOOL = Tool(function_declarations=[search_web_func])

report_generator_func = FunctionDeclaration(
    name="report_generator",
    description="Submit the final structured PR/sentiment assessment for this monitoring run.",
    parameters={
        "type": "object",
        "properties": {
            "sentiment_score": {"type": "integer"},
            "critic_sentiment_score": {"type": "integer"},
            "audience_sentiment_score": {"type": "integer"},
            "key_narratives": {"type": "array", "items": {"type": "string"}},
            "controversies_detected": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "summary": {"type": "string"},
            "recommended_pivot": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "sentiment_score",
            "critic_sentiment_score",
            "audience_sentiment_score",
            "key_narratives",
            "controversies_detected",
            "confidence",
            "summary",
            "recommended_pivot",
            "sources",
        ],
    },
)

AGENT_TOOL = Tool(function_declarations=[search_web_func, report_generator_func])
ALL_TOOLS = [AGENT_TOOL]
