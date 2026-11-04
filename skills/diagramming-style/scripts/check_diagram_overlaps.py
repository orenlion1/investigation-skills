#!/usr/bin/env python3
"""Check rendered Graphviz SVG diagrams for overlap and spacing defects.

Validates the Diagramming Style skill's edge-length and overlap rules on the
actual render: labels must keep clear of edge lines, arrowheads and endpoint
marks, and shape outlines; shapes must not collide; endpoint marks must not
penetrate node outlines; and edges must have enough run for their notation.

Scope and limits (also documented in the skill):
- Designed for Graphviz `dot -Tsvg` output, whose groups carry class="node"
  and class="edge". Other SVGs (for example Mermaid) use nested transforms
  and foreignObject labels this parser does not model; the script exits with
  an error rather than guessing.
- Text extents are estimated from font size and character count, so results
  are approximate. A pass supplements the skill's required visual inspection
  in both themes; it never replaces it.

Usage:
  python3 check_diagram_overlaps.py one.svg [more.svg ...] [options]

Exit status: 0 all checks passed, 1 violations found, 2 usage/parse error.

Stdlib only; no third-party dependencies.
"""

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET

ASCENT = 0.78   # fraction of font size above the text baseline
DESCENT = 0.22  # fraction of font size below the text baseline


def local_name(tag):
    return tag.rsplit('}', 1)[-1]


class Box:
    __slots__ = ('x0', 'y0', 'x1', 'y1')

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = min(x0, x1), min(y0, y1)
        self.x1, self.y1 = max(x0, x1), max(y0, y1)

    def inflate(self, amount):
        return Box(self.x0 - amount, self.y0 - amount,
                   self.x1 + amount, self.y1 + amount)

    def intersects(self, other):
        return (self.x0 < other.x1 and other.x0 < self.x1 and
                self.y0 < other.y1 and other.y0 < self.y1)

    def penetration(self, other):
        """Depth of mutual overlap in px; 0.0 when merely touching or apart."""
        dx = min(self.x1, other.x1) - max(self.x0, other.x0)
        dy = min(self.y1, other.y1) - max(self.y0, other.y0)
        if dx <= 0 or dy <= 0:
            return 0.0
        return min(dx, dy)

    def contains_point(self, x, y):
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def __repr__(self):
        return f'({self.x0:.1f},{self.y0:.1f})-({self.x1:.1f},{self.y1:.1f})'


def parse_points(value):
    pts = []
    for pair in value.replace(',', ' ').split():
        pts.append(float(pair))
    return list(zip(pts[0::2], pts[1::2]))


_PATH_TOKEN = re.compile(r'([MLCml])|(-?\d*\.?\d+(?:e-?\d+)?)')


def sample_path(d, step=3.0):
    """Sample an absolute M/L/C SVG path into a polyline, ~`step` px apart."""
    tokens = _PATH_TOKEN.findall(d)
    nums, cmds = [], []
    seq = []
    for cmd, num in tokens:
        if cmd:
            seq.append(('cmd', cmd.upper()))
        else:
            seq.append(('num', float(num)))
    pts = []
    i = 0
    current = None
    command = None
    while i < len(seq):
        kind, value = seq[i]
        if kind == 'cmd':
            command = value
            i += 1
            continue
        if command == 'M' or command == 'L':
            x, y = seq[i][1], seq[i + 1][1]
            i += 2
            if command == 'M' and current is None:
                pts.append((x, y))
            else:
                pts.extend(_interpolate(current, (x, y), step))
            current = (x, y)
            if command == 'M':
                command = 'L'
        elif command == 'C':
            p1 = (seq[i][1], seq[i + 1][1])
            p2 = (seq[i + 2][1], seq[i + 3][1])
            p3 = (seq[i + 4][1], seq[i + 5][1])
            i += 6
            pts.extend(_sample_cubic(current, p1, p2, p3, step))
            current = p3
        else:
            i += 1  # unsupported command content; skip defensively
    return pts


def _interpolate(a, b, step):
    if a is None:
        return [b]
    dist = math.hypot(b[0] - a[0], b[1] - a[1])
    n = max(1, int(dist / step))
    return [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n)
            for t in range(1, n + 1)]


