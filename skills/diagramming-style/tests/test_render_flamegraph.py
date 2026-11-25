import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/render_flamegraph.py'


def profile():
    return {'flamegraph': {'names': ['total', 'Loader.parse', 'Other.run', 'Reader.read'],
                          'levels': [{'values': ['0', '100', '0', '0']},
                                     {'values': [0, 85, 10, 1, 0, 15, 15, 2]},
                                     {'values': [0, 75, 75, 3]}], 'total': 100}}


class FlameGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('flame', SCRIPT)
        cls.flame = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.flame)

    def test_decodes_native_delta_offsets_and_preserves_self_weights(self):
        frames, total = self.flame.decode(profile())
        self.assertEqual(total, 100)
        self.assertEqual([(f['x'], f['total'], f['self']) for f in frames],
                         [(0, 100, 0), (0, 85, 10), (85, 15, 15), (0, 75, 75)])

    def test_invalid_parentage_and_self_weights_fail(self):
        for values in [[90, 10, 10, 3], [0, 86, 86, 3], [0, 75, 76, 3]]:
            data = profile()
            data['flamegraph']['levels'][2]['values'] = values
            with self.assertRaises(ValueError):
                self.flame.decode(data)

    def test_rejects_invalid_indices_fractional_weights_and_empty_profiles(self):
        for values in [[0, 75, 75, 99], [0, 75.5, 0, 3], [0, -1, 0, 3]]:
            data = profile()
            data['flamegraph']['levels'][2]['values'] = values
            with self.assertRaises(ValueError):
                self.flame.decode(data)
        with self.assertRaises(ValueError):
            self.flame.decode({'names': [], 'levels': [], 'total': 0})

    def test_names_and_levels_must_be_native_arrays(self):
        for field, value in [('names', 'abcd'), ('levels', 'not-levels')]:
            data = profile()
            data['flamegraph'][field] = value
            with self.assertRaises(ValueError):
                self.flame.decode(data)

    def test_cli_rejects_invalid_xml_names_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = profile()
            data['flamegraph']['names'][1] = 'bad\x00name'
            source = root / 'profile.json'
            source.write_text(json.dumps(data))
            result = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source),
                                     '--light', str(root / 'light.svg'), '--dark', str(root / 'dark.svg')],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'light.svg').exists())
            self.assertFalse((root / 'dark.svg').exists())

    def test_themes_have_identical_geometry_and_safe_labels(self):
        data = profile()
        data['flamegraph']['names'][1] = '</text><script>alert(1)</script>'
        geometry = []
        for theme in ['light', 'dark']:
            svg, meta = self.flame.render(data, theme)
            tree = ET.fromstring(svg)
            frames = [n for n in tree.iter() if 'data-name' in n.attrib]
            self.assertEqual(len(frames), 4)
            self.assertFalse(any(n.tag.endswith('script') for n in tree.iter()))
            geometry.append([{k: n.get(k) for k in ['x', 'y', 'width', 'height', 'data-name']}
                             for n in frames])
            self.assertEqual(meta['displayed_frames'], 4)
        self.assertEqual(*geometry)

    def test_subtree_focus_keeps_whole_profile_percentage_and_reports_truncation(self):
        svg, meta = self.flame.render(profile(), 'light', focus='Loader.parse', max_depth=1)
        self.assertEqual(meta['focus_share_percent'], 85)
        self.assertEqual(meta['percentage_denominator'], 100)
        self.assertEqual(meta['displayed_frames'], 1)
        self.assertEqual(meta['omitted_descendant_frames'], 1)
        self.assertIn(b'85.00%', svg)
        with self.assertRaises(ValueError):
            self.flame.render(profile(), 'light', focus='missing')

    def test_cli_generates_pair_and_refuses_any_output_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, light, dark = [root / n for n in ['profile.json', 'light.svg', 'dark.svg']]
            source.write_text(json.dumps(profile()))
            command = [sys.executable, str(SCRIPT), '--input', str(source),
                       '--light', str(light), '--dark', str(dark)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            meta = json.loads(run.stdout)
            self.assertEqual(meta['profile_total'], 100)
            self.assertEqual(len(meta['source_sha256']), 64)
            old = light.read_bytes()
            dark.unlink()
            again = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(light.read_bytes(), old)
            self.assertFalse(dark.exists())


if __name__ == '__main__':
    unittest.main()
