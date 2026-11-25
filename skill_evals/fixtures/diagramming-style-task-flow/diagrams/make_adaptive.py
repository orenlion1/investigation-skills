"""Builds the adaptive SVG from the light export by remapping light colors in dark mode."""
import sys

LIGHT_TO_DARK = {
    "#ffffff": "#0f172a",
    "#fffde7": "#374151",
    "#ececff": "#1e293b",
    "#111827": "#f1f5f9",
    "#4b5563": "#94a3b8",
    "#6366f1": "#a5b4fc",
    "#0e7490": "#a5f3fc",
}


def main(source, target):
    text = open(source, encoding="utf-8").read()
    rules = []
    for light, dark in LIGHT_TO_DARK.items():
        rules.append(f'[fill="{light}"]{{fill:{dark}}}')
        rules.append(f'[stroke="{light}"]{{stroke:{dark}}}')
    style = "<style>@media (prefers-color-scheme: dark){" + "".join(rules) + "}</style>"
    head, sep, tail = text.partition(">\n<g id=\"graph0\"")
    if not sep:
        raise SystemExit("unexpected SVG layout")
    open(target, "w", encoding="utf-8").write(head + ">\n" + style + "\n<g id=\"graph0\"" + tail)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
