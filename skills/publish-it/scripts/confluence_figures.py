"""Compose explicit native graph theme choices, independent of HTML export CSS.

Native media has one file ID, not a viewer-theme selector. This supported tabs
fallback is manual; it must never be reported as automatic profile switching.
"""
from html import escape
import json
from uuid import uuid4


def render_theme_pair(light, dark, *, page_id):
    """Return Dark/Light native tabs using already verified page attachments.

    Callers retain the caption/evidence immediately after the returned block.
    No uploads, theme preference changes, or export mutations happen here.
    """
    page_id = str(page_id)
    if not page_id.isdecimal():
        raise ValueError('a verified numeric owning page ID is required')
    for asset in (light, dark):
        if (str(asset.get('verified_owner', '')) != page_id
                or asset.get('collection') != 'contentId-' + page_id
                or not isinstance(asset.get('file_id'), str) or not asset['file_id'].strip()
                or not isinstance(asset.get('name'), str) or not asset['name'].strip()):
            raise ValueError('both themes require verified owning-page media and collection')
    if light['file_id'] == dark['file_id']:
        raise ValueError('light and dark must identify distinct verified media')
    tabs, frames = [], []
    for theme, asset in (('Dark', dark), ('Light', light)):
        tabs.append({'id': str(uuid4()), 'title': theme + ' graph'})
        attrs = {'data-type': 'media', 'data-media-type': 'file',
                 'data-id': asset['file_id'], 'data-collection': asset['collection'],
                 'data-alt': theme + ' graph: ' + asset['name']}
        media = '<div ' + ' '.join(k + '="' + escape(v, quote=True) + '"' for k, v in attrs.items()) + '></div>'
        frames.append('<div data-type="extension-frame">'
                      '<figure data-type="media-single" data-layout="center" '
                      'data-width="100" data-width-type="percentage">' + media + '</figure></div>')
    parameters = escape(json.dumps({'tabs': tabs}), quote=True)
    return ('<div data-type="multi-bodied-extension" data-extension-key="native-tabs" '
            'data-extension-type="com.atlassian.confluence.native" data-parameters="'
            + parameters + '">' + ''.join(frames) + '</div>')
