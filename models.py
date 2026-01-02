from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
import uuid

class BlockType(Enum):
    COMMAND = "command"
    AI_RESPONSE = "ai"
    SYSTEM_MSG = "system"

@dataclass
class BlockState:
    type: BlockType
    content_input: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    content_output: str = ""
    exit_code: Optional[int] = None
    is_running: bool = True
    metadata: Dict = field(default_factory=dict)
