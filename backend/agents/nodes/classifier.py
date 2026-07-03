import logging
from typing import Dict, Any

from agents.state import QueryState
from agents.prompts import CLASSIFIER_SYSTEM_PROMPT
from config import GROQ_MODEL
from agents.nodes.utils import get_groq_client

logger = logging.getLogger("querymind.agents.nodes.classifier")

async def query_classifier(state: QueryState) -> Dict[str, Any]:
    """
    Node 0: Classifies user input to check if it's a valid DB query, a greeting, or out of scope.
    """
    question = state.get("user_question", "")
    trace_steps = list(state.get("trace_steps", []))
    
    logger.info("Classifying user question: %s", question)
    
    try:
        client = get_groq_client()
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=10,
        )
        
        raw_intent = (response.choices[0].message.content or "").strip().lower()
        
        intent = "database_query"
        if "greeting" in raw_intent:
            intent = "greeting"
        elif "out_of_scope" in raw_intent or "out" in raw_intent:
            intent = "out_of_scope"
        
        logger.info("Classified intent: %s", intent)
        
        trace_steps.append({
            "node": "query_classifier",
            "status": "success",
            "intent": intent,
            "raw_response": raw_intent
        })
        
        return {
            "intent": intent,
            "trace_steps": trace_steps
        }
    except Exception as e:
        logger.error("query_classifier failed: %s", e)
        trace_steps.append({
            "node": "query_classifier",
            "status": "error",
            "error": str(e),
            "intent": "database_query"
        })
        return {
            "intent": "database_query",
            "trace_steps": trace_steps
        }


async def direct_responder(state: QueryState) -> Dict[str, Any]:
    """
    Direct response node for greetings and out-of-scope queries.
    """
    intent = state.get("intent", "out_of_scope")
    trace_steps = list(state.get("trace_steps", []))
    
    if intent == "greeting":
        answer = "Hello! I am QueryMind, your Database Copilot. How can I help you query the e-commerce database today?"
    else:
        answer = "I'm sorry, but I can only answer questions related to the database schema (customers, orders, products, sellers, reviews, payments, etc.). Please ask a query related to our data."
    
    trace_steps.append({
        "node": "direct_responder",
        "status": "success",
        "intent": intent,
        "answer": answer
    })
    
    return {
        "final_answer": answer,
        "success": True,
        "trace_steps": trace_steps
    }
