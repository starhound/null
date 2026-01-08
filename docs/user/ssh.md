# SSH & Remote Connections

Null Terminal acts as a first-class SSH client, wrapping standard SSH connections in its rich TUI environment.

## ✨ Features
- **Saved Hosts**: Manage frequently accessed servers.
- **Identity Management**: Automatic key forwarding.
- **TUI-over-SSH**: Run remote interactive apps (vim, htop) seamlessly.

## 🖥️ Managing Hosts

### Adding a Host
1. Type `/ssh add` to open the Host Manager.
2. Enter the connection details:
   - **Hostname/IP**: e.g., `192.168.1.50` or `myserver.com`
   - **User**: e.g., `root` or `ubuntu`
   - **Port**: default `22`
   - **Alias**: A friendly name (e.g., "Production DB")

### Connecting
You can connect in two ways:

1. **Directly via Command:**
   ```bash
   /ssh <alias>
   # or
   /ssh user@host
   ```

2. **Via Command Palette:**
   - Press `Ctrl+P`.
   - Select **"SSH: Connect to Host"**.
   - Choose from your list of saved hosts.

## 🔒 Key Management
Null Terminal uses your system's SSH keys (`~/.ssh/id_rsa`, etc.) by default. Ensure your public key is added to the remote server's `~/.ssh/authorized_keys`.

## 🛠️ Deployment via SSH
You can use the `/agent` to perform tasks on remote servers if you have SSH access configured. The agent can pipe commands over the SSH connection (feature in beta).
