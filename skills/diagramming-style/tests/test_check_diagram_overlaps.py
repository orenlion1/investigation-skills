"""Tests for the diagram overlap checker.

Each test feeds a minimal Graphviz-shaped SVG fixture to the checker and
asserts that a specific defect class is detected, and that a well-spaced
diagram passes clean. Run from the repository root (or the skill folder):

    python3 -m unittest discover -s skills/diagramming-style/tests
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import check_diagram_overlaps as checker  # noqa: E402


def svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
            '<g class="graph">' + body + '</g></svg>')


NODE_A = ('<g class="node"><title>a</title>'
          '<polygon fill="none" stroke="#6366f1" '
          'points="20,20 120,20 120,60 20,60"/>'
          '<text x="70" y="45" text-anchor="middle" font-size="14">A</text>'
          '</g>')
NODE_B = ('<g class="node"><title>b</title>'
          '<polygon fill="none" stroke="#6366f1" '
          'points="20,200 120,200 120,240 20,240"/>'
          '<text x="70" y="225" text-anchor="middle" font-size="14">B</text>'
          '</g>')
# A vertical edge from a to b with a well-offset label and a clear arrowhead.
EDGE_CLEAN = ('<g class="edge"><title>a-&gt;b</title>'
              '<path fill="none" stroke="#475569" d="M70,60 L70,190"/>'
              '<polygon fill="#475569" stroke="#475569" '
              'points="70,198 66,188 74,188"/>'
              '<text x="110" y="130" text-anchor="middle" font-size="12">'
              'writes</text></g>')


class CheckerTests(unittest.TestCase):

    def run_checker(self, markup, **overrides):
        options = {'clearance': 2.0, 'min_edge_run': 12.0,
                   'touch_tolerance': 1.0, 'char_width_ratio': 0.48}
        options.update(overrides)
        with tempfile.NamedTemporaryFile('w', suffix='.svg',
                                         delete=False) as handle:
            handle.write(markup)
            path = handle.name
        groups = checker.parse_groups(path, options['char_width_ratio'])
        return checker.check_groups(groups, options['clearance'],
                                    options['min_edge_run'],
                                    options['touch_tolerance'])

    def types(self, violations):
        return {v['type'] for v in violations}

    def test_clean_diagram_passes(self):
        violations = self.run_checker(svg(NODE_A + NODE_B + EDGE_CLEAN))
        self.assertEqual(violations, [])

    def test_label_on_edge_line_detected(self):
        edge = EDGE_CLEAN.replace('x="110"', 'x="70"')  # label onto the line
        violations = self.run_checker(svg(NODE_A + NODE_B + edge))
        self.assertIn('label_line_overlap', self.types(violations))

    def test_label_overlapping_shape_detected(self):
        edge = EDGE_CLEAN.replace('y="130"', 'y="205"').replace(
            'x="110"', 'x="60"')  # label pushed into node b's outline
        violations = self.run_checker(svg(NODE_A + NODE_B + edge))
        self.assertIn('label_shape_overlap', self.types(violations))

    def test_label_overlapping_arrow_mark_detected(self):
        edge = EDGE_CLEAN.replace('x="110" y="130"', 'x="70" y="195"')
        violations = self.run_checker(svg(NODE_A + NODE_B + edge))
        self.assertIn('label_mark_overlap', self.types(violations))

    def test_colliding_labels_detected(self):
        second = ('<g class="edge"><title>x</title>'
                  '<path fill="none" stroke="#475569" d="M200,60 L200,190"/>'
                  '<text x="112" y="131" text-anchor="middle" '
                  'font-size="12">reads</text></g>')
        violations = self.run_checker(svg(NODE_A + NODE_B + EDGE_CLEAN +
                                          second))
        self.assertIn('label_label_overlap', self.types(violations))

    def test_overlapping_shapes_detected(self):
        node_c = NODE_B.replace('<title>b</title>', '<title>c</title>') \
            .replace('20,200 120,200 120,240 20,240',
                     '100,40 220,40 220,80 100,80') \
            .replace('x="70" y="225"', 'x="160" y="65"') \
            .replace('>B<', '>C<')
        violations = self.run_checker(svg(NODE_A + node_c))
        self.assertIn('shape_shape_overlap', self.types(violations))

    def test_mark_touching_outline_allowed(self):
        # Arrowhead tip exactly on node b's top border: touch, not penetration.
        edge = EDGE_CLEAN.replace('points="70,198 66,188 74,188"',
                                  'points="70,200 66,190 74,190"')
        violations = self.run_checker(svg(NODE_A + NODE_B + edge))
        self.assertNotIn('mark_shape_penetration', self.types(violations))

    def test_mark_penetrating_outline_detected(self):
        edge = EDGE_CLEAN.replace('points="70,198 66,188 74,188"',
                                  'points="70,210 66,200 74,200"')
        violations = self.run_checker(svg(NODE_A + NODE_B + edge))
        self.assertIn('mark_shape_penetration', self.types(violations))

    def test_short_edge_detected(self):
        short = ('<g class="edge"><title>s</title>'
                 '<path fill="none" stroke="#475569" d="M300,100 L300,108"/>'
                 '</g>')
        violations = self.run_checker(svg(NODE_A + NODE_B + EDGE_CLEAN +
                                          short))
        short_edges = [v for v in violations if v['type'] == 'short_edge']
        self.assertEqual(len(short_edges), 1)
        self.assertIn('8.0px', short_edges[0]['detail'])

    def test_edge_too_short_for_its_marks_detected(self):
        # A 20px run bearing ~24px of ER-style endpoint notation must fail,
        # while the same notation on a long run passes (ratio rule).
        marks = ('<polygon fill="none" stroke="#475569" '
                 'points="296,{y0} 304,{y0} 304,{y1} 296,{y1}"/>')
        crammed = ('<g class="edge"><title>m</title>'
                   '<path fill="none" stroke="#475569" d="M300,100 L300,120"/>'
                   + marks.format(y0=102, y1=112)
                   + marks.format(y0=108, y1=120) + '</g>')
        violations = self.run_checker(svg(NODE_A + NODE_B + EDGE_CLEAN +
                                          crammed))
        self.assertIn('short_edge', self.types(violations))
        roomy = crammed.replace('d="M300,100 L300,120"',
                                'd="M300,100 L300,160"')
        violations = self.run_checker(svg(NODE_A + NODE_B + EDGE_CLEAN +
                                          roomy))
        self.assertNotIn('short_edge', self.types(violations))

    def test_plain_node_attachment_exempt_but_crossing_flagged(self):
        # Plain-label nodes have no outline: an edge may run up to the text
        # of its own endpoints, but a line crossing an unrelated node's
        # text is a defect.
        plain_a = ('<g class="node"><title>p</title>'
                   '<text x="300" y="100" text-anchor="middle" '
                   'font-size="14">Plain source</text></g>')
        plain_b = ('<g class="node"><title>q</title>'
                   '<text x="300" y="220" text-anchor="middle" '
                   'font-size="14">Plain target</text></g>')
        own_edge = ('<g class="edge"><title>p-&gt;q</title>'
                    '<path fill="none" stroke="#475569" '
                    'd="M300,105 L300,205"/></g>')
        violations = self.run_checker(svg(plain_a + plain_b + own_edge))
        self.assertEqual(violations, [])
        crossing = ('<g class="edge"><title>a-&gt;b</title>'
                    '<path fill="none" stroke="#475569" '
                    'd="M200,97 L400,97"/></g>')
        violations = self.run_checker(svg(plain_a + plain_b + own_edge +
                                          crossing))
        self.assertIn('label_line_overlap', self.types(violations))

    def test_invisible_layout_edges_ignored(self):
        invisible = ('<g class="edge"><title>i</title>'
                     '<path fill="none" stroke="none" d="M300,100 L300,110"/>'
                     '</g>')
        violations = self.run_checker(svg(NODE_A + NODE_B + EDGE_CLEAN +
                                          invisible))
        self.assertEqual(violations, [])

    def test_graph_title_checked_as_label(self):
        titled = svg('<text x="70" y="45" text-anchor="middle" '
                     'font-size="16">Title over node</text>' +
                     NODE_A + NODE_B + EDGE_CLEAN)
        violations = self.run_checker(titled)
        self.assertIn('label_shape_overlap', self.types(violations))

    @unittest.skipUnless(shutil.which('dot'), 'graphviz not installed')
    def test_rendered_er_spacing_separates_good_from_crammed(self):
        """End to end: dot-rendered ER edges with crow's-foot notation pass
        when spaced and fail when crammed."""
        template = '''digraph ER {{
          graph [pad=0.2, nodesep=0.5, ranksep={ranksep}];
          node [fontname="Trebuchet MS", fontsize=15, shape=plain];
          one [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0"
            CELLPADDING="4"><TR><TD><B>One</B></TD></TR>
            <TR><TD>OneID</TD></TR></TABLE>>];
          many [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0"
            CELLPADDING="4"><TR><TD><B>Many</B></TD></TR>
            <TR><TD>OneID</TD></TR></TABLE>>];
          one -> many [dir=both, arrowtail="teetee", arrowhead="crowodot"];
        }}'''

        def render_and_check(ranksep):
            with tempfile.NamedTemporaryFile('w', suffix='.dot',
                                             delete=False) as handle:
                handle.write(template.format(ranksep=ranksep))
                dot_path = handle.name
            svg_path = dot_path + '.svg'
            subprocess.run(['dot', '-Tsvg', '-o', svg_path, dot_path],
                           check=True)
            groups = checker.parse_groups(svg_path, 0.48)
            return checker.check_groups(groups, 2.0, 12.0, 1.0)

        self.assertEqual(render_and_check('0.9'), [])
        crammed = {v['type'] for v in render_and_check('0.02')}
        self.assertTrue(crammed & {'short_edge', 'mark_shape_penetration'},
                        f'crammed ER edge not detected: {crammed}')

    def test_non_graphviz_svg_rejected(self):
        plain = ('<svg xmlns="http://www.w3.org/2000/svg">'
                 '<rect x="1" y="1" width="5" height="5"/></svg>')
        with tempfile.NamedTemporaryFile('w', suffix='.svg',
                                         delete=False) as handle:
            handle.write(plain)
            path = handle.name
        with self.assertRaises(ValueError):
            checker.parse_groups(path, 0.55)


if __name__ == '__main__':
    unittest.main()
