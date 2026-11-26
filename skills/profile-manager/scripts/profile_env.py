#!/usr/bin/env python3
"""Local .env resource-profile store whose schema comes from the TASK template (Python 3.8+)."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

SCHEMA = 'profile-manager/v1'
PREFIX = 'PROFILE__'
SEPARATOR = '__'
HEADING = '## Resources'
MARKER = '# profile: '
MAX_ENV_BYTES = 262_144
MAX_TEMPLATE_BYTES = 262_144
MAX_TASK_BYTES = 1_048_576
MAX_VALUE_LENGTH = 512
MAX_ENDPOINT_BYTES = 8192
MAX_ENDPOINTS = 16
MAX_RESOURCE_LIST_BYTES = 8192
MAX_RESOURCE_LIST_ITEMS = 16
LIST_FIELDS = {'REPO': 'repository-or-array', 'SLACK_CHANNEL': 'channel-or-array',
               'PUBLISH': 'destination-or-array'}
HISTORICAL_WINDOW = 'RHYMING_HISTORICAL_WINDOW_DAYS'
DEFAULT_HISTORICAL_WINDOW_DAYS = '7'
GENERATE_MARKDOWN = 'GENERATE_MARKDOWN'
GENERATE_HTML = 'GENERATE_HTML'
GENERATE_PDF = 'GENERATE_PDF'
GRAFANA_ASSISTANT = 'GRAFANA_ASSISTANT'
# Settings contract: every toggle setting takes exactly these two values.
ENABLED = 'enabled'
DISABLED = 'disabled'
TOGGLE_VALUES = (ENABLED, DISABLED)
TOGGLE_ERROR = '; expected ' + ENABLED + ' or ' + DISABLED
DEFAULT_GENERATE_MARKDOWN = DISABLED
DEFAULT_GENERATE_HTML = ENABLED
DEFAULT_GENERATE_PDF = DISABLED
DEFAULT_GRAFANA_ASSISTANT = ENABLED
FAN_OUT = 'FAN_OUT'
DEFAULT_FAN_OUT = ENABLED
CONTROL_DEFAULTS = {GENERATE_MARKDOWN: DEFAULT_GENERATE_MARKDOWN,
                    GENERATE_HTML: DEFAULT_GENERATE_HTML,
                    GENERATE_PDF: DEFAULT_GENERATE_PDF,
                    GRAFANA_ASSISTANT: DEFAULT_GRAFANA_ASSISTANT,
                    FAN_OUT: DEFAULT_FAN_OUT}
HTML_THEME = 'HTML_THEME'
HTML_THEMES = ('light', 'dark', 'system')
DEFAULT_HTML_THEME = 'light, dark'
SETTING_DEFAULTS = {**CONTROL_DEFAULTS, HTML_THEME: DEFAULT_HTML_THEME}


LINT_MESSAGE = ('the profile store holds legacy or hand-edited settings; ask the user to run '
                '"lint profiles" (lint --fix) to update their .env')
TASK_LINT_MESSAGE = ('task Resources hold legacy, hand-edited or illegal settings; ask the user '
                     'to run "lint task <path>" (lint --task <path> --fix) and to replace any '
                     'value that needs a decision with a legal one')
DEFAULT_TASK_DIRECTORY = 'docs/tasks'
MAX_LINTED_TASKS = 200
# Values written before the contract; accepted on input and stored as their canonical value.
LEGACY_TOGGLE_VALUES = {GENERATE_PDF: {'T': ENABLED, 'F': DISABLED}}
ENDPOINT_KINDS = ('grafana-investigations', 'grafana-assistant-conversations',
                  'grafana-assistant-search', 'grafana-irm-incidents',
                  'confluence', 'slack', 'repository')
IGNORE_BLOCK = ('# Local resource-profile store; never commit.', '.env', '.env.*', '!.env.example')

NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
FIELD = re.compile(r'[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*\Z')
KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
BULLET = re.compile(r'- (?P<label>[^:`]+): (?P<rest>.+)\Z')
PLACEHOLDER = re.compile(r'`<[^`>]*>`\Z')
SUBFIELD = re.compile(r'(?P<sublabel>[A-Za-z][A-Za-z0-9 /]*) (?P<placeholder>`<[^`>]*>`)\Z')
EXAMPLES = re.compile(r'\s*\(examples?:.*\)\s*\Z')
ASSIGNMENT = re.compile(r'(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)\Z')
QUOTED = re.compile(r'`([^`]*)`')
# Resource profiles hold resource identifiers; credentials belong in their own stores.
CREDENTIAL = re.compile(
    r'(?:AKIA|ASIA)[0-9A-Z]{16}|xox[abprs]-|-----BEGIN [A-Z ]*PRIVATE KEY'
    r'|gh[pousr]_[A-Za-z0-9]{16,}|glsa_[A-Za-z0-9]{16,}|eyJ[A-Za-z0-9_-]{20,}')


class ProfileError(ValueError):
    """Invalid schema, profile, store or destination; never repaired implicitly."""


def regular_file(path, description, limit):
    """Reject symlinks, non-regular files and oversized inputs before reading."""
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ProfileError(description + ' must be a regular non-symlink file: ' + str(path))
    if path.stat().st_size > limit:
        raise ProfileError(description + ' exceeds ' + str(limit) + ' bytes: ' + str(path))
    return path


def read_text(path, description, limit):
    regular_file(path, description, limit)
    try:
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise ProfileError('cannot read ' + description + ': ' + str(path)) from error


def repository_root(value):
    root = Path(value).resolve()
    if not root.is_dir():
        raise ProfileError('repository root must be an existing directory')
    return root


def profile_name(value):
    if not NAME.fullmatch(value):
        raise ProfileError('profile name must be lowercase kebab-case: ' + value)
    return value


def namespace(name):
    return PREFIX + profile_name(name).replace('-', '_').upper() + SEPARATOR


def profile_from_key(key):
    """Recover a profile name from a managed key; the double separator is structural."""
    parts = key[len(PREFIX):].split(SEPARATOR)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ProfileError('managed key is not PROFILE__NAME__FIELD: ' + key)
    return parts[0].lower().replace('_', '-'), parts[1]


def normalize_label(label):
    key = re.sub(r'[^A-Za-z0-9]+', '_', re.sub(r'\([^)]*\)', ' ', label)).strip('_').upper()
    if not FIELD.fullmatch(key) or SEPARATOR in key:
        raise ProfileError('resource label does not normalize to a field key: ' + label.strip())
    return key


def squash(name):
    """Reduce a field name or label to its letters and digits for tolerant matching."""
    return re.sub(r'[^A-Za-z0-9]+', '', re.sub(r'\([^)]*\)', ' ', name)).upper()


def resolve_field(name, schema):
    """Match a field name or template label regardless of case, spaces, hyphens or underscores."""
    wanted = squash(name)
    matches = [field for field in schema['fields'] if squash(field) == wanted]
    if not matches:
        matches = [bullet['keys'][0] for bullet in schema['bullets']
                   if squash(bullet['label']) == wanted]
    if len(matches) != 1 or not wanted:
        raise ProfileError('unknown field ' + ' '.join(name.split()).upper()
                           + '; the schema comes from the template')
    return matches[0]


def parse_assignment(assignment, schema):
    """Split FIELD=value or "field: value"; the first delimiter decides the form."""
    positions = [index for index in (assignment.find('='), assignment.find(':')) if index >= 0]
    if not positions:
        raise ProfileError('field must be FIELD=value or "field: value"')
    index = min(positions)
    value = assignment[index + 1:]
    if assignment[index] == ':':
        value = value.strip()
    return resolve_field(assignment[:index], schema), value


def section_bounds(lines, description):
    """Locate the single Resources section; its body ends at the next level-2 heading."""
    starts = [index for index, line in enumerate(lines) if line.strip() == HEADING]
    if len(starts) != 1:
        raise ProfileError(description + ' needs exactly one "' + HEADING + '" section')
    start = starts[0]
    for index in range(start + 1, len(lines)):
        if lines[index].startswith('## '):
            return start, index
    return start, len(lines)


def parse_template(text):
    """Derive the profile schema from the template's Resources bullets."""
    lines = text.splitlines()
    start, end = section_bounds(lines, 'template')
    bullets, fields = [], {}
    for line in lines[start + 1:end]:
        if not line.startswith('- '):
            continue
        match = BULLET.fullmatch(EXAMPLES.sub('', line.rstrip()))
        if not match:
            raise ProfileError('resource bullet is not "- Label: `<placeholder>`": ' + line.strip())
        label = match.group('label').strip()
        primary = normalize_label(label)
        parts = match.group('rest').split('; ')
        if not PLACEHOLDER.fullmatch(parts[0]):
            raise ProfileError('resource bullet needs one backticked placeholder: ' + line.strip())
        entries = [(primary, None)]
        for part in parts[1:]:
            extra = SUBFIELD.fullmatch(part)
            if not extra:
                raise ProfileError('extra resource segment is not "Label `<placeholder>`": ' + part)
            sublabel = extra.group('sublabel').strip()
            entries.append((primary + '_' + normalize_label(sublabel), sublabel))
        bullet = {'label': label, 'keys': [key for key, _ in entries],
                  'sublabels': {key: sub for key, sub in entries if sub is not None}}
        for key, sublabel in entries:
            if key in fields:
                raise ProfileError('duplicate derived field key: ' + key)
            fields[key] = {'field': key, 'label': label, 'sublabel': sublabel,
                           'requires': None if sublabel is None else primary}
        bullets.append(bullet)
    if not fields:
        raise ProfileError('template Resources section declares no resource bullets')
    if 'RHYMING_ENDPOINTS' in fields:
        fields['RHYMING_ENDPOINTS'].update(
            type='endpoint-array', kinds=list(ENDPOINT_KINDS),
            max_bytes=MAX_ENDPOINT_BYTES, max_items=MAX_ENDPOINTS,
            required=['id', 'kind', 'target'],
            conditional={'grafana': ['context'], 'repository': ['provider']})
    for key, field_type in LIST_FIELDS.items():
        if key in fields:
            fields[key].update(type=field_type, max_items=MAX_RESOURCE_LIST_ITEMS,
                               max_item_characters=MAX_VALUE_LENGTH,
                               max_bytes=MAX_RESOURCE_LIST_BYTES)
    if HISTORICAL_WINDOW in fields:
        fields[HISTORICAL_WINDOW].update(
            type='positive-integer-days', default=DEFAULT_HISTORICAL_WINDOW_DAYS,
            render_requires='RHYMING_ENDPOINTS')
    for key, default in SETTING_DEFAULTS.items():
        if key in fields:
            fields[key].update(type='enum', enum=list(HTML_THEMES if key == HTML_THEME else TOGGLE_VALUES), default=default,
                               resource=False)
            if key == HTML_THEME:
                fields[key].update(type='enum-or-array', max_items=len(HTML_THEMES),
                                   unique_items=True, input_forms=['scalar', 'comma-separated', 'json-array'])
            if key in LEGACY_TOGGLE_VALUES:
                fields[key].update(legacy_values=dict(LEGACY_TOGGLE_VALUES[key]))
    return {'schema': SCHEMA, 'fields': fields, 'bullets': bullets}


