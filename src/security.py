"""
Security module for PII detection and anonymization using Redis vault.
"""
from presidio_analyzer import AnalyzerEngine
import redis
import json
import uuid
import logging
from typing import Optional
from cryptography.fernet import Fernet
import base64

from src.config import settings
from src.logger import get_logger, get_correlation_id
from src.metrics import (
    pii_entities_detected_total, 
    pii_anonymization_duration_seconds,
    redis_connections_active,
    track_time
)

logger = get_logger(__name__)

class PIIManager:
    """
    Manages PII detection, anonymization, and secure storage (vault).
    Uses Redis for persistence and Fernet for encryption.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize PII Maanger.
        
        Args:
            redis_client: Optional injected Redis client (for testing)
        """
        self._analyzer = None  # Lazy init
        self.vault = {}  # In-memory fallback
        self._redis = redis_client
        self._cipher = None
        self._redis_initialized = False
        
        # Initialize encryption - fast operation
        try:
            if settings.api_keys:
                seed = settings.api_keys[0].ljust(32)[:32].encode()
                key = base64.urlsafe_b64encode(seed)
                self._cipher = Fernet(key)
            else:
                self._cipher = Fernet(Fernet.generate_key())
        except Exception as e:
            logger.warning("Failed to initialize encryption, using plaintext", extra={"error": str(e)})

    @property
    def analyzer(self):
        """Lazy initialization of AnalyzerEngine."""
        if self._analyzer is None:
            logger.info("Initializing Presidio AnalyzerEngine...")
            self._analyzer = AnalyzerEngine()
            logger.info("Presidio AnalyzerEngine initialized")
        return self._analyzer

    @property
    def redis(self):
        """Lazy initialization of Redis connection."""
        if self._redis is None and not self._redis_initialized:
            try:
                self._redis = redis.from_url(
                    settings.redis_url,
                    max_connections=settings.redis_max_connections,
                    socket_timeout=5,
                    decode_responses=False
                )
                self._redis.ping()
                logger.info("Connected to Redis PII vault")
            except Exception as e:
                logger.error("Failed to connect to Redis, using in-memory vault", extra={"error": str(e)})
                self._redis = None
            finally:
                self._redis_initialized = True
        return self._redis

    def _encrypt(self, text: str) -> bytes:
        """Encrypt text using Fernet."""
        if self._cipher:
            return self._cipher.encrypt(text.encode())
        return text.encode()

    def _decrypt(self, data: bytes) -> str:
        """Decrypt text using Fernet."""
        if self._cipher:
            return self._cipher.decrypt(data).decode()
        return data.decode()

    @track_time(pii_anonymization_duration_seconds)
    def anonymize(self, text: str, trace_id: Optional[str] = None) -> str:
        """
        Detect and replace PII entities with tokens.
        Stores the mapping in Redis vault.
        """
        if not text:
            return text
            
        trace_id = trace_id or get_correlation_id() or "unknown"
        
        # 1. Analyze text (Trigger lazy init)
        results = self.analyzer.analyze(
            text=text,
            language='en',
            entities=[
                "PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", 
                "CREDIT_CARD", "LOCATION", "DATE_TIME", "IBAN_CODE"
            ]
        )
        
        # 2. Process results backwards
        for result in sorted(results, key=lambda x: x.start, reverse=True):
            if result.score < settings.pii_confidence_threshold:
                continue
                
            sensitive_data = text[result.start:result.end]
            entity_type = result.entity_type
            
            # Track metrics
            pii_entities_detected_total.labels(entity_type=entity_type).inc()
            
            # Generate token
            token_id = str(uuid.uuid4())[:8]
            token = f"[{entity_type}_{token_id}]"
            
            # Store in vault
            vault_data = {
                "value": base64.b64encode(self._encrypt(sensitive_data)).decode(),
                "type": entity_type,
                "trace_id": trace_id
            }
            
            try:
                if self.redis:
                    key = f"pii:{token}"
                    self.redis.setex(
                        key,
                        settings.pii_vault_ttl,
                        json.dumps(vault_data)
                    )
                else:
                    self.vault[token] = vault_data
            except Exception as e:
                logger.error("Failed to store PII in vault", extra={
                    "trace_id": trace_id,
                    "error": str(e)
                })
            
            text = text[:result.start] + token + text[result.end:]
            
            logger.debug("Anonymized entity", extra={
                "trace_id": trace_id,
                "entity": entity_type,
                "token": token
            })
            
        return text

    def deanonymize(self, text: str, trace_id: Optional[str] = None) -> str:
        """
        Restore original PII data from tokens.
        """
        trace_id = trace_id or get_correlation_id() or "unknown"
        
        import re
        token_pattern = r"\[[A-Z_]+_[a-f0-9]{8}\]"
        tokens = re.findall(token_pattern, text)
        
        for token in tokens:
            try:
                vault_data = None
                
                if self.redis:
                    key = f"pii:{token}"
                    data = self.redis.get(key)
                    if data:
                        vault_data = json.loads(data)
                else:
                    vault_data = self.vault.get(token)
                
                if vault_data:
                    encrypted_value = base64.b64decode(vault_data["value"])
                    real_value = self._decrypt(encrypted_value)
                    text = text.replace(token, real_value)
                else:
                    logger.warning("Token not found in vault", extra={
                        "trace_id": trace_id,
                        "token": token
                    })
                    
            except Exception as e:
                logger.error("Failed to deanonymize token", extra={
                    "trace_id": trace_id,
                    "token": token,
                    "error": str(e)
                })
        
        return text

# Global instance
pii_manager = PIIManager()