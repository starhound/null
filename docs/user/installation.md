# Installation

Null Terminal is cross-platform and can be installed on Linux, macOS, and Windows. Choose the method that best fits your workflow.

!!! info "System Requirements"
    Null Terminal requires **Python 3.10** or higher. We recommend using the latest stable Python version for the best experience.

## Quick Start

The fastest way to get up and running is using `pipx`.

```bash
pipx install null-terminal
null
```

---

## Installation Methods

=== "pipx (Recommended)"

    [`pipx`](https://github.com/pypa/pipx) is the recommended tool for installing Python applications. It creates an isolated environment for each application, preventing dependency conflicts.

    1. **Install pipx** (if not already installed):
       ```bash
       python3 -m pip install --user pipx
       python3 -m pipx ensurepath
       ```
    2. **Install Null Terminal**:
       ```bash
       pipx install null-terminal
       ```
    3. **Launch**:
       Type `null` in your terminal.

    !!! tip "Automatic Updates"
        To update Null Terminal to the latest version, simply run:
        ```bash
        pipx upgrade null-terminal
        ```

=== "Docker"

    Null Terminal is available as a Docker image, perfect for isolated environments or trying it out without local installation.

    1. **Run the container**:
       ```bash
       docker run -it --rm \
         -v ~/.null:/root/.null \
         ghcr.io/starhound/null-terminal:latest
       ```

    !!! warning "Persistence"
        Always mount the `~/.null` volume as shown above to persist your configuration, API keys, and session history. Without this, all data will be lost when the container exits.

    2. **Custom Build** (Optional):
       If you want to build the image locally:
       ```bash
       git clone https://github.com/starhound/null.git
       cd null
       docker build -t null-terminal .
       docker run -it --rm -v ~/.null:/root/.null null-terminal
       ```

=== "Windows"

    Windows users have several options, from native installers to standalone binaries.

    #### EXE Installer
    1. Download the latest `NullTerminal-Setup.exe` from the [Releases](https://github.com/starhound/null/releases) page.
    2. Run the installer and follow the instructions.
    3. Open PowerShell or Command Prompt and type `null`.

    #### Portable Version
    1. Download `NullTerminal-Windows.zip` from the Releases page.
    2. Extract it to your preferred location.
    3. Run `null.exe` directly.

    !!! info "PATH Refresh"
        If the `null` command is not recognized after installation, try restarting your terminal session to refresh the environment variables.

=== "Source"

    Installing from source is best for developers or those who want the latest features before they hit a stable release.

    1. **Clone the repository**:
       ```bash
       git clone https://github.com/starhound/null.git
       cd null
       ```
    2. **Install dependencies**:
       We recommend using [`uv`](https://github.com/astral-sh/uv) for lightning-fast environment management.
       ```bash
       pip install uv
       uv sync
       ```
    3. **Run**:
       ```bash
       uv run main.py
       ```

---

## Post-Installation

Once installed, follow these steps to complete your setup:

1.  **Configure AI Providers**: Open the settings with `F3` or type `/settings`.
2.  **Select a Model**: Use `F2` or type `/model` to choose your preferred AI model.
3.  **Toggle AI Mode**: Press `Ctrl+Space` to switch between standard CLI and AI-assisted modes.

## Troubleshooting

### "Command not found: null"
*   **Linux/macOS**: Ensure `~/.local/bin` is in your `$PATH`. If you used `pipx`, run `pipx ensurepath`.
*   **Windows**: Restart your terminal or computer to ensure the PATH changes take effect.

### Terminal Compatibility
Null Terminal works best in modern terminals that support:
*   **TrueColor (24-bit)**: For accurate theme rendering.
*   **Unicode/Emoji**: For icons and UI elements.
*   **Mouse Interaction**: For scrolling and clicking UI components.

Recommended terminals: **WezTerm**, **Kitty**, **Alacritty**, or **Windows Terminal**.