def supplied_values(section_lines):
    """Report backticked values already present in a Resources section body."""
    supplied = []
    for line in section_lines:
        if not line.startswith('- '):
            continue
        for value in QUOTED.findall(EXAMPLES.sub('', line.rstrip())):
            if value and not (value.startswith('<') and value.endswith('>')):
                supplied.append(value)
    return supplied


def check_value(value):
    if not isinstance(value, str) or value != value.strip() or not value:
        raise ProfileError('value must be non-empty without surrounding whitespace')
    if len(value) > MAX_VALUE_LENGTH:
        raise ProfileError('value exceeds ' + str(MAX_VALUE_LENGTH) + ' characters')
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ProfileError('value must not contain control characters')
    if "'" in value:
        raise ProfileError("value must not contain a single quote; the store quotes with '")
    if value.startswith('<') and value.endswith('>'):
        raise ProfileError('placeholders and examples are not resources: ' + value)
    if CREDENTIAL.search(value):
        raise ProfileError('value looks like a credential; profiles store resource identifiers only')
    return value


def validate_rhyming_endpoints(value):
    """Validate the entire optional JSON field before dispatch; never echo its values."""
    def reject():
        raise ProfileError('invalid RHYMING_ENDPOINTS; see the endpoint schema contract')

    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                reject()
            result[key] = item
        return result

    try:
        if not isinstance(value, str) or len(value.encode('utf-8')) > MAX_ENDPOINT_BYTES:
            reject()
        if any(ord(c) < 32 or ord(c) == 127 or c in "'`" for c in value):
            reject()
        endpoints = json.loads(value, object_pairs_hook=unique)
        if not isinstance(endpoints, list) or not 1 <= len(endpoints) <= MAX_ENDPOINTS:
            reject()
        ids = set()
        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                reject()
            kind = endpoint.get('kind')
            if kind not in ENDPOINT_KINDS:
                reject()
            keys = {'id', 'kind', 'target'}
            if kind.startswith('grafana-'):
                keys.add('context')
            if kind == 'repository':
                keys.add('provider')
            if set(endpoint) != keys:
                reject()
            for item in endpoint.values():
                check_value(item)
                if any(c in item for c in '`$<>\\'):
                    reject()
            identity, target = endpoint['id'], endpoint['target']
            if not NAME.fullmatch(identity) or identity in ids:
                reject()
            ids.add(identity)
            if kind.startswith('grafana-'):
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', endpoint['context']):
                    reject()
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.:/-]*', target):
                    reject()
            elif kind == 'slack':
                if not re.fullmatch(r'(?:[CG][A-Z0-9]{8,}|#[a-z0-9][a-z0-9_-]*)', target):
                    reject()
            else:
                url = urlsplit(target)
                decoded = unquote(target)
                if (url.scheme != 'https' or not url.hostname or url.username is not None
                        or url.password is not None or url.query or url.fragment or url.port
                        or any(ord(c) <= 32 or ord(c) == 127 or c in "`$<>\\'" for c in decoded)
                        or any(part in {'.', '..'} for part in unquote(url.path).split('/'))):
                    reject()
                try:
                    ipaddress.ip_address(url.hostname)
                except ValueError:
                    if not re.fullmatch(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', url.hostname):
                        reject()
                else:
                    reject()
                if kind == 'confluence':
                    if not url.hostname.endswith('.atlassian.net') or not url.path.startswith('/wiki/'):
                        reject()
                else:
                    hosts = {'github': 'github.com', 'bitbucket': 'bitbucket.org'}
                    if (endpoint['provider'] not in hosts
                            or url.hostname != hosts[endpoint['provider']]
                            or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?', url.path)):
                        reject()
        return endpoints
    except (ValueError, TypeError, UnicodeError, RecursionError):
        reject()


def toggle_value(field, value):
    """Translate any accepted spelling of a toggle value to its setting constant."""
    spelling = value.strip().casefold() if isinstance(value, str) else None
    for constant in TOGGLE_VALUES:
        if spelling == constant:
            return constant
    for legacy, constant in LEGACY_TOGGLE_VALUES.get(field, {}).items():
        if spelling == legacy.casefold():
            return constant
    raise ProfileError('invalid ' + field + TOGGLE_ERROR)


def check_field(field, value):
    """Validate one field and return the value to use, canonical for toggle settings."""
    if field in CONTROL_DEFAULTS:
        return toggle_value(field, value)
    if field == HTML_THEME:
        try:
            if not isinstance(value, str) or len(value) > MAX_VALUE_LENGTH:
                raise ValueError()
            entries = json.loads(value) if value.lstrip().startswith('[') else value.split(',')
            if not isinstance(entries, list) or not 1 <= len(entries) <= len(HTML_THEMES):
                raise ValueError()
            themes = [entry.strip().casefold() for entry in entries]
            if any(theme not in HTML_THEMES for theme in themes) or len(set(themes)) != len(themes):
                raise ValueError()
        except (ValueError, TypeError, AttributeError, RecursionError):
            raise ProfileError('invalid HTML_THEME; expected unique light, dark or system themes')
        return ', '.join(themes)
    if field in LIST_FIELDS:
        if isinstance(value, str) and not value.startswith('['):
            check_value(value)
        resource_values(value, field)
        return value
    if field == HISTORICAL_WINDOW:
        if (not isinstance(value, str) or len(value) > MAX_VALUE_LENGTH
                or not re.fullmatch(r'[1-9][0-9]*', value)):
            raise ProfileError('invalid ' + HISTORICAL_WINDOW + '; expected positive integer days')
        return value
    if field == 'RHYMING_ENDPOINTS':
        validate_rhyming_endpoints(value)
        return value
    return check_value(value)


def resource_values(value, field):
    """Normalize bounded repository/channel/destination lists without rewriting stored values."""
    try:
        if (not isinstance(value, str) or value != value.strip()
                or len(value.encode('utf-8')) > MAX_RESOURCE_LIST_BYTES
                or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValueError()
        entries = json.loads(value) if value.startswith('[') else [value]
        if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_RESOURCE_LIST_ITEMS:
            raise ValueError()
        seen = set()
        for entry in entries:
            check_value(entry)
            entry.encode('utf-8')
            if entry in seen or any(char in entry for char in '`<>\\\x85\u2028\u2029'):
                raise ValueError()
            if field in ('REPO', 'PUBLISH') and '://' in entry:
                url = urlsplit(entry)
                ssh_identity = url.scheme == 'ssh' and url.username == 'git'
                if (url.username is not None and not ssh_identity) or url.password is not None:
                    raise ValueError()
                # A Confluence page URL may carry its page ID in the query; a repository may not.
                if field == 'REPO' and (url.query or url.fragment):
                    raise ValueError()
            seen.add(entry)
        return entries
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ProfileError('invalid ' + field + '; expected a resource or a bounded unique JSON array') from None


def assigned_keys(lines):
    """Return every assigned key, without interpreting any value."""
    keys = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        match = ASSIGNMENT.fullmatch(stripped)
        if match:
            keys.add(match.group('key'))
    return keys


def parse_store(text):
    """Return (lines, managed) where managed maps line index to (key, value).

    Only keys inside the managed namespace are interpreted; every other line is
    preserved verbatim so unrelated environment entries and secrets stay untouched.
    """
    lines = text.splitlines()
    managed = {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        match = ASSIGNMENT.fullmatch(stripped)
        if not match or not match.group('key').startswith(PREFIX):
            continue
        key, raw = match.group('key'), match.group('value').strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
            value = raw[1:-1]
        elif raw and not any(character in raw for character in ' \t#"\'\\'):
            value = raw
        else:
            raise ProfileError('managed entry is not a plain or quoted value: ' + key)
        managed[index] = (key, value)
    return lines, managed


def load_store(path):
    if not os.path.lexists(path):
        return [], {}, False
    return (*parse_store(read_text(path, 'profile store', MAX_ENV_BYTES)), True)


def profiles(managed):
    found = {}
    for key, value in managed.values():
        name, field = profile_from_key(key)
        found.setdefault(name, {})[field] = value
    return found


def tracked(root, relative):
    try:
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '--error-unmatch', '--',
                                 relative], capture_output=True, check=False)
    except OSError:
        return None
    return result.returncode == 0


def ignored(root, relative):
    """True when Git ignores the path, False when it does not, None when unknown."""
    try:
        result = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', '--', relative],
                                capture_output=True, check=False)
    except OSError:
        return None
    if result.returncode in {0, 1}:
        return result.returncode == 0
    gitignore = root / '.gitignore'
    if os.path.lexists(gitignore):
        patterns = read_text(gitignore, 'gitignore', MAX_ENV_BYTES).splitlines()
        return relative in [line.strip() for line in patterns]
    return None


def require_untracked(root, env_path):
    relative = Path(os.path.relpath(env_path, root)).as_posix()
    if tracked(root, relative):
        raise ProfileError('store is tracked by Git; untrack it before storing profiles: ' + relative)
    return relative


def require_ignored(root, env_path):
    relative = require_untracked(root, env_path)
    if ignored(root, relative) is not True:
        raise ProfileError('store is not ignored by Git; run the ignore command first: ' + relative)
    return relative


def write_file(path, text, mode=0o600, enforce=False):
    """Replace the file atomically; keep an existing mode unless one is enforced."""
    if os.path.lexists(path):
        regular_file(path, 'destination', max(MAX_ENV_BYTES, MAX_TASK_BYTES))
        if not enforce:
            mode = stat.S_IMODE(path.stat().st_mode)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix='.' + path.name + '.')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except OSError as error:
        os.unlink(temporary)
        raise ProfileError('cannot write ' + str(path)) from error
    return mode


