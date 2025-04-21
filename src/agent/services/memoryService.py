import json
import logging
import uuid
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import os

# Check if we have PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    logging.info("PostgreSQL support not available. Using file-based memory storage.")

@dataclass
class MemoryItem:
    """Base class for all memory items"""
    memory_type: str = "base"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self):
        return asdict(self)

@dataclass
class ConversationMemory:
    """Short-term conversation memory"""
    session_id: str
    user_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory_type: str = "conversation"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self):
        return asdict(self)
    
@dataclass
class EpisodicMemory:
    """Memory of past interactions and outcomes"""
    session_id: str
    user_id: Optional[str] = None
    event_type: str = "interaction"
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory_type: str = "episodic"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self):
        return asdict(self)

@dataclass
class SemanticMemory:
    """Structured knowledge memory"""
    key: str
    value: Any
    category: str = "general"
    expiry: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory_type: str = "semantic"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self):
        return asdict(self)

class MemoryService:
    """Service for managing different types of memory"""
    
    def __init__(self, persistence_type="file"):
        self.persistence_type = persistence_type
        self._file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "memory_store.json")
        
        # Initialize DB connection if using PostgreSQL
        self._db_conn = None
        if persistence_type == "postgres" and HAS_POSTGRES:
            self._setup_postgres()
        
        # In-memory cache for active sessions
        self._memory_cache = {}
        
        # Load memory from persistence on startup
        self._load_memory()
    
    def _setup_postgres(self):
        """Set up PostgreSQL connection and tables"""
        try:
            conn_string = os.getenv("DATABASE_URL")
            if not conn_string:
                logging.warning("DATABASE_URL not set. Using file-based storage instead.")
                self.persistence_type = "file"
                return
                
            self._db_conn = psycopg2.connect(conn_string)
            
            # Create tables if they don't exist
            with self._db_conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    created_at FLOAT NOT NULL,
                    data JSONB NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_items(memory_type);
                CREATE INDEX IF NOT EXISTS idx_created_at ON memory_items(created_at);
                """)
            
            self._db_conn.commit()
            logging.info("PostgreSQL connection and tables set up successfully")
        
        except Exception as e:
            logging.error(f"Failed to initialize PostgreSQL: {e}")
            self.persistence_type = "file"
            logging.info("Falling back to file-based storage")
    
    def _load_memory(self):
        """Load memory from persistence"""
        if self.persistence_type == "file":
            try:
                if os.path.exists(self._file_path):
                    with open(self._file_path, 'r') as f:
                        data = json.load(f)
                        self._memory_cache = data
                        logging.info(f"Loaded {len(data)} memory items from file")
            except Exception as e:
                logging.error(f"Failed to load memory from file: {e}")
                self._memory_cache = {}
    
    def _save_memory(self):
        """Save memory to persistence"""
        if self.persistence_type == "file":
            try:
                with open(self._file_path, 'w') as f:
                    json.dump(self._memory_cache, f)
                logging.debug("Memory saved to file")
            except Exception as e:
                logging.error(f"Failed to save memory to file: {e}")
    
    def get_conversation_memory(self, session_id: str) -> ConversationMemory:
        """Get conversation memory for a session"""
        key = f"conversation:{session_id}"
        
        # Try to get from cache first
        if key in self._memory_cache:
            data = self._memory_cache[key]
            return ConversationMemory(**data)
        
        # If not in cache, check persistence
        if self.persistence_type == "postgres" and self._db_conn:
            try:
                with self._db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(
                        "SELECT data FROM memory_items WHERE id = %s AND memory_type = 'conversation'",
                        (key,)
                    )
                    result = cur.fetchone()
                    if result:
                        data = result[0]
                        self._memory_cache[key] = data
                        return ConversationMemory(**data)
            except Exception as e:
                logging.error(f"Error retrieving conversation memory from PostgreSQL: {e}")
        
        # Create new conversation memory if not found
        memory = ConversationMemory(session_id=session_id)
        self._memory_cache[key] = memory.to_dict()
        return memory
    
    def update_conversation_memory(self, session_id: str, messages: List[Dict[str, Any]],
                                  user_id: Optional[str] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> ConversationMemory:
        """Update conversation memory for a session"""
        memory = self.get_conversation_memory(session_id)
        
        # Update fields
        memory.messages = messages
        if user_id:
            memory.user_id = user_id
        if metadata:
            memory.metadata.update(metadata)
        
        # Save to cache and persistence
        key = f"conversation:{session_id}"
        self._memory_cache[key] = memory.to_dict()
        self._persist_memory(key, memory)
        
        return memory
    
    def add_to_conversation_memory(self, session_id: str, message: Dict[str, Any],
                                  user_id: Optional[str] = None) -> ConversationMemory:
        """Add a single message to conversation memory"""
        memory = self.get_conversation_memory(session_id)
        
        # Update fields
        memory.messages.append(message)
        if user_id:
            memory.user_id = user_id
        
        # Save to cache and persistence
        key = f"conversation:{session_id}"
        self._memory_cache[key] = memory.to_dict()
        self._persist_memory(key, memory)
        
        return memory
    
    def store_episodic_memory(self, session_id: str, event_type: str, 
                             content: Dict[str, Any],
                             user_id: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> EpisodicMemory:
        """Store an episodic memory"""
        memory = EpisodicMemory(
            session_id=session_id,
            event_type=event_type,
            content=content,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        # Save to cache and persistence
        key = f"episodic:{memory.id}"
        self._memory_cache[key] = memory.to_dict()
        self._persist_memory(key, memory)
        
        return memory
    
    def get_episodic_memories(self, session_id: Optional[str] = None, 
                             event_type: Optional[str] = None,
                             user_id: Optional[str] = None,
                             limit: int = 10) -> List[EpisodicMemory]:
        """Get episodic memories matching filters"""
        results = []
        count = 0
        
        # Filter memories from cache
        for key, data in self._memory_cache.items():
            if not key.startswith("episodic:"):
                continue
                
            if data.get("memory_type") != "episodic":
                continue
                
            if session_id and data.get("session_id") != session_id:
                continue
                
            if event_type and data.get("event_type") != event_type:
                continue
                
            if user_id and data.get("user_id") != user_id:
                continue
                
            results.append(EpisodicMemory(**data))
            count += 1
            
            if count >= limit:
                break
        
        # Sort by creation time (newest first)
        results.sort(key=lambda x: x.created_at, reverse=True)
        
        return results
    
    def store_semantic_memory(self, key: str, value: Any, 
                             category: str = "general",
                             expiry: Optional[float] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> SemanticMemory:
        """Store a semantic memory"""
        memory = SemanticMemory(
            key=key,
            value=value,
            category=category,
            expiry=expiry,
            metadata=metadata or {}
        )
        
        # Save to cache and persistence
        cache_key = f"semantic:{key}"
        self._memory_cache[cache_key] = memory.to_dict()
        self._persist_memory(cache_key, memory)
        
        return memory
    
    def get_semantic_memory(self, key: str) -> Optional[SemanticMemory]:
        """Get semantic memory by key"""
        cache_key = f"semantic:{key}"
        
        # Try to get from cache first
        if cache_key in self._memory_cache:
            data = self._memory_cache[cache_key]
            
            # Check expiry
            if data.get("expiry") and time.time() > data["expiry"]:
                del self._memory_cache[cache_key]
                self._delete_memory(cache_key)
                return None
                
            return SemanticMemory(**data)
        
        return None
    
    def get_semantic_memories_by_category(self, category: str, limit: int = 20) -> List[SemanticMemory]:
        """Get semantic memories by category"""
        results = []
        count = 0
        
        # Filter memories from cache
        for key, data in self._memory_cache.items():
            if not key.startswith("semantic:"):
                continue
                
            if data.get("memory_type") != "semantic":
                continue
                
            if data.get("category") != category:
                continue
                
            # Check expiry
            if data.get("expiry") and time.time() > data["expiry"]:
                del self._memory_cache[key]
                self._delete_memory(key)
                continue
                
            results.append(SemanticMemory(**data))
            count += 1
            
            if count >= limit:
                break
        
        return results
    
    def _persist_memory(self, key: str, memory: Union[ConversationMemory, EpisodicMemory, SemanticMemory]):
        """Persist memory to storage"""
        if self.persistence_type == "file":
            self._save_memory()
        elif self.persistence_type == "postgres" and self._db_conn:
            try:
                data = memory.to_dict()
                
                with self._db_conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO memory_items (id, memory_type, created_at, data)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET data = %s, created_at = %s
                        """,
                        (key, memory.memory_type, memory.created_at, 
                         json.dumps(data), json.dumps(data), memory.created_at)
                    )
                
                self._db_conn.commit()
            except Exception as e:
                logging.error(f"Error persisting memory to PostgreSQL: {e}")
    
    def _delete_memory(self, key: str):
        """Delete memory from storage"""
        if self.persistence_type == "file":
            self._save_memory()
        elif self.persistence_type == "postgres" and self._db_conn:
            try:
                with self._db_conn.cursor() as cur:
                    cur.execute("DELETE FROM memory_items WHERE id = %s", (key,))
                self._db_conn.commit()
            except Exception as e:
                logging.error(f"Error deleting memory from PostgreSQL: {e}")
    
    def cleanup_expired_memories(self):
        """Clean up expired memories"""
        current_time = time.time()
        keys_to_delete = []
        
        # Find expired memories
        for key, data in self._memory_cache.items():
            if data.get("memory_type") == "semantic" and data.get("expiry"):
                if current_time > data["expiry"]:
                    keys_to_delete.append(key)
        
        # Delete expired memories
        for key in keys_to_delete:
            del self._memory_cache[key]
            self._delete_memory(key)
        
        if keys_to_delete:
            logging.info(f"Cleaned up {len(keys_to_delete)} expired memories")