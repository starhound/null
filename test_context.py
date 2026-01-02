from models import BlockState, BlockType
from context import ContextManager

# Mock blocks
b1 = BlockState(type=BlockType.COMMAND, content_input="echo hello", content_output="hello\n")
b2 = BlockState(type=BlockType.AI_QUERY, content_input="hi")
b3 = BlockState(type=BlockType.AI_RESPONSE, content_input="", content_output="Hello there.")

blocks = [b1, b2, b3]

print("--- Testing Context Manager ---")
ctx = ContextManager.get_context(blocks)
print(f"Context Length: {len(ctx)}")
print("--- Context Content ---")
print(ctx)
print("-----------------------")

if "User Command: echo hello" in ctx and "Output:\nhello" in ctx:
    print("SUCCESS: Command found.")
else:
    print("FAILURE: Command missing.")

if "User Question: hi" in ctx:
    print("SUCCESS: Query found.")