def render_store(lines, managed, name, values):
    """Rewrite managed lines for one profile, preserving every other line and its order."""
    space = namespace(name)
    owned = sorted(index for index, (key, _) in managed.items() if key.startswith(space))
    block = [space + field + "='" + values[field] + "'" for field in sorted(values)]
    kept = [line for index, line in enumerate(lines) if index not in set(owned)]
    if owned:
        anchor = owned[0]
        marker = anchor - 1
        if 0 <= marker < len(kept) and kept[marker].strip() == (MARKER + name).strip():
            if block:
                return kept[:anchor] + block + kept[anchor:]
            return kept[:marker] + kept[anchor:]
        return kept[:anchor] + block + kept[anchor:]
    if not block:
        return kept
    prefix = [] if not kept or not kept[-1].strip() else ['']
    return kept + prefix + [MARKER + name] + block


def render_section(schema, values):
    """Render the Resources section body from resolved values, omitting unset bullets."""
    values = dict(values)
    for field, default in SETTING_DEFAULTS.items():
        if field in schema['fields']:
            values.setdefault(field, default)
    actual_resources = False
    if 'RHYMING_ENDPOINTS' in values and HISTORICAL_WINDOW in schema['fields']:
        values.setdefault(HISTORICAL_WINDOW, DEFAULT_HISTORICAL_WINDOW_DAYS)
    for field, definition in schema['fields'].items():
        required = definition['requires']
        if field in values and required is not None and required not in values:
            raise ProfileError('field ' + field + ' requires ' + required)
    bullets = []
    for bullet in schema['bullets']:
        primary = bullet['keys'][0]
        if primary not in values:
            continue
        if primary == HISTORICAL_WINDOW and 'RHYMING_ENDPOINTS' not in values:
            continue
        if primary not in (*SETTING_DEFAULTS, HISTORICAL_WINDOW):
            actual_resources = True
        if primary in LIST_FIELDS:
            bullets.extend('- ' + bullet['label'] + ': `' + entry + '`'
                           for entry in resource_values(values[primary], primary))
            continue
        text = '- ' + bullet['label'] + ': `' + values[primary] + '`'
        for key in bullet['keys'][1:]:
            if key in values:
                text += '; ' + bullet['sublabels'][key] + ' `' + values[key] + '`'
        bullets.append(text)
    if not actual_resources:
        raise ProfileError('profile supplies no actual resource for the Resources section')
    return bullets


