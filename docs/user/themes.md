# Themes

Customize the appearance of Null Terminal with built-in or custom themes.

## Changing Themes

### Via Command
```bash
/theme              # Open theme selector
/theme null-warm    # Set theme directly
```

### Via Shortcut
Press `F3` to open theme selector.

### Via Settings
`/config` → Appearance → Theme

## Built-in Themes

### null-dark (Default)
Dark theme with soft blue accents. Easy on the eyes for extended use.

### null-warm
Warm variant with orange/amber accents. Comfortable in low-light environments.

### null-mono
Minimal monochrome with subtle blue tints. Maximum focus, minimal distraction.

### null-light
Light theme for daytime use or well-lit environments.

## Custom Themes

Create custom themes in `~/.null/themes/` as JSON files.

### Theme Structure

```json
{
  "name": "my-custom-theme",
  "dark": true,
  "primary": "#7aa2f7",
  "secondary": "#bb9af7",
  "accent": "#7dcfff",
  "foreground": "#c0caf5",
  "background": "#1a1b26",
  "surface": "#24283b",
  "panel": "#1f2335",
  "success": "#9ece6a",
  "warning": "#e0af68",
  "error": "#f7768e",
  "boost": "#ff9e64",
  "luminosity_spread": 0.15,
  "text_alpha": 0.95
}
```

### Color Properties

| Property | Description |
|----------|-------------|
| `name` | Theme identifier |
| `dark` | `true` for dark themes, `false` for light |
| `primary` | Primary accent color (buttons, highlights) |
| `secondary` | Secondary accent (headings, labels) |
| `accent` | Tertiary accent (links, focus) |
| `foreground` | Main text color |
| `background` | Main background |
| `surface` | Elevated surface (cards, dialogs) |
| `panel` | Panel/sidebar background |
| `success` | Success messages, CLI prompt |
| `warning` | Warnings, pending states |
| `error` | Errors, cancel actions |
| `boost` | Emphasis, important items |

### Optional Properties

| Property | Default | Description |
|----------|---------|-------------|
| `luminosity_spread` | `0.15` | Color variation range |
| `text_alpha` | `0.95` | Text opacity |

### Example: Tokyo Night

```json
{
  "name": "tokyo-night",
  "dark": true,
  "primary": "#7aa2f7",
  "secondary": "#bb9af7",
  "accent": "#7dcfff",
  "foreground": "#c0caf5",
  "background": "#1a1b26",
  "surface": "#24283b",
  "panel": "#1f2335",
  "success": "#9ece6a",
  "warning": "#e0af68",
  "error": "#f7768e"
}
```

### Example: Catppuccin Mocha

```json
{
  "name": "catppuccin-mocha",
  "dark": true,
  "primary": "#89b4fa",
  "secondary": "#cba6f7",
  "accent": "#94e2d5",
  "foreground": "#cdd6f4",
  "background": "#1e1e2e",
  "surface": "#313244",
  "panel": "#181825",
  "success": "#a6e3a1",
  "warning": "#f9e2af",
  "error": "#f38ba8"
}
```

## Theme Loading

1. Built-in themes load first
2. Custom themes from `~/.null/themes/*.json` loaded on startup
3. Theme preference saved in config
4. Theme applied immediately when changed

## Creating a Theme

1. Copy the example file:
   ```bash
   cp ~/.null/themes/example-custom.json.example ~/.null/themes/my-theme.json
   ```

2. Edit colors in your favorite editor

3. Restart Null Terminal or use `/theme my-theme`

## Color Format

Colors can be specified as:
- Hex: `#7aa2f7` or `#7af`
- Named colors: `blue`, `red`, `green`, etc.

## Tips

- **Contrast**: Ensure `foreground` contrasts well with `background`
- **Consistency**: Keep `surface` and `panel` close to `background`
- **Accessibility**: Test with different types of content
- **Dark vs Light**: Set `dark` appropriately for proper text styling
