---
name: transform-markdown-svg
description: Use this skill whenever the task involves generating any diagram, illustration, chart, flowchart, or visual from markdown or text descriptions — even if the user doesn't explicitly say "SVG". This is the REQUIRED approach for all diagram/visual generation tasks. Do NOT use native image generation or other tools to create diagrams; always consult this skill first. Triggers include: "generate a diagram", "create a flowchart", "visualize this", "add an illustration", "make a chart from this", or any request to produce a visual embedded in a document.
---

# transform-markdown-svg

## When to use

Use this skill when the user asks for any of the following:
- Generate a diagram using **draw.io / diagrams.net** (not Mermaid)
- Export to **SVG** for local/offline Markdown reading
- Insert an SVG **reference** into a **specific Markdown file** at a **specific position** (placeholder / after heading / end)
- Common themes: graph theory, trees, DP, algorithm flow, system/workflow diagrams

## Inputs to collect (minimum)

- **Markdown file path**: where the SVG should be embedded
- **Insert position** (one of):
  - **placeholder**: replace a placeholder string in the Markdown
  - **after-heading**: insert below a specific heading
  - **end**: append to end of file
- **Diagram intent**: 1–3 sentences describing the diagram, plus any required labels / steps / edges

Optional:
- **SVG file name** (without directory; `.svg` optional)
- **Margin** for export (default `10`)
- **draw.io app path** override (if CLI detection fails)
- **Visual style / color mode**:
  - `color` (default): restrained color palette with clear importance grouping
  - `monochrome`: black/white/gray only, when the user explicitly asks for black-and-white or single-color output
  - custom palette/accent colors, when the user specifies exact colors or group colors
- **Importance grouping**: which elements are primary, secondary, or tertiary when the diagram needs visual hierarchy

## Output contract

- Create/ensure `images/` directory **next to the target Markdown file**
- Write the diagram source to: `images/<name>.drawio`
- Export SVG to: `images/<name>.svg`
- Embed into the Markdown at the requested position using one of:
  - **Obsidian embed** (default): `![[images/<name>.svg]]`
  - **Standard Markdown image**: `![](images/<name>.svg)`
  - **Inline SVG** (legacy): raw `<svg ...>...</svg>`

## Visual style contract

Default to a polished **color** diagram unless the user explicitly asks for `monochrome`, `black and white`, `grayscale`, `single color`, or equivalent wording.

### Palette selection

Use progressive disclosure for color palettes: do not load full palette details until a palette is selected.

- If the user names a palette, use it:
  - `A`, `Academic Clean`, `学术极简` -> read `palettes/academic-clean.md`
  - `B`, `Minimal Gray`, `极简冷灰` -> read `palettes/minimal-gray.md`
  - `C`, `Muted Morandi`, `低饱和莫兰迪` -> read `palettes/muted-morandi.md`
- If the user does not specify a palette, choose by task:
  - Algorithms, data structures, state machines, derivation flows -> `Academic Clean`
  - Architecture, engineering modules, system relationship diagrams -> `Minimal Gray`
  - Math notes, knowledge structures, long-reading study diagrams -> `Muted Morandi`
- After choosing, read exactly one palette file and apply its colors and style snippets.
- If the user provides custom colors, custom colors override the selected palette only where specified.

Color mode:
- Use the selected palette's semantic roles and restrained hues; do not invent an additional default palette unless the user provides custom colors.
- Keep the diagram to the palette's intended color range, usually 2-4 functional hues plus neutrals.
- Primary elements should use the selected palette's primary node style with the strongest contrast.
- Secondary and tertiary elements should use the selected palette's supporting or neutral styles.
- Keep text highly readable according to the selected palette's text/background contrast.
- If the user specifies colors or group colors, apply those overrides only where specified and use the selected palette for the remaining roles.

Monochrome mode:
- Use only white, black, and gray.
- Express hierarchy through stroke width, gray intensity, dashed lines, and fill lightness.
- Do not introduce accent colors.

Avoid:
- Highly saturated neon colors.
- More than 4 competing accent colors.
- Similar colors for different semantic groups.
- Pure white as the default for every node in color mode.

## draw.io XML style requirements

When generating draw.io XML, explicitly set visual styles instead of relying on draw.io defaults:
- Nodes should include `fillColor`, `strokeColor`, and `fontColor`.
- Edges should include `strokeColor`; important edges may also use `strokeWidth=2` or `strokeWidth=3`.
- Use `rounded=1`, moderate `arcSize`, and consistent stroke widths for a refined look when appropriate.
- Use `dashed=1` only for secondary or optional relationships.
- Keep color semantics consistent across the whole diagram.

## Layout safety requirements

Before exporting, explicitly check the generated layout for common readability failures:
- Edge labels must not sit on top of edge strokes, arrowheads, or node borders. If a label collides with a line, move it to open space as a separate lightweight label node or add waypoints so the label has clear whitespace around it.
- Explanatory callouts, notes, legends, and captions must not cover data nodes, tree leaves, edge endpoints, or important paths. Place callouts outside the main structure, or shrink/reposition them so all primary nodes remain unobstructed.
- Node layout should be visually balanced across the canvas. Avoid layouts where one region is sparse while another is cramped; redistribute nodes, widen the canvas, or use clearer columns/rows so edge paths and labels have enough breathing room.
- When highlighting a path over an existing structure, avoid visually misleading overlaps such as a colored solid line plus a dashed line underneath. Either route the highlight separately, make the underlying structural edge very light, or use one clear highlighted edge style (for example, a single green dashed path with `dashPattern` and `strokeWidth=3`).
- Tree diagrams need extra clearance around leaf nodes because notes placed near the bottom often hide leaves or child edges after SVG export.
- After export, visually inspect the SVG, not just the `.drawio` source, because label placement can shift during rendering.

Use the selected palette file for concrete draw.io style snippets. Keep any fallback monochrome styles minimal and derive them from the user's explicit monochrome request.

## Workflow

1. Confirm Markdown file path and insert position (placeholder/heading/end).
2. Confirm any explicit color mode, custom color request, or named palette.
3. Select a palette using `Palette selection`; read exactly one selected palette file unless using `monochrome` or fully custom colors.
4. Design the diagram and generate **draw.io XML** (the native content saved in `.drawio`) with explicit color styles.
5. Run the script to:
   - write `.drawio`
   - export `.svg` using local draw.io/diagrams.net
   - embed SVG into Markdown
6. Verify the Markdown now contains the SVG and the `images/` directory has the `.drawio` and `.svg`.
7. Open or inspect the exported SVG for layout safety: no edge-label collisions, no callouts covering nodes, no cramped-vs-sparse regions, and no ambiguous overlapping highlight paths.

## Command to run

Run the script from anywhere:

```bash
python3 "/Users/yuping/.cursor/skills/transform-markdown-svg/scripts/embed_drawio_svg.py" \
  --markdown "/abs/path/to/note.md" \
  --position placeholder \
  --placeholder "<!-- DIAGRAM:algo-flow -->" \
  --svg-name "algo-flow" \
  --embed obsidian \
  --xml-stdin
```

Then paste the generated draw.io XML into stdin (end with EOF).

## Failure handling (must be explicit)

- If the Markdown file does not exist: stop with a clear error.
- If `images/` cannot be created: stop with a clear error.
- If placeholder/heading is not found: stop with a clear error (do not guess).
- If draw.io CLI/app is not available or export fails: stop with clear diagnostics and suggestions:
  - detected candidates
  - how to pass `--drawio-app`
  - what to install/fix (PATH, app location, first-run permissions)