def resolve_profile(store_values, schema, name):
    values = store_values.get(name)
    if values is None:
        raise ProfileError('profile is not in the store: ' + name)
    # Legacy toggle values resolve to their canonical value without rewriting the store.
    known = {field: check_field(field, value) for field, value in values.items()
             if field in schema['fields']}
    unknown = sorted(field for field in values if field not in schema['fields'])
    return known, unknown


def command_schema(arguments, context):
    return {'schema': SCHEMA, 'template': context['template_relative'],
            'fields': [context['schema']['fields'][key]
                       for key in sorted(context['schema']['fields'])]}


def command_list(arguments, context):
    store = profiles(context['managed'])
    return {'store': context['env_relative'], 'exists': context['exists'],
            'ignored': ignored(context['root'], context['env_relative']),
            'tracked': tracked(context['root'], context['env_relative']),
            'profiles': sorted(store), 'profile_count': len(store)}


def command_show(arguments, context):
    known, unknown = resolve_profile(profiles(context['managed']), context['schema'],
                                     arguments.profile)
    return {'profile': arguments.profile, 'store': context['env_relative'], 'fields': known,
            'unknown_fields': unknown,
            'missing_fields': sorted(set(context['schema']['fields']) - set(known)),
            'effective_generate_markdown': known.get(GENERATE_MARKDOWN, DEFAULT_GENERATE_MARKDOWN)
            if GENERATE_MARKDOWN in context['schema']['fields'] else None,
            'effective_html_theme': known.get(HTML_THEME, DEFAULT_HTML_THEME)
            if HTML_THEME in context['schema']['fields'] else None,
            'effective_generate_html': known.get(GENERATE_HTML, DEFAULT_GENERATE_HTML)
            if GENERATE_HTML in context['schema']['fields'] else None,
            'effective_generate_pdf': known.get(GENERATE_PDF, DEFAULT_GENERATE_PDF)
            if GENERATE_PDF in context['schema']['fields'] else None,
            'effective_grafana_assistant': known.get(GRAFANA_ASSISTANT,
                                                    DEFAULT_GRAFANA_ASSISTANT)
            if GRAFANA_ASSISTANT in context['schema']['fields'] else None,
            'effective_fan_out': known.get(FAN_OUT, DEFAULT_FAN_OUT)
            if FAN_OUT in context['schema']['fields'] else None}