def _sample_cubic(p0, p1, p2, p3, step):
    approx = (math.hypot(p1[0] - p0[0], p1[1] - p0[1]) +
              math.hypot(p2[0] - p1[0], p2[1] - p1[1]) +
              math.hypot(p3[0] - p2[0], p3[1] - p2[1]))
    n = max(2, int(approx / step))
    out = []
    for k in range(1, n + 1):
        t = k / n
        u = 1 - t
        x = (u ** 3 * p0[0] + 3 * u * u * t * p1[0] +
             3 * u * t * t * p2[0] + t ** 3 * p3[0])
        y = (u ** 3 * p0[1] + 3 * u * u * t * p1[1] +
             3 * u * t * t * p2[1] + t ** 3 * p3[1])
        out.append((x, y))
    return out


def polyline_length(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(pts, pts[1:]))


def text_box(element, char_width_ratio):
    content = ''.join(element.itertext())
    if not content.strip():
        return None
    x = float(element.get('x', '0'))
    y = float(element.get('y', '0'))
    size = float(element.get('font-size', '14'))
    anchor = element.get('text-anchor', 'start')
    full = len(content) * size * char_width_ratio
    if anchor == 'middle':
        left, right = x - full / 2, x + full / 2
    elif anchor == 'end':
        left, right = x - full, x
    else:
        left, right = x, x + full
    # Trim the estimate for leading/trailing spaces used as label offsets.
    lead = len(content) - len(content.lstrip())
    trail = len(content) - len(content.rstrip())
    left += lead * size * char_width_ratio
    right -= trail * size * char_width_ratio
    return {'box': Box(left, y - ASCENT * size, right, y + DESCENT * size),
            'text': content.strip()}


def shape_box(element):
    name = local_name(element.tag)
    if name == 'polygon':
        pts = parse_points(element.get('points', ''))
        if not pts:
            return None
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return Box(min(xs), min(ys), max(xs), max(ys))
    if name == 'ellipse':
        cx, cy = float(element.get('cx', '0')), float(element.get('cy', '0'))
        rx, ry = float(element.get('rx', '0')), float(element.get('ry', '0'))
        return Box(cx - rx, cy - ry, cx + rx, cy + ry)
    if name == 'rect':
        x, y = float(element.get('x', '0')), float(element.get('y', '0'))
        w, h = float(element.get('width', '0')), float(element.get('height', '0'))
        return Box(x, y, x + w, y + h)
    return None


def is_invisible(element):
    return (element.get('stroke') == 'none' and
            element.get('fill', 'none') in ('none', 'transparent'))


def parse_groups(svg_path, char_width_ratio):
    tree = ET.parse(svg_path)
    root = tree.getroot()
    groups = []
    graph_group = None
    for g in root.iter():
        if local_name(g.tag) != 'g':
            continue
        cls = g.get('class', '')
        if 'graph' in cls.split():
            graph_group = g
            continue
        kind = ('node' if 'node' in cls.split()
                else 'edge' if 'edge' in cls.split() else None)
        if kind is None:
            continue
        title = ''
        entry = {'kind': kind, 'id': g.get('id', ''), 'title': title,
                 'endpoints': set(), 'texts': [], 'shapes': [], 'paths': [],
                 'marks': []}
        for child in g.iter():
            name = local_name(child.tag)
            if name == 'title':
                entry['title'] = (child.text or '').strip()
                if kind == 'edge':
                    entry['endpoints'] = set(
                        part.strip()
                        for part in re.split(r'->|--', entry['title'])
                        if part.strip())
            elif name == 'text':
                tb = text_box(child, char_width_ratio)
                if tb:
                    entry['texts'].append(tb)
            elif name == 'path':
                d = child.get('d')
                if d and not is_invisible(child):
                    pts = sample_path(d)
                    if pts:
                        entry['paths'].append(pts)
            elif name in ('polygon', 'ellipse', 'rect'):
                box = shape_box(child)
                if box is None or is_invisible(child):
                    continue
                if kind == 'edge':
                    entry['marks'].append(box)
                else:
                    entry['shapes'].append(box)
        groups.append(entry)
    # The graph title is checked like any other label.
    if graph_group is not None:
        entry = {'kind': 'title', 'id': 'graph-title', 'title': 'graph title',
                 'endpoints': set(), 'texts': [], 'shapes': [], 'paths': [],
                 'marks': []}
        for child in list(graph_group):
            if local_name(child.tag) == 'text':
                tb = text_box(child, char_width_ratio)
                if tb:
                    entry['texts'].append(tb)
        if entry['texts']:
            groups.append(entry)
    if not any(g['kind'] in ('node', 'edge') for g in groups):
        raise ValueError(
            f'{svg_path}: no Graphviz node/edge groups found; this checker '
            'supports Graphviz -Tsvg output (see module docstring)')
    return groups


