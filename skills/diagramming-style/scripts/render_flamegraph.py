#!/usr/bin/env python3
"""Render paired SVG flame graphs from a saved Pyroscope names/levels profile (stdlib only)."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)


def integer(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('profile weights and indices must be integers')
    return int(value)


def decode(data):
    """Decode per-level gap/total/self/name-index tuples, validating the saved tree."""
    if not isinstance(data, dict):
        raise ValueError('profile must be a JSON object')
    graph = data.get('flamegraph', data)
    if not isinstance(graph, dict):
        raise ValueError('flamegraph must be a JSON object')
    names, levels = graph['names'], graph['levels']
    if not isinstance(names, list) or not isinstance(levels, list):
        raise ValueError('names and levels must be native JSON arrays')
    total = integer(graph['total'])
    if total <= 0 or not levels or not names or not all(isinstance(n, str) for n in names):
        raise ValueError('a nonempty sampled profile and names table are required')
    frames, parents = [], []
    for depth, level in enumerate(levels):
        if not isinstance(level, dict) or not isinstance(level.get('values'), list):
            raise ValueError('each level must contain a values array')
        values = level['values']
        if len(values) % 4:
            raise ValueError('each level must contain gap/total/self/name-index tuples')
        row, x, parent = [], 0, 0
        children = [0] * len(parents)
        for offset in range(0, len(values), 4):
            gap, width, own, index = map(integer, values[offset:offset + 4])
            x += gap
            if gap < 0 or width <= 0 or not 0 <= own <= width or x + width > total:
                raise ValueError('invalid frame offset or inclusive/self weight')
            if not 0 <= index < len(names):
                raise ValueError('frame name index is outside the names table')
            if depth:
                while parent < len(parents) and x >= parents[parent]['x'] + parents[parent]['total']:
                    parent += 1
                if (parent == len(parents) or x < parents[parent]['x'] or
                        x + width > parents[parent]['x'] + parents[parent]['total']):
                    raise ValueError('child frame lies outside its saved parent')
                children[parent] += width
            row.append({'x': x, 'total': width, 'self': own, 'name': names[index], 'depth': depth})
            x += width
        if depth and any(weight + p['self'] > p['total'] for weight, p in zip(children, parents)):
            raise ValueError('children plus self exceed the parent inclusive weight')
        if depth == 0 and (len(row) != 1 or row[0]['x'] != 0 or row[0]['total'] != total):
            raise ValueError('one root matching the profile total is required')
        frames.extend(row)
        parents = row
    return frames, total


def render(data, theme, focus=None, max_depth=16):
    """Keep source geometry and whole-profile percentages in both themes, including focus views."""
    frames, total = decode(data)
    if theme not in ('light', 'dark') or max_depth < 1:
        raise ValueError('use light/dark theme and a positive depth limit')
    matches = [f for f in frames if f['name'] == focus] if focus else frames[:1]
    if len(matches) != 1:
        raise ValueError('focus must identify exactly one saved frame; use a full view otherwise')
    root = matches[0]
    subtree = [f for f in frames if f['depth'] >= root['depth'] and
               root['x'] <= f['x'] and f['x'] + f['total'] <= root['x'] + root['total']]
    shown = [f for f in subtree if f['depth'] - root['depth'] < max_depth]
    depth_count = max(f['depth'] - root['depth'] for f in shown) + 1
    width, row, margin = 900, 36, 12
    height = depth_count * row + margin * 2
    bg, fg, fill = ('#ffffff', '#0f172a', '#fed7aa') if theme == 'light' else ('#0f172a', '#f1f5f9', '#7c2d12')
    svg = ET.Element(f'{{{SVG}}}svg', {'width': str(width), 'height': str(height),
                                    'viewBox': f'0 0 {width} {height}', 'role': 'img',
                                    'aria-labelledby': 'flame-title'})
    ET.SubElement(svg, f'{{{SVG}}}title', {'id': 'flame-title'}).text = 'Sampled profile flame graph'
    ET.SubElement(svg, f'{{{SVG}}}rect', {'width': str(width), 'height': str(height), 'fill': bg})
    scale = (width - margin * 2) / root['total']
    definitions = ET.SubElement(svg, f'{{{SVG}}}defs')
    for index, frame in enumerate(shown):
        x = margin + (frame['x'] - root['x']) * scale
        w = frame['total'] * scale
        y = margin + (depth_count - 1 - frame['depth'] + root['depth']) * row
        attrs = {'x': f'{x:.8g}', 'y': str(y), 'width': f'{w:.8g}', 'height': str(row - 2),
                 'fill': fill, 'stroke': bg, 'data-name': frame['name'],
                 'data-total': str(frame['total']), 'data-self': str(frame['self'])}
        rect = ET.SubElement(svg, f'{{{SVG}}}rect', attrs)
        share = frame['total'] / total * 100
        ET.SubElement(rect, f'{{{SVG}}}title').text = (
            f"{frame['name']}: {share:.2f}% inclusive; {frame['self'] / total * 100:.2f}% self (whole profile)")
        name = frame['name'].rsplit('/', 1)[-1]
        suffix = f' {share:.2f}%'
        capacity = int((w - 8) / 10.5)
        if capacity >= len(suffix) + 4:
            if len(name) + len(suffix) > capacity:
                name = name[:capacity - len(suffix) - 3] + '...'
            label = name + suffix
            clip = ET.SubElement(definitions, f'{{{SVG}}}clipPath', {'id': f'frame-{index}'})
            ET.SubElement(clip, f'{{{SVG}}}rect', {'x': f'{x + 3:.8g}', 'y': str(y),
                          'width': f'{max(0, w - 6):.8g}', 'height': str(row - 2)})
            ET.SubElement(svg, f'{{{SVG}}}text', {'x': f'{x + 4:.8g}', 'y': str(y + 24),
                          'clip-path': f'url(#frame-{index})',
                          'fill': fg, 'font-size': '18',
                          'font-family': 'Trebuchet MS, Arial, sans-serif'}).text = label
    metadata = {'profile_total': total, 'percentage_denominator': total, 'focus': focus,
                'focus_share_percent': root['total'] / total * 100,
                'displayed_frames': len(shown), 'omitted_descendant_frames': len(subtree) - len(shown),
                'max_depth': max_depth}
    content = ET.tostring(svg, encoding='utf-8', xml_declaration=True)
    ET.fromstring(content)  # Reject invalid XML characters before either output is created.
    return content, metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--light', type=Path, required=True)
    parser.add_argument('--dark', type=Path, required=True)
    parser.add_argument('--focus', help='exact, unique saved frame name; width is normalized to this subtree')
    parser.add_argument('--max-depth', type=int, default=16)
    args = parser.parse_args(argv)
    try:
        outputs = [args.light, args.dark]
        if args.light.resolve() == args.dark.resolve() or any(p.exists() or p.is_symlink() for p in outputs):
            raise ValueError('light and dark outputs must be distinct new files')
        raw = args.input.read_bytes()
        data = json.loads(raw)
        rendered = [render(data, theme, args.focus, args.max_depth) for theme in ['light', 'dark']]
        for path, (content, _) in zip(outputs, rendered):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as handle:
                handle.write(content)
        print(json.dumps({**rendered[0][1], 'source_sha256': hashlib.sha256(raw).hexdigest()}))
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as error:
        parser.exit(1, f'error: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