def command_set(arguments, context):
    name = profile_name(arguments.profile)
    schema, updates, cleared = context['schema'], {}, []
    for assignment in arguments.field:
        field, value = parse_assignment(assignment, schema)
        if value == '':
            cleared.append(field)
        else:
            updates[field] = check_field(field, value)
    if not updates and not cleared:
        raise ProfileError('supply at least one FIELD=value')
    existing = profiles(context['managed']).get(name, {})
    values = {} if arguments.replace else dict(existing)
    values.update(updates)
    for field in cleared:
        values.pop(field, None)
    if (values and HISTORICAL_WINDOW in schema['fields'] and HISTORICAL_WINDOW not in cleared
            and (not existing or 'RHYMING_ENDPOINTS' in values)):
        values.setdefault(HISTORICAL_WINDOW, DEFAULT_HISTORICAL_WINDOW_DAYS)
    for field, default in SETTING_DEFAULTS.items():
        if values and field in schema['fields'] and field not in cleared:
            values.setdefault(field, default)
    for field in list(values):
        if field not in schema['fields']:
            raise ProfileError('store holds unknown field ' + field + ' for profile ' + name)
        values[field] = check_field(field, values[field])
    if values:
        render_section(schema, values)
    relative = require_ignored(context['root'], context['env_path'])
    lines = render_store(context['lines'], context['managed'], name, values)
    result = {'profile': name, 'store': relative, 'fields': values,
              'added': sorted(set(values) - set(existing)),
              'updated': sorted(field for field in values
                                if field in existing and existing[field] != values[field]),
              'cleared': sorted(set(existing) - set(values)), 'dry_run': arguments.dry_run}
    if not arguments.dry_run:
        result['mode'] = oct(write_file(context['env_path'],
                                        '\n'.join(lines) + ('\n' if lines else ''), enforce=True))
        _, written = parse_store(read_text(context['env_path'], 'profile store', MAX_ENV_BYTES))
        if profiles(written).get(name, {}) != values:
            raise ProfileError('stored profile did not read back as written: ' + name)
    return result


def command_remove(arguments, context):
    name = profile_name(arguments.profile)
    if name not in profiles(context['managed']):
        raise ProfileError('profile is not in the store: ' + name)
    relative = require_untracked(context['root'], context['env_path'])
    lines = render_store(context['lines'], context['managed'], name, {})
    remaining = sorted(profiles(parse_store('\n'.join(lines))[1]))
    result = {'profile': name, 'store': relative, 'removed': True,
              'remaining_profiles': remaining, 'dry_run': arguments.dry_run}
    if not arguments.dry_run:
        result['mode'] = oct(write_file(context['env_path'],
                                        '\n'.join(lines) + ('\n' if lines else ''), enforce=True))
        _, written = parse_store(read_text(context['env_path'], 'profile store', MAX_ENV_BYTES))
        if name in profiles(written):
            raise ProfileError('profile remained in the store after removal: ' + name)
    return result


def command_compose(arguments, context):
    """Persist a named snapshot from ordered sources, refusing scalar conflicts."""
    names = [profile_name(name) for name in arguments.profile]
    target = profile_name(arguments.into)
    if len(names) < 2 or len(set(names)) != len(names) or target in names:
        raise ProfileError('compose needs at least two unique sources and a separate target')
    store = profiles(context['managed'])
    if target in store and not arguments.replace:
        raise ProfileError('target profile already exists; use --replace to replace it')
    overrides = explicit_fields(arguments.field, context['schema'])
    values, lists = {}, {field: [] for field in LIST_FIELDS}
    for name in names:
        known, unknown = resolve_profile(store, context['schema'], name)
        if unknown:
            raise ProfileError('source profile has unknown fields; verify the intended template')
        for field, value in known.items():
            if field in LIST_FIELDS:
                for entry in resource_values(value, field):
                    if entry not in lists[field]:
                        lists[field].append(entry)
            elif field in values and values[field] != value and field not in overrides:
                raise ProfileError('conflicting field ' + field + '; align source profiles first')
            else:
                values[field] = value
    for field, entries in lists.items():
        if entries and field not in overrides:
            values[field] = (entries[0] if len(entries) == 1
                             else json.dumps(entries, separators=(',', ':'), ensure_ascii=False))
            check_field(field, values[field])
    values.update(overrides)
    # Defaults apply only after all stored source values have been reconciled.
    if values:
        for field, default in (*SETTING_DEFAULTS.items(),
                               (HISTORICAL_WINDOW, DEFAULT_HISTORICAL_WINDOW_DAYS)):
            if field in context['schema']['fields']:
                values.setdefault(field, default)
    render_section(context['schema'], values)
    relative = require_ignored(context['root'], context['env_path'])
    # Preserve original newline bytes outside the destination profile as well as values.
    regular_file(context['env_path'], 'profile store', MAX_ENV_BYTES)
    with context['env_path'].open(encoding='utf-8', newline='') as stream:
        original = stream.read()
    raw_lines = original.splitlines(keepends=True)
    space = namespace(target)
    owned = {index for index, (key, _) in context['managed'].items()
             if profile_from_key(key)[0] == target}
    block = ''.join(space + field + "='" + values[field] + "'\n" for field in sorted(values))
    if owned:
        body = ''.join((block if index == min(owned) else '')
                       + (line if index not in owned else '')
                       for index, line in enumerate(raw_lines))
    else:
        body = (original + ('\n' if original and not original.endswith('\n') else '')
                + ('\n' if original else '') + MARKER + target + '\n' + block)
    if len(body.encode('utf-8')) > MAX_ENV_BYTES:
        raise ProfileError('composed store exceeds maximum bytes')
    result = {'profile': target, 'sources': names, 'store': relative,
              'fields': values, 'replaced': target in store, 'dry_run': arguments.dry_run}
    if not arguments.dry_run:
        result['mode'] = oct(write_file(context['env_path'], body, enforce=True))
        _, written = parse_store(read_text(context['env_path'], 'profile store', MAX_ENV_BYTES))
        expected = dict(store, **{target: values})
        if profiles(written) != expected:
            raise ProfileError('composed profile did not read back as written')
        result['verified'] = True
    return result


def command_init(arguments, context):
    relative = require_ignored(context['root'], context['env_path'])
    if context['exists']:
        return {'store': relative, 'created': False, 'already_present': True,
                'dry_run': arguments.dry_run}
    result = {'store': relative, 'created': not arguments.dry_run, 'already_present': False,
              'dry_run': arguments.dry_run}
    if not arguments.dry_run:
        result['mode'] = oct(write_file(context['env_path'], '', enforce=True))
    return result


def command_remove_env(arguments, context):
    relative = require_untracked(context['root'], context['env_path'])
    if not context['exists']:
        raise ProfileError('store does not exist: ' + relative)
    unmanaged = sorted(key for key in assigned_keys(context['lines'])
                       if not key.startswith(PREFIX))
    if unmanaged and not arguments.force:
        raise ProfileError('store holds unmanaged keys (' + ', '.join(unmanaged) +
                           '); re-run with --force to delete the whole file')
    result = {'store': relative, 'deleted': not arguments.dry_run,
              'profiles': sorted(profiles(context['managed'])), 'unmanaged_keys': unmanaged,
              'dry_run': arguments.dry_run}
    if not arguments.dry_run:
        regular_file(context['env_path'], 'profile store', MAX_ENV_BYTES)
        context['env_path'].unlink()
        if os.path.lexists(context['env_path']):
            raise ProfileError('store still exists after deletion: ' + relative)
    return result