def label_for(group, item_text=None):
    base = group['title'] or group['id'] or group['kind']
    if item_text:
        return f'{group["kind"]} {base} text "{item_text}"'
    return f'{group["kind"]} {base}'


def attached(text_group, edge_group):
    """True when the text's group legitimately meets the edge.

    An edge necessarily runs up to its endpoint nodes; with plain-label
    styling the node's text is that attachment boundary. The edge's own
    label also sits beside its own line by construction. For these pairs
    only actual penetration counts; for every other pair the clearance
    distance applies.
    """
    if text_group is edge_group:
        return True
    return (text_group['kind'] == 'node' and edge_group['kind'] == 'edge'
            and text_group['title'] in edge_group['endpoints'])


def check_groups(groups, clearance, min_edge_run, touch_tolerance):
    violations = []

    def add(vtype, detail, measure):
        violations.append({'type': vtype, 'detail': detail,
                           'measure_px': round(measure, 2)})

    texts = [(g, t) for g in groups for t in g['texts']]
    shapes = [(g, s) for g in groups for s in g['shapes']]
    paths = [(g, p) for g in groups for p in g['paths']]
    marks = [(g, m) for g in groups for m in g['marks']]

    # 1. Labels must keep `clearance` px from every edge line. Where the
    #    pair is attached by construction, flag only genuine penetration.
    for tg, tb in texts:
        inflated = tb['box'].inflate(clearance)
        for pg, pts in paths:
            if attached(tg, pg):
                depth = max((_point_depth(p, tb['box']) for p in pts
                             if tb['box'].contains_point(*p)), default=0.0)
                if depth > touch_tolerance:
                    add('label_line_overlap',
                        f'line of {label_for(pg)} crosses '
                        f'{label_for(tg, tb["text"])}', depth)
                continue
            hit = [p for p in pts if inflated.contains_point(*p)]
            if hit:
                add('label_line_overlap',
                    f'{label_for(tg, tb["text"])} within {clearance}px of '
                    f'line of {label_for(pg)}',
                    min(_point_box_distance(p, tb['box']) for p in hit))

    # 2. Labels must keep clear of arrowheads and endpoint marks, with the
    #    same attachment allowance.
    for tg, tb in texts:
        inflated = tb['box'].inflate(clearance)
        for mg, mb in marks:
            if attached(tg, mg):
                if tb['box'].penetration(mb) > touch_tolerance:
                    add('label_mark_overlap',
                        f'arrow/endpoint mark of {label_for(mg)} overlaps '
                        f'{label_for(tg, tb["text"])}',
                        tb['box'].penetration(mb))
                continue
            if inflated.intersects(mb):
                add('label_mark_overlap',
                    f'{label_for(tg, tb["text"])} within {clearance}px of '
                    f'arrow/endpoint mark of {label_for(mg)}',
                    tb['box'].penetration(mb))

    # 3. Labels must keep clear of other groups' shape outlines.
    for tg, tb in texts:
        inflated = tb['box'].inflate(clearance)
        for sg, sb in shapes:
            if sg is tg:
                continue  # a node's own text sits inside its own outline
            if inflated.intersects(sb):
                add('label_shape_overlap',
                    f'{label_for(tg, tb["text"])} within {clearance}px of '
                    f'outline of {label_for(sg)}',
                    tb['box'].penetration(sb))

    # 4. Labels from different groups must not collide with each other.
    #    A node's text and the label of an edge attached to that node sit
    #    close by construction; genuine penetration still counts.
    for i, (ag, atb) in enumerate(texts):
        for bg, btb in texts[i + 1:]:
            if ag is bg:
                continue
            exempt = attached(ag, bg) or attached(bg, ag)
            pen = atb['box'].penetration(btb['box'])
            if exempt:
                if pen > touch_tolerance:
                    add('label_label_overlap',
                        f'{label_for(ag, atb["text"])} overlaps '
                        f'{label_for(bg, btb["text"])}', pen)
            elif atb['box'].inflate(clearance).intersects(btb['box']):
                add('label_label_overlap',
                    f'{label_for(ag, atb["text"])} within {clearance}px of '
                    f'{label_for(bg, btb["text"])}', pen)

    # 5. Shape outlines must not collide (touching is already too close).
    for i, (ag, ab) in enumerate(shapes):
        for bg, bb in shapes[i + 1:]:
            if ag is bg:
                continue
            pen = ab.penetration(bb)
            if pen > touch_tolerance:
                add('shape_shape_overlap',
                    f'outline of {label_for(ag)} overlaps outline of '
                    f'{label_for(bg)}', pen)

    # 6. Arrowheads/endpoint marks may touch, but not penetrate, outlines.
    for mg, mb in marks:
        for sg, sb in shapes:
            pen = mb.penetration(sb)
            if pen > touch_tolerance:
                add('mark_shape_penetration',
                    f'arrow/endpoint mark of {label_for(mg)} penetrates '
                    f'outline of {label_for(sg)}', pen)

    # 7. Edges need enough run for their notation: the line must be at
    #    least MARK_RUN_FACTOR times the along-edge extent of its own
    #    arrowheads and endpoint marks, and never below the bare floor.
    for g in groups:
        if g['kind'] != 'edge' or not g['paths']:
            continue
        run = sum(polyline_length(p) for p in g['paths'])
        required = max(min_edge_run,
                       _marks_extent(g) * MARK_RUN_FACTOR + 2 * clearance)
        if run < required:
            add('short_edge',
                f'{label_for(g)} run {run:.1f}px is below the required '
                f'{required:.1f}px for its notation', run)

    return violations


