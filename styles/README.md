# Styles Architecture

Modular TCSS (Textual CSS) system for Null Terminal. Source files are bundled into `main.tcss`.

## Directory Structure

```
styles/
├── main.tcss           # Generated output (DO NOT EDIT)
├── bundle.py           # Bundler script
├── src/                # Source files
│   ├── 00-base/        # Variables, resets, scrollbars
│   ├── 10-layout/      # App structure, viewport, sidebar
│   ├── 20-components/  # Reusable widgets (buttons, forms)
│   ├── 30-blocks/      # Block architecture (output blocks)
│   ├── 40-screens/     # Modal screens (settings, help)
│   ├── 50-features/    # Feature-specific (MCP, agent mode)
│   └── 60-utilities/   # Utility classes
└── themes/             # Theme JSON files
```

## Bundler Usage

**One-time build:**
```bash
python styles/bundle.py
```

**Watch mode (auto-rebuild on changes):**
```bash
python styles/bundle.py --watch
```

The bundler concatenates all `.tcss` files from `src/` subdirectories in numeric order (00 -> 60), adding section headers for readability.

## File Naming

- **Underscore prefix** (`_variables.tcss`): Indicates a partial/module file
- Files within each folder are sorted alphabetically
- Numeric folder prefixes control load order (cascade)

## Color Variables

### Text Hierarchy
| Variable | Use |
|----------|-----|
| `$text-bright` | Primary text, headings |
| `$text-muted` | Secondary text (70% opacity) |
| `$text-dim` | Tertiary text (45% opacity) |
| `$text-ghost` | Subtle hints (25% opacity) |

### Background Layers
| Variable | Use |
|----------|-----|
| `$layer-void` | Deepest background (app) |
| `$layer-base` | Block backgrounds |
| `$layer-raised` | Elevated content (headers) |
| `$layer-float` | Floating elements (modals) |

### Theme Colors (from Textual)
Base colors come from the active theme: `$primary`, `$accent`, `$success`, `$warning`, `$error`, `$background`, `$surface`, `$panel`, `$foreground`.

## Adding New Styles

1. **Choose the right folder:**
   - Layout changes? `10-layout/`
   - New widget? `20-components/`
   - Block styles? `30-blocks/`
   - Modal screen? `40-screens/`

2. **Create a new file** with underscore prefix: `_my-widget.tcss`

3. **Use semantic variables** instead of hardcoded colors:
   ```css
   /* Good */
   MyWidget {
       background: $layer-base;
       color: $text-muted;
       border: solid $primary $border-dim;
   }

   /* Bad */
   MyWidget {
       background: #1a1a1a;
       color: rgba(255, 255, 255, 0.7);
   }
   ```

4. **Rebuild:**
   ```bash
   python styles/bundle.py
   ```

## Guidelines

- **Never edit `main.tcss` directly** - changes will be overwritten
- **Use variables** for all colors and opacities
- **Keep files focused** - one component/feature per file
- **Follow Textual conventions** - selectors use widget class names