def command_ignore(arguments, context):
    root, relative = context['root'], require_untracked(context['root'], context['env_path'])
    gitignore = root / '.gitignore'
    if ignored(root, relative) is True:
        return {'store': relative, 'gitignore': '.gitignore', 'already_ignored': True,
                'appended': [], 'dry_run': arguments.dry_run}
    existing = read_text(gitignore, 'gitignore', MAX_ENV_BYTES) if os.path.lexists(gitignore) else ''
    present = {line.strip() for line in existing.splitlines()}
    appended = [line for line in IGNORE_BLOCK if line not in present]
    result = {'store': relative, 'gitignore': '.gitignore', 'already_ignored': False,
              'appended': appended, 'dry_run': arguments.dry_run}
    if not arguments.dry_run:
        separator = '' if not existing or existing.endswith('\n') else '\n'
        gap = '\n' if existing.strip() else ''
        write_file(gitignore, existing + separator + gap + '\n'.join(appended) + '\n', 0o644)
        if ignored(root, relative) is not True:
            raise ProfileError('store is still not ignored after updating .gitignore: ' + relative)
        result['verified'] = True
    return result


def command_render(arguments, context):
    known, unknown = resolve_profile(profiles(context['managed']), context['schema'],
                                     arguments.profile)
    bullets = render_section(context['schema'], known)
    print('\n'.join([HEADING, ''] + bullets))
    return None


def command_endpoints(arguments, context):
    """Read only selected, validated endpoint resources; do not authenticate or query."""
    require_ignored(context['root'], context['env_path'])
    known, unknown = resolve_profile(profiles(context['managed']), context['schema'],
                                     arguments.profile)
    if unknown:
        raise ProfileError('profile has unknown fields; verify the intended template')
    value = known.get('RHYMING_ENDPOINTS')
    return {'profile': arguments.profile,
            'endpoints': validate_rhyming_endpoints(value) if value else [],
            'historical_window_days': int(known.get(HISTORICAL_WINDOW,
                                                   DEFAULT_HISTORICAL_WINDOW_DAYS)) if value else None}


def command_load(arguments, context):
    known, unknown = resolve_profile(profiles(context['managed']), context['schema'],
                                     arguments.profile)
    task_path = Path(arguments.task)
    if not task_path.is_absolute():
        task_path = context['root'] / task_path
    if not os.path.lexists(task_path):
        raise ProfileError('task does not exist: ' + str(task_path))
    text = read_text(task_path, 'task', MAX_TASK_BYTES)
    lines = text.splitlines()
    start, end = section_bounds(lines, 'task')
    section = lines[start + 1:end]
    task_values, _ = task_fields(section, context['schema'])
    known.update(task_values)
    known.update(explicit_fields(arguments.field, context['schema']))
    bullets = render_section(context['schema'], known)
    toggles = {squash(bullet['label']) for bullet in context['schema']['bullets']
               if bullet['keys'][0] in SETTING_DEFAULTS}
    supplied = supplied_values([line for line in section
                                if squash(line[2:].split(':', 1)[0]) not in toggles])
    if supplied and not arguments.replace:
        raise ProfileError('task Resources already supplies ' + ', '.join(supplied) +
                           '; re-run with --replace to rewrite while preserving user fields')
    section = replace_resource_bullets(section, bullets, context['schema'])
    resources = [line for line in section if line.startswith('- ')]
    updated = lines[:start + 1] + section + lines[end:]
    body = '\n'.join(updated) + ('\n' if text.endswith('\n') or not text else '')
    result = {'profile': arguments.profile, 'task': str(task_path), 'fields': known,
              'unknown_fields': unknown, 'resources': resources, 'replaced': bool(supplied),
              'dry_run': arguments.dry_run}
    if not arguments.dry_run:
        write_file(task_path, body)
        verified = read_text(task_path, 'task', MAX_TASK_BYTES).splitlines()
        start, end = section_bounds(verified, 'task')
        if [line for line in verified[start + 1:end] if line.startswith('- ')] != resources:
            raise ProfileError('task Resources did not read back as written: ' + str(task_path))
        result['verified'] = True
    return result


def replace_resource_bullets(section, bullets, schema):
    """Replace known fields in place, retaining surrounding prose and whitespace."""
    labels = {squash(bullet['label']) for bullet in schema['bullets']}

    def field(line):
        return squash(line[2:].split(':', 1)[0]) if line.startswith('- ') else None

    pending = {}
    for bullet in bullets:
        pending.setdefault(field(bullet), []).append(bullet)
    positions = [index for index, line in enumerate(section) if field(line) in labels]
    updated = []
    for index, line in enumerate(section):
        key = field(line)
        if key in labels:
            updated.extend(pending.pop(key, []))
        else:
            updated.append(line)
        # Fields absent from the task join the end of its existing resource list.
        if positions and index == positions[-1]:
            updated.extend(bullet for group in pending.values() for bullet in group)
            pending.clear()
    if pending:
        # An empty/prose-only section has no existing bullet position to replace.
        if not updated or updated[-1].strip():
            updated.append('')
        updated.extend(bullet for group in pending.values() for bullet in group)
        updated.append('')
    return updated


def explicit_fields(assignments, schema):
    """Validate the user's highest-priority layer without mutating any source."""
    values = {}
    for assignment in assignments:
        field, value = parse_assignment(assignment, schema)
        if field in values:
            raise ProfileError('duplicate explicit field ' + field)
        values[field] = check_field(field, value)
    return values


