from typing import List, Optional
from models import BlockState, BlockType

class ContextManager:
    @staticmethod
    def get_context(history_blocks: List[BlockState], limit_chars: int = 4000) -> str:
        """
        Builds a text context from the block history.
        Includes Command inputs and outputs, and AI interactions.
        """
        buffer = []
        current_len = 0
        
        # Iterate backwards to get most recent context first
        for block in reversed(history_blocks):
            block_text = ""
            if block.type == BlockType.COMMAND:
                block_text = f"User Command: {block.content_input}\nOutput:\n{block.content_output}\n"
            elif block.type == BlockType.AI_QUERY:
                block_text = f"User Question: {block.content_input}\n"
            elif block.type == BlockType.AI_RESPONSE:
                block_text = f"AI Answer: {block.content_output}\n"
            
            if not block_text:
                continue
                
            if current_len + len(block_text) > limit_chars:
                break
            
            buffer.insert(0, block_text)
            current_len += len(block_text)
            
        return "\n".join(buffer)
