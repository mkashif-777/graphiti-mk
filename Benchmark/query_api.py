#!/usr/bin/env python

import json
import logging
import os
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.prompts.models import Message
from graphiti_core.search.search_helpers import search_results_to_context_string
from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_RRF
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence noisy Neo4j notifications
logging.getLogger("neo4j").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

app = FastAPI()

# ---- CONFIG ----
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'test1234')

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "dummy_local_key")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:30000/")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://localhost:30001/")

# Helper to normalize URLs
def normalize_url(url: str) -> str:
    if not url.endswith('/'):
        url += '/'
    if not url.endswith('v1/'):
        url += 'v1'
    return url

LLM_BASE_URL = normalize_url(OPENAI_BASE_URL)
EMBED_BASE_URL = normalize_url(EMBEDDING_URL)

class CustomOpenAIClient(OpenAIClient):
    """
    Custom OpenAI client that overrides structured completion to work with local LLMs.
    """
    async def _create_structured_completion(self, model, messages, temperature, max_tokens, response_model, reasoning=None, verbosity=None):
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={'type': 'json_object'},
        )

    def _get_content(self, response: Any) -> str:
        """Helper to safely get content from either an object or a dict response."""
        try:
            # Handle object-based response (standard OpenAI library)
            if hasattr(response, 'choices'):
                message = response.choices[0].message
                if hasattr(message, 'content'):
                    return message.content or ""
                if isinstance(message, dict):
                    return message.get('content', "")
            
            # Handle dictionary-based response (some local LLM wrappers)
            if isinstance(response, dict):
                choices = response.get('choices', [])
                if choices:
                    message = choices[0].get('message', {})
                    if isinstance(message, dict):
                        return message.get('content', "")
                    if hasattr(message, 'content'):
                        return message.content or ""
            
            return ""
        except Exception as e:
            logger.error(f"Error extracting content from response: {e}")
            return ""

    def _handle_json_response(self, response: Any) -> dict[str, Any]:
        """Override to handle non-JSON responses and dict-based responses."""
        content = self._get_content(response)
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If it's not valid JSON, return it as the answer directly
            return {"answer": content}

    def _handle_structured_response(self, response: Any) -> dict[str, Any]:
        try:
            content = self._get_content(response)
            if not content:
                return {}
            data = json.loads(content)
            
            # Key mappings for compatibility
            if 'extracted_entities' not in data:
                if 'entities' in data: data['extracted_entities'] = data.pop('entities')
                elif 'entity_nodes' in data: data['extracted_entities'] = data.pop('entity_nodes')
            
            if 'extracted_entities' in data:
                for entity in data['extracted_entities']:
                    if 'entity_name' in entity and 'name' not in entity:
                        entity['name'] = entity.pop('entity_name')
            
            if 'entity_resolutions' not in data and 'duplicates' in data:
                data = {'entity_resolutions': [data]}
            
            if 'entity_resolutions' in data:
                for res in data['entity_resolutions']:
                    if 'entity_name' in res and 'name' not in res: res['name'] = res.pop('entity_name')
                    if 'duplicates' in res and isinstance(res['duplicates'], list):
                        for dup in res['duplicates']:
                            if isinstance(dup, dict) and 'entity_name' in dup and 'name' not in dup:
                                dup['name'] = dup.pop('entity_name')

            if 'edges' not in data and 'facts' in data: data['edges'] = data.pop('facts')
            if 'edges' not in data and ('fact_type' in data or 'relation_type' in data):
                if 'duplicate_facts' not in data and 'contradicted_facts' not in data:
                    data = {'edges': [data]}
            
            if 'edges' in data and isinstance(data['edges'], list):
                for edge in data['edges']:
                    if 'fact_type' in edge and 'relation_type' not in edge: edge['relation_type'] = edge['fact_type']
                    if edge.get('source_entity_id') is None: edge['source_entity_id'] = -1
                    if edge.get('target_entity_id') is None: edge['target_entity_id'] = -1

            if not data or (isinstance(data, dict) and len(data) == 0):
                data = {'edges': []}
                
            return data
        except Exception as e:
            logger.error(f"Error parsing structured response: {e}")
            return {}


# Global Graphiti instance
graphiti = None

@app.on_event("startup")
async def startup_event():
    try:
        global graphiti
        llm_config = LLMConfig(
            api_key=OPENAI_API_KEY,
            base_url=LLM_BASE_URL,
            model="llama-3.1-70b",
            small_model="llama-3.1-70b" # Use same for small_model to avoid gpt-5 errors
        )
        llm_client = CustomOpenAIClient(config=llm_config)
        
        embedder_config = OpenAIEmbedderConfig(
            api_key=OPENAI_API_KEY,
            base_url=EMBED_BASE_URL,
            embedding_model="Nexus-bge-m3-opensearch-embeddings"
        )
        embedder = OpenAIEmbedder(config=embedder_config)
        
        logger.info(f"Connecting to Neo4j at {NEO4J_URI}...")
        graphiti = Graphiti(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD,
            llm_client=llm_client,
            embedder=embedder
        )
        logger.info("Graphiti initialized and connected to Neo4j")
    except Exception as e:
        logger.error(f"Failed to initialize Graphiti: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    if graphiti:
        await graphiti.close()
        logger.info("Graphiti connection closed")

# ---- REQUEST SCHEMA ----
class QueryRequest(BaseModel):
    query: str

# ---- API ENDPOINT ----
@app.post("/query")
async def query_graph(req: QueryRequest):
    try:
        logger.info(f"Received query: {req.query}")
        
        if graphiti is None:
            raise Exception("Graphiti client not initialized")

        # Retrieve graph context using search_
        # Using COMBINED_HYBRID_SEARCH_RRF to include nodes, edges, episodes, and communities
        from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_RRF
        
        logger.info("Performing graph search...")
        search_results = await graphiti.search_(
            query=req.query,
            config=COMBINED_HYBRID_SEARCH_RRF
        )
        
        # Format context for LLM
        logger.info("Formatting search results...")
        context_text = search_results_to_context_string(search_results)
        
        # Call LLM for final answer
        prompt = f"""
You are answering based on WhatsApp conversations stored in a knowledge graph.

{context_text}

Question: {req.query}

Answer concisely and only using the context provided above.
"""
        
        logger.info("Calling LLM for synthesis...")
        response = await graphiti.clients.llm_client.generate_response(
            messages=[Message(role="user", content=prompt)]
        )
        
        # generate_response returns a dict (parsed JSON or fallback)
        answer = ""
        if isinstance(response, dict):
            # Try various common keys used by LLMs for structured answers
            answer_keys = ['answer', 'response', 'result', 'text', 'content', 'message']
            for key in answer_keys:
                if key in response and response[key]:
                    answer = str(response[key])
                    break
            
            if not answer:
                # Fallback: if it's a dict but we didn't find a key, 
                # check if there's only one key or take the longest string value
                string_values = [v for v in response.values() if isinstance(v, str)]
                if string_values:
                    answer = max(string_values, key=len)
                else:
                    answer = str(response)
        else:
            answer = str(response)
            
        logger.info("Synthesis complete.")

        return {
            "query": req.query,
            "answer": answer,
            "context": context_text
        }

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return {"error": str(e), "query": req.query}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8102)
