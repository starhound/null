# RLLM Training & Chat with Code

Null Terminal includes a powerful local engine for both "Chat with Code" (RAG) and "Scratch Training" (creating new models).

## 🧠 Chat with Code (RAG)

Index your local codebase to allow the AI to answer questions about your project.

### Usage
1. **Navigate to your project root.**
2. **Build the index:**
   ```bash
   /index build
   ```
3. **Ask questions:**
   Just toggle AI mode (`Ctrl+Space`) and ask:
   > "How does the authentication system work?"
   > "Refactor the check_permissions function in utils.py"

The system uses semantic search to find relevant code snippets and inserts them into the context window.

## 🏋️ RLLM Scratch Training

Train your own small language models (like LLaMA or custom architectures) directly on your hardware.

### 1. The Training Screen
Access the training UI via the command palette (`Ctrl+P`) -> **"Open Training Dashboard"** or by typing `/train`.

### 2. Configuration
The dashboard allows you to configure text-based training parameters:

- **Model Architecture**: Define layers, hidden size, heads, etc. (e.g., LLaDA config).
- **Dataset**: Path to your local training data (streaming JSON/Text supported).
- **Hyperparameters**: Learning rate, batch size, context length.
- **Optimization**: Flash Attention, BF16 mixed precision, Activation Checkpointing.

### 3. Monitoring
Real-time metrics are displayed in the TUI:
- **Loss Curves**: Training and validation loss.
- **Throughput**: Tokens per second.
- **Hardware Stats**: GPU/CPU usage and VRAM consumption.

### 4. Output
Trained checkpoints are saved to `~/.null/models/checkpoints`. You can load these back into Null Terminal using the **Custom Provider** interface.

---

> [!WARNING]
> Training requires significant hardware resources. Ensure you have an NVIDIA GPU with CUDA support for best performance.
