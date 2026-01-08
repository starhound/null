# Installation Guide

Null Terminal runs on Linux, macOS, and Windows.

## 🪟 Windows Installation

### 1. EXE Installer (Recommended)
The easiest way to install Null Terminal on Windows is using the official installer.

1.  Go to the [**Releases**](https://github.com/starhound/null/releases) page.
2.  Download the latest `NullTerminal-Setup.exe`.
3.  Run the installer and follow the on-screen instructions.
4.  Once installed, open a command prompt (cmd or PowerShell) and type:
    ```powershell
    null
    ```

### 2. Standalone Zip
If you prefer a portable version:
1. Download `NullTerminal-Windows.zip` from Releases.
2. Extract it to a folder of your choice.
3. Run `null.exe` directly from that folder.

## 🐧 Linux & 🍎 macOS Installation

### 1. Via pipx (Recommended)
`pipx` installs Null Terminal in an isolated environment, preventing conflicts with other Python packages.

**Prerequisites:** Python 3.10+

```bash
# Install pipx if you haven't already
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install Null Terminal
pipx install null-terminal

# Run
null
```

### 2. From Source
For developers or those who want the latest "bleeding edge" version.

```bash
# Clone the repository
git clone https://github.com/starhound/null.git
cd null

# Install dependencies using uv (fast!)
pip install uv
uv sync

# Run from source
uv run main.py
```

## 🐳 Docker

You can run Null Terminal directly from a Docker container.

```bash
# Build the image
docker build -t null-terminal .

# Run the container
docker run -it --rm \
  -v $(pwd)/config:/root/.null \
  null-terminal
```
*Note: Persist data (config, keys, history) by mounting the `/root/.null` volume.*

## Troubleshooting

### "Command not found: null"
- **pipx:** Ensure `~/.local/bin` is in your PATH. Run `pipx ensurepath`.
- **Windows:** Restart your terminal after installation to refresh the PATH.

### Python Version Support
Null Terminal requires Python 3.10 or higher.
```bash
python3 --version
```