def task_fields(lines, schema):
    """Collect explicit task fields; keep unrecognized settings such as Fan-out."""
    # Task labels match the template regardless of case, spaces, hyphens or underscores.
    definitions = {squash(bullet['label']): bullet for bullet in schema['bullets']}
    values, preserved, seen = {}, [], set()
    lists = {field: [] for field in LIST_FIELDS}
    for line in lines:
        match = BULLET.fullmatch(EXAMPLES.sub('', line.rstrip()))
        # A malformed known label must not be silently replaced by a profile.
        label = line[2:].split(':', 1)[0].strip() if line.startswith('- ') else None
        key = squash(label) if label else None
        if key not in definitions:
            if line.strip():
                preserved.append(line)
            continue
        bullet = definitions[key]
        primary = bullet['keys'][0]
        if primary not in LIST_FIELDS and primary in seen:
            raise ProfileError('duplicate ' + bullet['label'] + ' setting in task Resources')
        seen.add(primary)
        pattern = r'`([^`]*)`' + ''.join(
            r'(?:; ' + re.escape(bullet['sublabels'][key]) + r' `([^`]*)`)?'
            for key in bullet['keys'][1:])
        parsed = re.fullmatch(pattern, match.group('rest')) if match else None
        if parsed is None and primary in SETTING_DEFAULTS and match:
            # Settings also permit bare values; check_field validates them below.
            parsed = re.fullmatch(r'(.+)', match.group('rest').strip())
        if not parsed:
            if primary in SETTING_DEFAULTS:
                check_field(primary, '')
            raise ProfileError('invalid task resource field ' + primary)
        for key, value in zip(bullet['keys'], parsed.groups()):
            if value is None or (value.startswith('<') and value.endswith('>')):
                continue
            value = check_field(key, value)
            if key in LIST_FIELDS:
                lists[key].extend(resource_values(value, key))
            else:
                values[key] = value
    for field, entries in lists.items():
        if entries:
            values[field] = (entries[0] if len(entries) == 1
                             else json.dumps(entries, separators=(',', ':'), ensure_ascii=False))
            check_field(field, values[field])
    return values, preserved


def finding(rule, location, line, fixable, **details):
    """Describe one lint finding without ever including a stored value."""
    return dict(rule=rule, location=location, line=line, fixable=fixable, **details)


def value_rule(field, value):
    """Name a non-canonical value: a pre-contract legacy value, or a hand-edited spelling."""
    legacy = {key.casefold() for key in LEGACY_TOGGLE_VALUES.get(field, {})}
    return 'legacy-value' if value.strip().casefold() in legacy else 'value-spelling'


def lint_notice(context):
    """Tell the caller when the store needs the user's lint run; never fix it implicitly."""
    try:
        # Read the store again so a command that just rewrote entries reports its new state.
        lines, managed, exists = load_store(context['env_path'])
        findings = lint_store(lines, managed, context['schema'])[0] if exists else []
    except (ProfileError, OSError):
        return None
    if not findings:
        return None
    fixable = sum(1 for item in findings if item['fixable'])
    return {'findings': len(findings), 'fixable': fixable,
            'needs_decision': len(findings) - fixable,
            'rules': sorted({item['rule'] for item in findings}),
            'message': LINT_MESSAGE}


def lint_store(lines, managed, schema, only=None):
    """Find hand-edited store entries; return (findings, lines with fixable ones resolved)."""
    findings, replace, drop, first = [], {}, set(), {}
    for index in sorted(managed):
        key, value = managed[index]
        try:
            name, raw_field = profile_from_key(key)
            space = namespace(name)
        except ProfileError:
            findings.append(finding('invalid-key', 'store', index + 1, False))
            continue
        if only is not None and name != only:
            continue
        where = {'profile': name}
        try:
            field = resolve_field(raw_field, schema)
        except ProfileError:
            findings.append(finding('unknown-field', 'store', index + 1, False, **where))
            continue
        where['field'] = field
        try:
            canonical = check_field(field, value)
        except ProfileError:
            findings.append(finding('invalid-value', 'store', index + 1, False, **where))
            continue
        if (name, field) in first:
            # A repeated setting is one finding: dropped when it agrees, left for the user
            # when it disagrees, since only they know which value was intended.
            same = first[(name, field)] == canonical
            findings.append(finding('duplicate' if same else 'conflicting-duplicate', 'store',
                                    index + 1, same, **where))
            if same:
                drop.add(index)
            continue
        first[(name, field)] = canonical
        if key != space + field:
            findings.append(finding('key-spelling', 'store', index + 1, True,
                                    canonical=space + field, **where))
        if canonical != value:
            findings.append(finding(value_rule(field, value), 'store', index + 1, True,
                                    canonical=canonical, **where))
        rendered = space + field + "='" + canonical + "'"
        if lines[index] != rendered:
            if key == space + field and canonical == value:
                findings.append(finding('formatting', 'store', index + 1, True, **where))
            replace[index] = rendered
    fixed = [replace.get(index, line) for index, line in enumerate(lines) if index not in drop]
    return findings, fixed


def lint_task(lines, schema):
    """Find hand-edited Resources bullets; return (findings, lines with fixable ones resolved)."""
    start, end = section_bounds(lines, 'task')
    definitions = {squash(bullet['label']): bullet for bullet in schema['bullets']}
    findings, replace, drop, first = [], {}, set(), {}
    for index in range(start + 1, end):
        line = lines[index]
        match = BULLET.fullmatch(EXAMPLES.sub('', line.rstrip()))
        if not match or squash(match.group('label')) not in definitions:
            continue
        bullet = definitions[squash(match.group('label'))]
        primary, rest = bullet['keys'][0], match.group('rest')
        where = {'field': primary}
        if match.group('label').strip() != bullet['label']:
            findings.append(finding('label-spelling', 'task', index + 1, True,
                                    canonical=bullet['label'], **where))
            replace[index] = '- ' + bullet['label'] + ': ' + rest
        if primary not in SETTING_DEFAULTS:
            continue
        quoted = re.fullmatch(r'`([^`]*)`', rest)
        value = quoted.group(1) if quoted else rest.strip()
        if value.startswith('<') and value.endswith('>'):
            continue
        try:
            canonical = check_field(primary, value)
        except ProfileError:
            findings.append(finding('invalid-value', 'task', index + 1, False, **where))
            continue
        if not quoted or canonical != value:
            findings.append(finding(value_rule(primary, value), 'task', index + 1, True,
                                    canonical=canonical, **where))
            replace[index] = '- ' + bullet['label'] + ': `' + canonical + '`'
        if primary in first:
            same = first[primary] == canonical
            findings.append(finding('duplicate' if same else 'conflicting-duplicate', 'task',
                                    index + 1, same, **where))
            if same:
                drop.add(index)
        first.setdefault(primary, canonical)
    fixed = [replace.get(index, line) for index, line in enumerate(lines) if index not in drop]
    if not any(not item['fixable'] for item in findings):
        try:
            bounds = section_bounds(fixed, 'task')
            task_fields(fixed[bounds[0] + 1:bounds[1]], schema)
        except ProfileError as error:
            findings.append(finding('invalid-resources', 'task', start + 1, False,
                                    detail=str(error)))
    return findings, fixed


