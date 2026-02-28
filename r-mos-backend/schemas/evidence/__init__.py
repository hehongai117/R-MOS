# Evidence Schema Definitions
# Version: 1.0.0

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import hashlib
import hmac
import time


class EvidenceType(str, Enum):
    """Types of evidence"""
    TRAJECTORY = "trajectory"
    SENSOR_READING = "sensor_reading"
    SCREENSHOT = "screenshot"
    VERDICT = "verdict"
    TIMING = "timing"
    STATE_SNAPSHOT = "state_snapshot"


# Replay prevention settings
MAX_TIME_DRIFT_MS = 5 * 60 * 1000  # 5 minutes


class Evidence(BaseModel):
    """Evidence structure with chain hash"""
    id: str
    task_id: str
    step_id: str
    action_id: str
    type: EvidenceType = EvidenceType.TRAJECTORY

    # Storage
    storage_uri: str = Field(default="", description="S3/OSS path")
    content_preview: str = Field(default="", description="First 256 chars for quick reference")

    # Chain hash (anti-tamper)
    hash_prev: str = Field(default="", description="Previous evidence hash")
    hash_content: str = Field(..., description="SHA256 of content")
    chain_hash: str = Field(default="", description="SHA256(prev + content + timestamp)")

    # Signature
    signature: str = Field(default="", description="Server signature (HMAC)")

    # Anti-replay
    nonce: str = Field(default="", description="Random nonce for anti-replay")
    expires_at: int = Field(default=0, description="Expiration timestamp (0 = never)")

    # Timestamps
    timestamp_client: int = 0
    timestamp_server: int = 0

    # Schema version
    schema_version: str = Field(default="1.0.0")

    # Metadata
    actor: str = Field(default="", description="Who generated this evidence")
    source: str = Field(default="", description="Where this came from (3d, tool, ui)")

    def verify_chain(self, prev_hash: str) -> bool:
        """Verify chain integrity"""
        return self.hash_prev == prev_hash

    def verify_anti_replay(self, current_time_ms: int = None) -> tuple[bool, str]:
        """Verify evidence is not replayed"""
        if current_time_ms is None:
            current_time_ms = int(time.time() * 1000)

        # Check expiration
        if self.expires_at > 0 and current_time_ms > self.expires_at:
            return False, f"Evidence expired at {self.expires_at}"

        # Check time drift
        time_diff = abs(self.timestamp_server - self.timestamp_client)
        if time_diff > MAX_TIME_DRIFT_MS:
            return False, f"Time drift too large: {time_diff}ms"

        return True, "Anti-replay OK"


class EvidenceChainValidator:
    """Validate evidence chain integrity"""

    @staticmethod
    def validate_chain(evidence_list: list[Evidence]) -> tuple[bool, str]:
        """Validate entire chain"""
        if not evidence_list:
            return True, "Empty chain is valid"

        # Check first item has empty prev_hash
        if evidence_list[0].hash_prev != "":
            return False, f"First evidence must have empty hash_prev, got: {evidence_list[0].hash_prev}"

        # Check chain continuity
        for i in range(1, len(evidence_list)):
            if evidence_list[i].hash_prev != evidence_list[i-1].hash_content:
                return False, f"Chain broken at index {i}: {evidence_list[i].hash_prev} != {evidence_list[i-1].hash_content}"

        return True, "Chain valid"

    @staticmethod
    def verify_signature(evidence: Evidence, secret_key: str) -> bool:
        """Verify server signature"""
        if not evidence.signature:
            return False

        message = f"{evidence.id}:{evidence.hash_content}:{evidence.timestamp_server}"
        expected = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(evidence.signature, expected)

    @staticmethod
    def validate_evidence(evidence: Evidence, secret_key: str) -> tuple[bool, str]:
        """Full validation: chain + signature + anti-replay"""
        # Check signature
        if not EvidenceChainValidator.verify_signature(evidence, secret_key):
            return False, "Invalid signature"

        # Check anti-replay
        is_valid, msg = evidence.verify_anti_replay()
        if not is_valid:
            return False, f"Anti-replay failed: {msg}"

        return True, "Evidence valid"


class EvidenceGenerator:
    """Generate and sign evidence"""

    @staticmethod
    def generate_content_hash(content: dict) -> str:
        """Generate SHA256 hash of content"""
        import json
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    @staticmethod
    def generate_chain_hash(prev_hash: str, content_hash: str, timestamp: int) -> str:
        """Generate chain hash"""
        chain_input = f"{prev_hash}:{content_hash}:{timestamp}"
        return hashlib.sha256(chain_input.encode()).hexdigest()

    @staticmethod
    def sign_evidence(evidence: Evidence, secret_key: str) -> str:
        """Sign evidence with server secret"""
        message = f"{evidence.id}:{evidence.hash_content}:{evidence.timestamp_server}"
        return hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
