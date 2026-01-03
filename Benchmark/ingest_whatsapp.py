"""
Ingest WhatsApp data into Graphiti.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Entity Models
class User(BaseModel):
    """A WhatsApp user."""
    full_name: str = Field(..., description="The name of the user")
    phone_number: str | None = Field(None, description="The phone number of the user")

class CustomOpenAIClient(OpenAIClient):
    """
    Custom OpenAI client that overrides structured completion to work with local LLMs
    that don't support the OpenAI beta 'parse' endpoint.
    """
    async def _create_structured_completion(
        self,
        model: str,
        messages: list,
        temperature: float | None,
        max_tokens: int,
        response_model: type[BaseModel],
        reasoning: str | None = None,
        verbosity: str | None = None,
    ):
        """
        Override to use standard chat completion with json_object response format
        instead of client.responses.parse
        """
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
            # If it's not valid JSON, return it as a dict with the content
            return {"answer": content}

    def _handle_structured_response(self, response: Any) -> dict[str, Any]:
        """
        Override to handle standard ChatCompletion response from local LLM.
        """
        try:
            content = self._get_content(response)
            if not content:
                raise Exception(f"No content found in response: {response}")

            data = json.loads(content)
            
            # Debug logging
            logger.info(f"Raw LLM response: {json.dumps(data, indent=2)}")
            
            # Graphiti's ExtractedEntities model expects 'extracted_entities'.
            # Some LLMs might return 'entities' or 'entity_nodes' if not strictly governed.
            if 'extracted_entities' not in data:
                if 'entities' in data:
                    data['extracted_entities'] = data.pop('entities')
                elif 'entity_nodes' in data:
                    data['extracted_entities'] = data.pop('entity_nodes')
            
            # Additional cleanup: Ensure 'name' field exists (LLM might return entity_name)
            if 'extracted_entities' in data:
                for entity in data['extracted_entities']:
                    if 'entity_name' in entity and 'name' not in entity:
                        entity['name'] = entity.pop('entity_name')
            
            # Handle User entity attribute extraction with nested attributes
            if 'attributes' in data and isinstance(data['attributes'], dict):
                logger.info(f"Flattening attributes: {data['attributes']}")
                # Flatten attributes to top level
                for key, value in data['attributes'].items():
                    if key not in data:
                        data[key] = value
                        logger.info(f"Added {key} = {value} to top level")
                # Remove the attributes dict to avoid Neo4j MAP type error
                del data['attributes']

            
            # Handle User entity attribute extraction (name -> full_name)
            # Check if this is a User entity response (has entity_types with 'User')
            if 'name' in data and 'full_name' not in data:
                if 'entity_types' in data and 'User' in data['entity_types']:
                    data['full_name'] = data.pop('name')
            
            # Handle NodeResolutions schema (common for Graphiti extract_nodes)
            if 'entity_resolutions' not in data:
                 # Check if the LLM returned a single resolution object (it has 'duplicates' key usually)
                 if 'duplicates' in data:
                      data = {'entity_resolutions': [data]}
                 # OR if it returned just a list of resolutions directly (not wrapped in dict)
                 # But data is a dict here (json.loads(content)). If content was a list, data would be list.
            
            # Fix field names within entity_resolutions list
            if 'entity_resolutions' in data:
                for resolution in data['entity_resolutions']:
                    # Map entity_name to name at resolution level
                    if 'entity_name' in resolution and 'name' not in resolution:
                        resolution['name'] = resolution.pop('entity_name')
                    # Also check within duplicates list if present
                    if 'duplicates' in resolution and isinstance(resolution['duplicates'], list):
                        for dup in resolution['duplicates']:
                            # Only process if dup is a dict (sometimes LLM returns just IDs as integers)
                            if isinstance(dup, dict):
                                if 'entity_name' in dup and 'name' not in dup:
                                    dup['name'] = dup.pop('entity_name')

            
            # Handle ExtractedEdges schema
            if 'edges' not in data and 'facts' in data:
                 data['edges'] = data.pop('facts')
            
            # If LLM returned a single edge object instead of a list, wrap it
            # BUT don't wrap EdgeDuplicate responses (which have duplicate_facts/contradicted_facts)
            if 'edges' not in data and ('fact_type' in data or 'relation_type' in data):
                # Check if this is an EdgeDuplicate response (has duplicate_facts or contradicted_facts)
                if 'duplicate_facts' not in data and 'contradicted_facts' not in data:
                    data = {'edges': [data]}
            
            # Fix missing relation_type in edges (LLM sometimes only returns fact_type)
            if 'edges' in data and isinstance(data['edges'], list):
                for edge in data['edges']:
                    if 'fact_type' in edge and 'relation_type' not in edge:
                        edge['relation_type'] = edge['fact_type']
                    # Convert null entity IDs to -1 (Graphiti expects integers)
                    if edge.get('source_entity_id') is None:
                        edge['source_entity_id'] = -1
                    if edge.get('target_entity_id') is None:
                        edge['target_entity_id'] = -1

            
            # Handle empty responses - provide default empty edges list
            if not data or (isinstance(data, dict) and len(data) == 0):
                data = {'edges': []}

            
            # Debug logging after transformations
            logger.info(f"Transformed response: {json.dumps(data, indent=2)}")
            
            return data
        except (AttributeError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse structured response: {e}")
            raise Exception(f"Invalid response from LLM: {response}")

def get_graphiti_client() -> Graphiti:
    """Initialize Graphiti client with local LLM configuration."""
    
    # Neo4j Config
    neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
    neo4j_password = os.environ.get('NEO4J_PASSWORD', 'test1234')
    
    # LLM Config
    openai_api_key = os.environ.get('OPENAI_API_KEY', 'dummy_local_key')
    openai_base_url = os.environ.get('OPENAI_BASE_URL', 'http://69.48.159.10:30000/v1')
    
    # Fix common miss-configuration where /v1 is missing from local LLM base URL
    if openai_base_url and '/v1' not in openai_base_url:
        # If the user provided URL ends with '/', strip it before appending
        if openai_base_url.endswith('/'):
             openai_base_url = openai_base_url + "v1"
        else:
             openai_base_url = openai_base_url + "/v1"

    llm_config = LLMConfig(
        api_key=openai_api_key,
        base_url=openai_base_url,
        model="llama-3.1-70b", 
        small_model="llama-3.1-70b",  # Use same model for small tasks to avoid gpt-5-nano error
        temperature=0
    )
    
    # Use our custom client
    llm_client = CustomOpenAIClient(config=llm_config)
    
    # Embedder Config
    # User provided: http://69.48.159.10:30001/
    # We should use this for embeddings.
    embedder_base_url = os.environ.get('EMBEDDING_URL', 'http://69.48.159.10:30001')
    
    if embedder_base_url and '/v1' not in embedder_base_url:
         # Check if it ends with /
        if embedder_base_url.endswith('/'):
             embedder_base_url = embedder_base_url + "v1"
        else:
             embedder_base_url = embedder_base_url + "/v1"
    
    logger.info(f"Using embedding URL: {embedder_base_url}")

    # Initialize AsyncOpenAI client explicitly to control timeout
    from openai import AsyncOpenAI
    import httpx
    
    # Pre-check connection and fallback to localhost if public IP fails (common NAT issue)
    async def check_connection(url: str) -> bool:
        try:
             # Try a simple GET output request to health or just valid connection to base
             # We trim /v1 for health check usually, but let's just try to connect
             test_url = url.replace('/v1', '') # basic root check
             async with httpx.AsyncClient(timeout=3.0) as client:
                 await client.get(test_url)
             return True
        except Exception:
             return False

    # This check needs to be async, but get_graphiti_client is sync. 
    # We will just proceed with setting up the client with potential fallback logic handled by usage 
    # OR we can do a quick sync check via httpx.get inside this function if strictly needed, 
    # but strictly get_graphiti_client should probably just configure it.
    
    # Let's trust the timeout config, BUT if we want to be smart:
    # We can try to assume if it IS the public IP, and we are on linux, we might want localhost.
    
    # Simpler approach: Configure the client. If the user provided URL is unreachable, 
    # we can't easily swap it inside the library without more logic. 
    # However, let's stick to the Plan: Add robust configuration.
    
    # If the user is getting ConnectTimeout, let's fallback to localhost:30001 if the IP is 69.48.159.10
    if '69.48.159.10' in embedder_base_url:
         # Basic check if we can connect, if not use localhost
         import socket
         try:
             # Try to connect to the IP/Port
             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
             s.settimeout(2)
             host = '69.48.159.10'
             port = 30001
             s.connect((host, port))
             s.close()
         except (socket.timeout, socket.error):
             logger.warning(f"Could not connect to {embedder_base_url}. Attempting fallback to http://69.48.159.10:30001/v1")
             embedder_base_url = 'http://69.48.159.10:30001/v1'

    embedder_client = AsyncOpenAI(
        api_key='dummy_embed_key',
        base_url=embedder_base_url,
        timeout=30.0 # Increase timeout
    )

    embedder_config = OpenAIEmbedderConfig(
        embedding_model='Nexus-bge-m3-opensearch-embeddings'
    )
    
    # Pass the client explicitly
    embedder = OpenAIEmbedder(config=embedder_config, client=embedder_client)

    client = Graphiti(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
        llm_client=llm_client,
        embedder=embedder
    )
    
    return client

def parse_whatsapp_data(file_path: str) -> List[Dict[str, Any]]:
    """Parse WhatsApp JSONL data into list of episodes info."""
    episodes_data = []
    
    contacts_map = {}
    
    # First pass: Build contacts map if possible, though structure is per line
    # Actually, each line has "entry" -> "changes" -> "value" -> "contacts"
    # We can process line by line.
    
    with open(file_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        
                        # Update contacts
                        for contact in value.get('contacts', []):
                            wa_id = contact.get('wa_id')
                            name = contact.get('profile', {}).get('name')
                            if wa_id and name:
                                contacts_map[wa_id] = name
                                
                        # Process messages
                        messages = value.get('messages', [])
                        for msg in messages:
                            episodes_data.append({
                                'message': msg,
                                'contacts_snapshot': contacts_map.copy() # Snapshot in case names change? Unlikely but safe.
                            })
                            
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON line: {line[:50]}...")
                continue
                
    # Process extracted messages into Episode format
    parsed_episodes = []
    
    for item in episodes_data:
        msg = item['message']
        contacts = item['contacts_snapshot']
        
        msg_id = msg.get('id')
        timestamp = msg.get('timestamp')
        sender_id = msg.get('from')
        sender_name = contacts.get(sender_id, "Unknown User")
        msg_type = msg.get('type')
        group_id = msg.get('group_id')
        
        context_info = ""
        context = msg.get('context', {})
        if context:
             reply_to_id = context.get('id')
             reply_to_from = context.get('from')
             context_info = f" [Context: Reply to {reply_to_id} from {reply_to_from}]"
        
        body_content = ""
        
        if msg_type == 'text':
            body_content = msg.get('text', {}).get('body', '')
        elif msg_type == 'image':
            caption = msg.get('image', {}).get('caption', '')
            body_content = f"[Image] {caption}"
        elif msg_type == 'video':
            caption = msg.get('video', {}).get('caption', '')
            body_content = f"[Video] {caption}"
        elif msg_type == 'document':
            caption = msg.get('document', {}).get('caption', '')
            filename = msg.get('document', {}).get('filename', '')
            body_content = f"[Document: {filename}] {caption}"
        elif msg_type == 'reaction':
            emoji = msg.get('reaction', {}).get('emoji', '')
            target_msg = msg.get('reaction', {}).get('message_id', '')
            body_content = f"[Reaction: {emoji} to message {target_msg}]"
        elif msg_type == 'system':
             sys_type = msg.get('system', {}).get('type', '')
             sys_body = msg.get('system', {}).get('body', str(msg.get('system', {})))
             body_content = f"[System Event: {sys_type}] {sys_body}"
        else:
            body_content = f"[{msg_type} message]"

        # Format final episode body
        # "{Sender Name} ({Sender Phone}): {Message Body} [Context: Reply to {Reply ID}]"
        final_body = f"{sender_name} ({sender_id}): {body_content}{context_info}"
        
        parsed_episodes.append({
            'uuid': msg_id, # Using message ID as UUID might be risky if not UUID formatted, but Graphiti might handle strings. 
                            # If Graphiti strictly requires UUID4 strings, we might need to hash or generate one and store map.
                            # However, `podcast_runner.py` passed `group_id` as uuid4 but didn't specify uuid for episodes, letting Graphiti generate.
                            # BUT we want to reference this message later? 
                            # The plan said "name = Message ID".
                            # Let's let Graphiti generate UUID for the node, but we use Message ID as the 'name' or separate ID property if supported.
                            # Actually, `add_episode` has `uuid` param. If we pass a non-uuid string it might fail validation if Pydantic expects UUID.
                            # Let's check `graphiti_core` types.
                            # EpisodicNode model usually expects uuid field.
            'name': msg_id, # Use message ID as name
            'body': final_body,
            'timestamp': float(timestamp),
            'group_id': group_id
        })
        
    return parsed_episodes

async def main():
    file_path = 'whatsapp_synthetic_events.jsonl' # Assumes running from Benchmark dir or adjust path
    if not os.path.exists(file_path):
        file_path = os.path.join('Benchmark', 'whatsapp_synthetic_events.jsonl')
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    logger.info("Initializing Graphiti client...")
    client = get_graphiti_client()
    
    logger.info("Building indices...")
    await client.build_indices_and_constraints()
    
    logger.info("Parsing WhatsApp data...")
    episodes = parse_whatsapp_data(file_path)
    logger.info(f"Found {len(episodes)} episodes.")
    
    # Ingest
    for i, ep in enumerate(episodes):
        logger.info(f"Adding episode {i+1}/{len(episodes)}: {ep['name']}")
        
        # Convert timestamp to datetime
        ref_time = datetime.fromtimestamp(ep['timestamp'])
        
        await client.add_episode(
            name=ep['name'],
            episode_body=ep['body'],
            reference_time=ref_time,
            source_description='Whatsapp messages',
            group_id=ep['group_id'], # Use actual group ID from WhatsApp
            # Removed entity_types to allow generic entity extraction
            # entity_types={'User': User},
        )
        
    logger.info("Building communities...")
    await client.build_communities()
    
    await client.close()
    logger.info("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(main())