def task_lint_notice(context, directory):
    """Scan saved tasks read-only so a store lint can prompt for the tasks that need one."""
    folder = Path(directory)
    if not folder.is_absolute():
        folder = context['root'] / folder
    if not folder.is_dir():
        return None
    tasks = []
    for path in sorted(folder.glob('TASK*.md'))[:MAX_LINTED_TASKS]:
        try:
            lines = read_text(path, 'task', MAX_TASK_BYTES).splitlines()
            findings = lint_task(lines, context['schema'])[0]
        except (ProfileError, OSError):
            continue
        if findings:
            fixable = sum(1 for item in findings if item['fixable'])
            tasks.append({'task': Path(os.path.relpath(path, context['root'])).as_posix(),
                          'findings': len(findings), 'fixable': fixable,
                          'needs_decision': len(findings) - fixable,
                          'rules': sorted({item['rule'] for item in findings})})
    return {'tasks': tasks, 'message': TASK_LINT_MESSAGE} if tasks else None


def command_lint(arguments, context):
    """Report hand-edited settings in the store and an optional task; --fix resolves them."""
    only = profile_name(arguments.profile) if arguments.profile else None
    findings, writes = [], []
    if context['exists']:
        found, fixed = lint_store(context['lines'], context['managed'], context['schema'], only)
        findings += found
        if fixed != context['lines']:
            writes.append(('store', context['env_path'],
                           '\n'.join(fixed) + ('\n' if fixed else ''), True))
    task_path = None
    if arguments.task:
        task_path = Path(arguments.task)
        if not task_path.is_absolute():
            task_path = context['root'] / task_path
        if not os.path.lexists(task_path):
            raise ProfileError('task does not exist: ' + str(task_path))
        text = read_text(task_path, 'task', MAX_TASK_BYTES)
        lines = text.splitlines()
        found, fixed = lint_task(lines, context['schema'])
        findings += found
        if fixed != lines:
            writes.append(('task', task_path,
                           '\n'.join(fixed) + ('\n' if text.endswith('\n') else ''), False))
    fixable = [item for item in findings if item['fixable']]
    applied = bool(arguments.fix and not arguments.dry_run and writes)
    if applied:
        for location, path, body, enforce in writes:
            if location == 'store':
                require_ignored(context['root'], path)
            write_file(path, body, enforce=enforce)
        lines, managed = parse_store(read_text(context['env_path'], 'profile store',
                                               MAX_ENV_BYTES)) if context['exists'] else ([], {})
        remaining = lint_store(lines, managed, context['schema'], only)[0]
        if task_path is not None:
            remaining += lint_task(read_text(task_path, 'task', MAX_TASK_BYTES).splitlines(),
                                   context['schema'])[0]
        if any(item['fixable'] for item in remaining):
            raise ProfileError('lint fixes did not read back as written')
    unresolved = [item for item in findings if not (applied and item['fixable'])]
    result = {'store': context['env_relative'] if context['exists'] else None,
              'task': str(task_path) if task_path is not None else None,
              'findings': findings, 'fixable': len(fixable),
              'unfixable': len(findings) - len(fixable), 'fixed': len(fixable) if applied else 0,
              'clean': not unresolved, 'dry_run': arguments.dry_run,
              'exit_status': 1 if unresolved else 0}
    if task_path is None:
        # A store lint never edits a task; it reports the tasks whose own lint is due.
        notice = task_lint_notice(context, arguments.task_dir)
        if notice:
            result['task_notice'] = notice
    return result


COMMANDS = {'schema': command_schema, 'list': command_list, 'show': command_show,
            'set': command_set, 'remove': command_remove, 'init': command_init,
            'remove-env': command_remove_env, 'ignore': command_ignore,
            'render': command_render, 'load': command_load, 'endpoints': command_endpoints,
            'compose': command_compose, 'lint': command_lint}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', required=True)
    parser.add_argument('--env', help='profile store path; default <repository-root>/.env')
    parser.add_argument('--template', help='TASK template; default <repository-root>/templates/TASK.md')
    subparsers = parser.add_subparsers(dest='command', required=True)
    for command in COMMANDS:
        sub = subparsers.add_parser(command)
        if command in {'show', 'set', 'remove', 'render', 'load', 'endpoints'}:
            sub.add_argument('--profile', required=True)
        if command == 'compose':
            sub.add_argument('--profile', action='append', required=True,
                             help='source profile, repeated in merge order')
            sub.add_argument('--into', required=True, help='named destination profile in .env')
        if command in {'set', 'compose', 'load'}:
            sub.add_argument('--field', action='append', default=[], metavar='FIELD=value')
        if command in {'set', 'load', 'compose'}:
            sub.add_argument('--replace', action='store_true',
                             help='discard values this command would otherwise preserve')
        if command == 'load':
            sub.add_argument('--task', required=True)
        if command == 'lint':
            sub.add_argument('--profile', help='limit store findings to one profile')
            sub.add_argument('--task', help='also lint this task\'s Resources section')
            sub.add_argument('--task-dir', default=DEFAULT_TASK_DIRECTORY,
                             help='saved tasks to check, read-only, when no --task is given')
            sub.add_argument('--fix', action='store_true',
                             help='rewrite fixable findings in canonical form')
        if command == 'remove-env':
            sub.add_argument('--force', action='store_true',
                             help='delete the store even though it holds unmanaged keys')
        if command not in {'schema', 'list', 'show', 'render', 'endpoints'}:
            sub.add_argument('--dry-run', action='store_true')
    return parser


def build_context(arguments):
    root = repository_root(arguments.repository_root)
    env_path = Path(arguments.env) if arguments.env else root / '.env'
    if not env_path.is_absolute():
        env_path = root / env_path
    template = Path(arguments.template) if arguments.template else root / 'templates' / 'TASK.md'
    if not template.is_absolute():
        template = root / template
    if not os.path.lexists(template):
        raise ProfileError('TASK template does not exist: ' + str(template))
    lines, managed, exists = load_store(env_path)
    return {'root': root, 'env_path': env_path, 'exists': exists, 'lines': lines,
            'managed': managed, 'template_path': template,
            'template_relative': Path(os.path.relpath(template, root)).as_posix(),
            'env_relative': Path(os.path.relpath(env_path, root)).as_posix(),
            'schema': parse_template(read_text(template, 'TASK template', MAX_TEMPLATE_BYTES))}


def main():
    arguments = build_parser().parse_args()
    try:
        context = build_context(arguments)
        result = COMMANDS[arguments.command](arguments, context)
        status = result.pop('exit_status', 0) if isinstance(result, dict) else 0
        # Every other command reports, but never repairs, a store that needs linting.
        notice = lint_notice(context) if arguments.command != 'lint' else None
        if notice and isinstance(result, dict):
            result['lint_notice'] = notice
        elif notice:
            print('profile_env.py: ' + notice['message'], file=sys.stderr)
        if result is not None:
            print(json.dumps(result, sort_keys=True))
        return status
    except (ProfileError, OSError, RuntimeError) as error:
        print('profile_env.py: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
