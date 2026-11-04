#!/usr/bin/env bash
# Render each README workflow view with fixed palettes and an adaptive SVG.
set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
resolver="$repository_root/skills/workflow-artifact-naming/scripts/resolve_artifact_names.py"

command -v dot >/dev/null || { printf 'Graphviz dot is required.\n' >&2; exit 1; }
command -v python3 >/dev/null || { printf 'Python 3.8+ is required.\n' >&2; exit 1; }

resolve_path() {
  python3 "$resolver" --repository-root "$repository_root" \
    --title "$diagram_title" --type DIAGRAM --destination docs/diagrams "$@" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["absolute_path"])'
}

for diagram_title in 'Investigation Workflow' 'Investigation Skill Routing'; do
source_path="$(resolve_path --extension dot)"
[[ ! -L "$source_path" ]] || { printf 'Refusing symlink source: %s\n' "$source_path" >&2; exit 1; }
test -f "$source_path" || { printf 'Missing canonical diagram: %s\n' "$source_path" >&2; exit 1; }

for theme in light dark; do
  if [[ "$theme" == light ]]; then
    canvas='#ffffff'
    text_color='#0f172a'
    outline='#6366f1'
    arrow='#475569'
    action='#0e7490'
  else
    canvas='#0f172a'
    text_color='#f1f5f9'
    outline='#a5b4fc'
    arrow='#94a3b8'
    action='#67e8f9'
  fi
  for format in svg png; do
    output_path="$(resolve_path --extension "$format" --suffix "$theme")"
    [[ ! -L "$output_path" ]] || { printf 'Refusing symlink output: %s\n' "$output_path" >&2; exit 1; }
    dot -Gbgcolor="$canvas" -Gfontcolor="$text_color" -Gdpi=144 \
      -Nfontcolor="$text_color" -Ncolor="$outline" \
      -Ecolor="$arrow" -Efontcolor="$action" \
      -T"$format" "$source_path" -o "$output_path"
    printf 'Rendered %s\n' "${output_path#"$repository_root/"}"
  done
done

adaptive_path="$(resolve_path --extension svg)"
[[ ! -L "$adaptive_path" ]] || { printf 'Refusing symlink output: %s\n' "$adaptive_path" >&2; exit 1; }
python3 - "$(resolve_path --extension svg --suffix light)" \
  "$(resolve_path --extension svg --suffix dark)" "$adaptive_path" <<'PY'
import sys
import xml.etree.ElementTree as ET

namespace = "http://www.w3.org/2000/svg"
ET.register_namespace("", namespace)
light = ET.parse(sys.argv[1])
dark = ET.parse(sys.argv[2])
light_elements, dark_elements = list(light.getroot().iter()), list(dark.getroot().iter())
if len(light_elements) != len(dark_elements):
    raise SystemExit("Light and dark SVG structures differ")
colors = {}
for left, right in zip(light_elements, dark_elements):
    if left.tag != right.tag or left.text != right.text or left.attrib.keys() != right.attrib.keys():
        raise SystemExit("Light and dark SVG content differs")
    for attribute, value in left.attrib.items():
        replacement = right.attrib[attribute]
        if value == replacement:
            continue
        if attribute not in ("fill", "stroke") or not value.startswith("#") or not replacement.startswith("#"):
            raise SystemExit("Light and dark SVG geometry differs")
        key = (attribute, value)
        if key in colors and colors[key] != replacement:
            raise SystemExit("Conflicting dark palette mapping")
        colors[key] = replacement

style = ET.Element(f"{{{namespace}}}style")
rules = [f'  [{attribute}="{value}"] {{ {attribute}: {replacement}; }}'
         for (attribute, value), replacement in sorted(colors.items())]
style.text = "\n@media (prefers-color-scheme: dark) {\n" + "\n".join(rules) + "\n}\n"
light.getroot().insert(0, style)
light.write(sys.argv[3], encoding="utf-8", xml_declaration=True)
PY
printf 'Rendered %s\n' "${adaptive_path#"$repository_root/"}"

python3 "$repository_root/skills/diagramming-style/scripts/check_diagram_overlaps.py" \
  "$(resolve_path --extension svg --suffix light)" \
  "$(resolve_path --extension svg --suffix dark)"
done