MARK_RUN_FACTOR = 1.0


def _marks_extent(edge_group):
    """Along-edge extent of the edge's arrowheads and endpoint marks.

    Each mark's bounding box is projected onto the edge's end-to-end axis
    and the projection intervals are merged, so stacked marks that share
    the same stretch of the edge are not double-counted.
    """
    pts = [p for path in edge_group['paths'] for p in path]
    if len(pts) >= 2:
        dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
    else:
        ux, uy = 1.0, 0.0
    intervals = []
    for mark in edge_group['marks']:
        corners = ((mark.x0, mark.y0), (mark.x0, mark.y1),
                   (mark.x1, mark.y0), (mark.x1, mark.y1))
        ts = [c[0] * ux + c[1] * uy for c in corners]
        intervals.append((min(ts), max(ts)))
    intervals.sort()
    extent, cursor = 0.0, None
    for start, end in intervals:
        if cursor is None or start > cursor:
            extent += end - start
            cursor = end
        elif end > cursor:
            extent += end - cursor
            cursor = end
    return extent


def _point_box_distance(point, box):
    dx = max(box.x0 - point[0], 0, point[0] - box.x1)
    dy = max(box.y0 - point[1], 0, point[1] - box.y1)
    return math.hypot(dx, dy)


def _point_depth(point, box):
    """How far inside `box` the point sits; 0.0 on or outside the border."""
    if not box.contains_point(*point):
        return 0.0
    return min(point[0] - box.x0, box.x1 - point[0],
               point[1] - box.y0, box.y1 - point[1])


def check_file(svg_path, args):
    groups = parse_groups(svg_path, args.char_width_ratio)
    return check_groups(groups, args.clearance, args.min_edge_run,
                        args.touch_tolerance)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('svgs', nargs='+', help='Graphviz SVG files to check')
    parser.add_argument('--clearance', type=float, default=2.0,
                        help='minimum px between labels and lines, marks, '
                             'shapes, and other labels (default 2.0)')
    parser.add_argument('--min-edge-run', type=float, default=12.0,
                        help='bare minimum sampled edge length in px; edges '
                             'carrying notation additionally need '
                             f'{MARK_RUN_FACTOR}x their marks\' along-edge '
                             'extent (default 12)')
    parser.add_argument('--touch-tolerance', type=float, default=1.0,
                        help='allowed px of boundary contact for attached '
                             'elements (default 1.0)')
    parser.add_argument('--char-width-ratio', type=float, default=0.48,
                        help='estimated glyph width as a fraction of font '
                             'size, calibrated for Trebuchet MS/Arial mixed '
                             'case (default 0.48)')
    parser.add_argument('--json', action='store_true',
                        help='emit a JSON report instead of text')
    args = parser.parse_args(argv)

    report = {}
    failed = False
    for svg in args.svgs:
        try:
            violations = check_file(svg, args)
        except (ET.ParseError, ValueError, OSError) as error:
            print(f'error: {error}', file=sys.stderr)
            return 2
        report[svg] = violations
        failed = failed or bool(violations)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for svg, violations in report.items():
            status = 'FAIL' if violations else 'ok'
            print(f'{status}  {svg}')
            for v in violations:
                print(f'      {v["type"]}: {v["detail"]} '
                      f'[{v["measure_px"]}px]')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
