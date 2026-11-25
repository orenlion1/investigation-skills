"""Native Confluence themes must not inherit a fixed HTML download theme."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/publish-it/scripts/confluence_figures.py'


class ConfluenceThemePairTests(unittest.TestCase):
    def render(self, light, dark):
        spec = importlib.util.spec_from_file_location('confluence_figures', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.render_theme_pair(light, dark, page_id='42')

    def asset(self, theme):
        return {'name': 'cpu-' + theme + '.png', 'file_id': theme + '-media',
                'collection': 'contentId-42', 'verified_owner': '42'}

    def test_light_export_still_delivers_dark_and_light_native_choices(self):
        # Fixed export rewrites source media to "not all"; native composition must
        # use the verified pair, never the export's fallback img or media condition.
        light, dark = self.asset('light'), self.asset('dark')
        result = self.render(light, dark)
        self.assertIn('data-extension-key="native-tabs"', result)
        self.assertLess(result.index('dark-media'), result.index('light-media'))
        self.assertEqual(result.count('data-type="media-single"'), 2)
        self.assertIn('Dark graph', result)
        self.assertIn('Light graph', result)
        self.assertNotIn('<picture', result)
        self.assertNotIn('<style', result)
        self.assertEqual(light, self.asset('light'))

    def test_missing_pair_or_wrong_owner_blocks_composition(self):
        for invalid in ({}, {**self.asset('dark'), 'verified_owner': '9'},
                        {**self.asset('dark'), 'collection': ''}):
            with self.assertRaises(ValueError):
                self.render(self.asset('light'), invalid)

    def test_same_media_cannot_masquerade_as_two_themes(self):
        with self.assertRaises(ValueError):
            self.render(self.asset('light'), self.asset('light'))


if __name__ == '__main__':
    unittest.main()
