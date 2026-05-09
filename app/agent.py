import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from app.retriever import search_catalog
from app.models import ChatResponse, Recommendation

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# We use Flash for speed (critical for the 30s timeout) and force JSON output
model = genai.GenerativeModel(
    'gemini-2.5-flash', 
    generation_config={"response_mime_type": "application/json"}
)
async def process_chat(messages):
    # 1. Reconstruct the stateless conversation
    history_str = "\n".join([f"{m.role}: {m.content}" for m in messages])

    # --- STEP 1: THE ROUTER ---
    # Determine intent and extract search constraints
    router_prompt = f"""
    You are an SHL assessment hiring agent.
    Conversation History:
    {history_str}

    Analyze the LAST user message and decide the next action.
    1. If vague (e.g., "I need a test", "hiring someone"), action="clarify".
    2. If asking for legal advice, general hiring tips, or non-SHL tools, action="refuse".
    3. If specific constraints exist (e.g., "Java dev", "mid-level", "compare X and Y", "add personality tests"), action="search".

    Return strictly JSON matching this schema:
    {{
        "action": "clarify" | "refuse" | "search",
        "query": "extracted keywords for the database if searching, else empty",
        "reply": "Your text reply if clarifying or refusing, else empty"
    }}
    
    GUIDELINES:
- Do not recommend a shortlist until you know the ROLE and the PURPOSE (Selection vs. Development).
- If the user says "Senior Leadership" but doesn't specify the intent, your action must be "clarify".
- Only move to "search" when you have enough constraints to provide a professional recommendation.
    """
    
    router_res = model.generate_content(router_prompt)
    decision = json.loads(router_res.text)

    # If we don't need the catalog, return immediately
    if decision["action"] in ["clarify", "refuse"]:
        return ChatResponse(
            reply=decision["reply"],
            recommendations=[],
            end_of_conversation=False
        )

    # --- STEP 2: RETRIEVAL & FORMATTING ---
    # Hit ChromaDB for the top 10 results (Maximizes Recall@10 score)
    raw_results = search_catalog(decision["query"], n_results=10)
    
    # If ChromaDB returns a dictionary, convert it to a list of dicts for the LLM
    catalog_context = []
    if raw_results and isinstance(raw_results, list):
         catalog_context = raw_results
    elif raw_results and isinstance(raw_results, dict):
         # Handle potential ChromaDB output format variations
         catalog_context = [raw_results]
         
    context_str = json.dumps(catalog_context, indent=2)

    final_prompt = f"""
    You are an SHL assessment hiring agent.
    Conversation History:
    {history_str}

    You searched the catalog for "{decision['query']}" and found these exact SHL tests:
    {context_str}

    Task: Provide a final response to the user.
    - If recommending, list between 1 and 10 relevant tests from the search results.
    - If comparing, explain the differences based ONLY on the test types and names.
    - NEVER invent a URL or recommend a test not in the search results.
    - If the user changes constraints mid-conversation, update the list using the new search results.

    Return strictly JSON matching this exact schema:
    {{
        "reply": "Your conversational text reply",
        "recommendations": [
            {{"name": "Exact Name", "url": "Exact URL", "test_type": "Exact Type"}}
        ],
        "end_of_conversation": true if you have delivered a grounded shortlist, else false
    }}

    GUIDELINES for 'end_of_conversation':
- Set to FALSE if you have just delivered the first set of recommendations. This allows the user to ask for changes or clarifications.
- Set to TRUE only if the user says something like "Thanks," "Perfect," "That is all," or if you have reached Turn 7 of the conversation.

    """

    final_res = model.generate_content(final_prompt)
    final_data = json.loads(final_res.text)

    # Validate and map to our strict Pydantic models
    recs = []
    for r in final_data.get("recommendations", []):
        try:
            recs.append(Recommendation(**r))
        except:
            continue # Drop invalid formats to protect the API response

    return ChatResponse(
        reply=final_data.get("reply", "Here are the recommendations."),
        recommendations=recs,
        end_of_conversation=final_data.get("end_of_conversation", True)
    )