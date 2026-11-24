#!/usr/bin/env python3
"""Print only the doc sections a task needs.

usage: ai-context.py list | [--dedupe] <topic> [<topic>...] | check | --version

Topics live in wiki/ai-context.json. A source is a whole file or one exact
heading (the section runs to the next heading of the same or higher level).
A source may set "frontmatter": true to exclude a closed opening YAML-style
envelope from heading discovery; whole-file output and default behavior stay unchanged.
check also fails on orphans, so docs cannot silently drift out of the router:
wiki pages no topic loads, history files missing from the router index, and
nested AGENTS.md files no topic loads, opted-in indexed pages no instructions name, and relative Markdown links are checked.
Set "okfReservedPages" to true to exempt index.md and log.md under the wiki
from orphan checks; relative links in those pages are still checked.
Mounted roots have independent topic namespaces and configs; check excludes
their subtrees from the outer wiki scan and checks each root separately.
List bulky trees that hold no instructions under "skipDirs" (exact paths or
case-sensitive fnmatch globs) to keep check from walking them; the wiki is walked
except for mounted subtrees, which are checked under their own configs.
List deliberate routing exceptions under
"unrouted" in the config as exact paths or case-sensitive fnmatch globs,
each with a reason. Keys match themselves and other names via fnmatch, regardless
of existence; use wiki/file[[]1].md to exempt the literal wiki/file[1].md
without matching wiki/file1.md.
Keys normalize backslashes to /; * also matches /.
Copy this file to <repo>/scripts/ai-context.py; the repo root is its parent's parent.
A symlink outside a scripts/ directory (e.g. on PATH) whose own parent's parent
has no wiki/ai-context.json uses its target's parent's parent, unless
AI_CONTEXT_CONFIG is set; only runs that would fail on a missing config change.
For a shared installation, set AI_CONTEXT_ROOT and optionally AI_CONTEXT_CONFIG
(default: <root>/wiki/ai-context.json). Explicit relative overrides resolve from
the invocation cwd independently; relative paths inside the config resolve from ROOT.
Empty or unset overrides use the defaults.
No dependencies beyond the Python 3.8+ standard library.
"""
import fnmatch, json, os, posixpath, re, stat, sys, unicodedata
from collections import namedtuple
from urllib.parse import unquote
from html import unescape
from html.entities import html5

VERSION = '0.5.0'  # x-release-please-version


def script_root():
    """The script's parent's parent, or its symlink target's when that is the only way to a config."""
    path = os.path.abspath(__file__)
    root = os.path.dirname(os.path.dirname(path))
    if (os.path.islink(path) and not os.environ.get('AI_CONTEXT_CONFIG')
            and os.path.basename(os.path.dirname(path)).lower() != 'scripts'
            and not os.path.exists(os.path.join(root, 'wiki', 'ai-context.json'))):
        root = os.path.dirname(os.path.dirname(os.path.realpath(path)))
    return root


ROOT = os.path.realpath(os.environ.get('AI_CONTEXT_ROOT') or script_root())
CFG_PATH = os.path.realpath(os.environ.get('AI_CONTEXT_CONFIG') or os.path.join(ROOT, 'wiki', 'ai-context.json'))
HEAD = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
FENCE = re.compile(r'^\s{0,3}(`{3,}|~{3,})')
LINK_FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')
BLOCK_HTML = re.compile(r'^ {0,3}</?(?:address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?:\s|/?>|$)', re.I)
THEMATIC = re.compile(r' {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})')
LIST_MARKER = re.compile(r'^ {0,3}(?:[-+*]|[0-9]{1,9}[.)])(?:[ \t]+|$)')
CONTAINER_LEAD = re.compile(r'(?:[ \t>]|(?:[-+*]|[0-9]{1,9}[.)])(?=[ \t]|$))*')
BLOCK_HEADING = re.compile(r'^ {0,3}#{1,6}(?:[ \t]|$)')
TITLE = r'(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\((?:\\.|[^)\\])*\))'
HTML_ATTRIBUTE = r"[A-Za-z_:][A-Za-z0-9_.:-]*(?:[ \t\r\n]*=[ \t\r\n]*(?:[^ \t\r\n\"'=<>`]+|'[^']*'|\"[^\"]*\"))?"
HTML_TAG = re.compile(r'</[A-Za-z][A-Za-z0-9-]*[ \t\r\n]*>|<[A-Za-z][A-Za-z0-9-]*(?:[ \t\r\n]+' + HTML_ATTRIBUTE + r')*[ \t\r\n]*/?>')

PUNCTUATION = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
BACKTICKS = re.compile(r'`+')
BLANK_LINE = re.compile(r'\n[ \t]*\n')
WHITESPACE = re.compile(r'[ \t\r\n]*')
INLINE_END = re.compile(r'(?:\s+' + TITLE + r')?\s*\)')
AUTOLINK = re.compile(r'<(?:[A-Za-z][A-Za-z0-9+.-]{1,31}:[^<>\x00-\x20]*|[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+)>')
INLINE_HTML = re.compile(r'<!--(?:(?!-->)[\s\S])*-->|<\?[\s\S]*?\?>|<![A-Z][\s\S]*?>|<!\[CDATA\[[\s\S]*?\]\]>|' + HTML_TAG.pattern)
DEFINITION_START = re.compile(r'^ {0,3}\[((?:\\.|[^\]\\])+)\]:')
DEFINITION_END = re.compile(r'(?:(?=[ \t\n])[ \t]*(?:\n[ \t]*)?' + TITLE + r')?[ \t]*(?:\n|$)')


def load_cfg(path=None, root=None):
    if path is None and not os.path.exists(CFG_PATH):
        sys.exit(f'missing {CFG_PATH}; copy this script to <repo>/scripts/ and create wiki/ai-context.json, or set AI_CONTEXT_ROOT and AI_CONTEXT_CONFIG for a shared installation')
    return json.loads(read_text(CFG_PATH if path is None else path, root,
                                f'config {path}: outside root {root}'))


def inside_root(path, root, allow_root=False):
    """Compare physical path components, including anchors and drive boundaries."""
    try:
        identity = root if isinstance(root, PhysicalPath) else PhysicalPath(root)
        return identity.contains(path, allow_root=allow_root)
    except (OSError, ValueError):
        return False


def case_alias_candidate(path, root):
    """Cheap rejection only; filesystem identity must still confirm an alias."""
    path, root = (unicodedata.normalize('NFD', value).casefold() for value in (path, root))
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


class PhysicalPath:
    """A physical root resolved once for a bounded operation, never globally cached."""
    def __init__(self, path):
        self.path = os.path.normcase(os.path.realpath(path))
        self.identity = None

    def contains(self, path, allow_root=False):
        path = os.path.normcase(os.path.realpath(path))
        try:
            if os.path.commonpath([path, self.path]) == self.path:
                return allow_root or path != self.path
        except (OSError, ValueError):
            pass

        # Reject unrelated trees before touching their filesystem metadata.
        # Case folding is only a filter, never proof of physical containment.
        if not case_alias_candidate(path, self.path):
            return False
        if self.identity is None:
            try:
                info = os.stat(self.path)
                self.identity = (info.st_dev, info.st_ino)
            except (OSError, ValueError):
                return False
        current, depth = path, 0
        while True:
            try:
                info = os.stat(current)
                if (info.st_dev, info.st_ino) == self.identity:
                    return allow_root or depth > 0
            except (OSError, ValueError):
                pass
            parent = os.path.dirname(current)
            if parent == current:
                return False
            current, depth = parent, depth + 1


def read_text(path, root=None, outside='outside repo', scope=None):
    if root is not None and not inside_root(path, scope or root):
        raise ValueError(outside)
    with open(path, encoding='utf-8') as document:
        return document.read()


def excluded_path(path, excluded_roots):
    return any(inside_root(path, owner, allow_root=True) for owner in excluded_roots)


def owner_relative(path, owner, preserve_name=False):
    """Return a physical path's identity relative to owner, handling case aliases."""
    path, owner = os.path.abspath(path), os.path.realpath(owner)
    try:
        if os.path.commonpath([path, owner]) == owner:
            return os.path.relpath(path, owner)
    except (OSError, ValueError):
        pass

    parts, current = [], path
    if preserve_name:
        parts.append(os.path.basename(current))
        current = os.path.dirname(current)
    while True:
        try:
            if os.path.samefile(current, owner):
                return os.path.join(*reversed(parts)) if parts else '.'
        except (OSError, ValueError):
            pass
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.relpath(path, owner)
        parts.append(os.path.basename(current))
        current = parent


def inventory_name(path, root):
    """Physical owner-relative identity, never a replacement for a link's base."""
    path = os.path.realpath(os.path.join(root, path.replace('\\', '/')))
    return os.path.normcase(owner_relative(path, root)).replace(os.sep, '/')


def diagnostic(value):
    """Keep a mounted diagnostic on one line without changing ordinary Unicode."""
    return ''.join(f'\\x{ord(c):02x}' if unicodedata.category(c) == 'Cc' else c
                   for c in str(value)).encode('utf-8', 'backslashreplace').decode('utf-8')


def configured_path(value, root, field, allow_root=False):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError(f'{field}: expected a nonempty path string without NUL')
    if any(unicodedata.category(c) == 'Cs' for c in value):
        raise ValueError(f'{field}: path must not contain surrogates')
    path = os.path.abspath(os.path.join(root, value.replace('\\', '/')))
    if not inside_root(path, root, allow_root=allow_root):
        raise ValueError(f'{field} {value}: outside root {root}')
    return path


Mount = namedtuple('Mount', 'name root config_path error')


class MissingMount(ValueError):
    """Only a safely contained root that stat could not find is optional in list."""


def valid_mount_name(name):
    return (isinstance(name, str) and bool(name) and name not in ('.', '..')
            and not any(c in '/\\' or c.isspace() or unicodedata.category(c) in ('Cc', 'Cs') for c in name))


def mount_entries(cfg, root=None):
    root = ROOT if root is None else root
    declarations = cfg.get('mounts', {})
    if not isinstance(declarations, dict):
        raise ValueError('mounts: expected an object')
    if not declarations:
        return []
    protected = []
    wiki_value = cfg.get('wikiDir', 'wiki')
    for field, value in [('wikiDir', wiki_value),
                         ('historyDir', cfg.get('historyDir', f'{wiki_value}/history'))]:
        try:
            path = os.path.realpath(configured_path(value, root, field, allow_root=True))
            protected.append((field, path, value))
        except (OSError, ValueError):
            pass  # The outer check reports an invalid inventory path separately.
    for field, value in [('config', CFG_PATH),
                         ('rootInstructions', cfg.get('rootInstructions', 'AGENTS.md'))]:
        try:
            path = value if field == 'config' else configured_path(value, root, field)
            protected.append((field, os.path.realpath(path), value))
        except (OSError, TypeError, ValueError):
            # The outer check reports an invalid protected path separately.
            continue
    entries = []
    for name, declaration in declarations.items():
        mounted_root = config_path = error = None
        # Resolve a safe root even if another declaration field is invalid:
        # ownership of that subtree must not depend on a readable config.
        try:
            if isinstance(declaration, dict) and 'root' in declaration:
                mounted_root = os.path.realpath(configured_path(declaration['root'], root, 'root'))
            if not valid_mount_name(name):
                raise ValueError('name: expected a nonempty single segment without whitespace, controls or surrogates')
            if not isinstance(declaration, dict):
                raise ValueError('declaration: expected an object')
            if 'root' not in declaration:
                raise ValueError('root: required path')
            unknown = set(declaration) - {'root', 'config'}
            if unknown:
                raise ValueError(f'declaration: unknown field {sorted(unknown)[0]}')
            config_path = configured_path(declaration.get('config', 'wiki/ai-context.json'),
                                          mounted_root, 'config')
            if any(topic.startswith(name + '/') for topic in cfg['topics']):
                raise ValueError(f'namespace collision: local topic reserves {name}/')
            root_identity = PhysicalPath(mounted_root)
            for field, path, display in protected:
                if root_identity.contains(path, allow_root=True):
                    raise ValueError(f'root {declaration["root"]}: contains outer {field} {display}')
        except (OSError, ValueError) as failure:
            error = str(failure)
        entries.append(Mount(name, mounted_root, config_path, error))
    errors = [entry.error for entry in entries]
    identities = [PhysicalPath(entry.root) if entry.root is not None else None for entry in entries]
    for index, entry in enumerate(entries):
        if identities[index] is None:
            continue
        for other_index in range(index):
            other = entries[other_index]
            if identities[other_index] is None:
                continue
            entry_in_other = identities[other_index].contains(entry.root, allow_root=True)
            other_in_entry = identities[index].contains(other.root, allow_root=True)
            if entry_in_other == other_in_entry:
                continue  # The same physical root may have multiple names.
            for current_index, other_mount in ((index, other), (other_index, entry)):
                message = (f'root {declarations[entries[current_index].name]["root"]}: strict '
                           f'ancestor/descendant overlap with mount {other_mount.name} '
                           f'({declarations[other_mount.name]["root"]})')
                errors[current_index] = (errors[current_index] + '; ' + message
                                         if errors[current_index] else message)
    return [entry._replace(error=errors[index]) for index, entry in enumerate(entries)]


def validate_defaults(cfg):
    for field in ('stripFrontmatter', 'compactPathLinks', 'okfReservedPages'):
        if not isinstance(cfg.get(field, False), bool):
            raise ValueError(f'{field}: expected a boolean')


def validate_mounted_cfg(cfg, root):
    """Validate only shapes used by this router; leave legacy outer configs alone."""
    if not isinstance(cfg, dict):
        raise ValueError('config: expected an object')
    topics = cfg.get('topics')
    if not isinstance(topics, dict):
        raise ValueError('topics: expected an object')
    mounts = cfg.get('mounts', {})
    if not isinstance(mounts, dict):
        raise ValueError('mounts: expected an object')
    if mounts:
        raise ValueError('nested mounts are not supported')
    budgets = cfg.get('budgets', {})
    if not isinstance(budgets, dict):
        raise ValueError('budgets: expected an object')
    def cap(value, field):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f'{field}: expected a nonnegative integer')
    for field in ('rootInstructionsMaxBytes', 'defaultTopicMaxBytes'):
        if field in budgets:
            cap(budgets[field], 'budgets.' + field)
    for field in ('rootInstructions', 'wikiDir', 'historyDir', 'routerFile'):
        if field in cfg:
            configured_path(cfg[field], root, field, allow_root=field in ('wikiDir', 'historyDir'))
    for field in ('indexed', 'skipDirs'):
        if field in cfg and (not isinstance(cfg[field], list)
                             or any(not isinstance(item, str) for item in cfg[field])):
            raise ValueError(f'{field}: expected a list of strings')
    if not isinstance(cfg.get('unrouted', {}), dict):
        raise ValueError('unrouted: expected an object')
    for name, topic in topics.items():
        field = f'topics.{name}'
        if (not isinstance(name, str) or not name
                or any(unicodedata.category(c) == 'Cs' for c in name)):
            raise ValueError('topics: expected nonempty topic names without surrogates')
        if not isinstance(topic, dict):
            raise ValueError(f'{field}: expected an object')
        description = topic.get('description')
        if (not isinstance(description, str)
                or any(unicodedata.category(c) == 'Cs' for c in description)):
            raise ValueError(f'{field}.description: expected a string without surrogates')
        if 'maxBytes' in topic:
            cap(topic['maxBytes'], field + '.maxBytes')
        sources = topic.get('sources')
        if not isinstance(sources, list):
            raise ValueError(f'{field}.sources: expected a list')
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError(f'{field}.sources: expected source objects')
            configured_path(source.get('path'), root, field + '.sources.path')
            if 'heading' in source and not isinstance(source['heading'], str):
                raise ValueError(f'{field}.sources.heading: expected a string')
            if 'frontmatter' in source and not isinstance(source['frontmatter'], bool):
                raise ValueError(f'{field}.sources.frontmatter: expected a boolean')
            if 'stripFrontmatter' in source and not isinstance(source['stripFrontmatter'], bool):
                raise ValueError(f'{field}.sources.stripFrontmatter: expected a boolean')
    validate_defaults(cfg)


def load_mount(entry):
    if entry.error:
        raise ValueError(entry.error)
    try:
        info = os.stat(entry.root)
    except FileNotFoundError:
        raise MissingMount(f'missing root {entry.root}')
    except OSError as error:
        raise ValueError(f'root {entry.root}: {error}') from error
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f'root {entry.root}: expected a directory')
    try:
        path = configured_path(entry.config_path, entry.root, 'config')
        if not stat.S_ISREG(os.stat(path).st_mode):
            raise ValueError(f'config {path}: expected a regular file')
        cfg = load_cfg(path, root=entry.root)
    except UnicodeError as error:
        raise ValueError(f'config {entry.config_path}: invalid UTF-8: {error}') from error
    except json.JSONDecodeError as error:
        raise ValueError(f'config {entry.config_path}: invalid JSON: {error}') from error
    except OSError as error:
        raise ValueError(f'config {entry.config_path}: {error}') from error
    validate_mounted_cfg(cfg, entry.root)
    return cfg


def frontmatter_end(lines):
    """Return the end of a closed leading frontmatter envelope, without parsing YAML."""
    if not lines or lines[0].lstrip('\ufeff').rstrip(' \t\r') != '---':
        return 0
    for i in range(1, len(lines)):
        if lines[i].rstrip(' \t\r') in ('---', '...'):
            return i + 1
    # A leading thematic break without a closing delimiter is ordinary Markdown.
    return 0


def headings(lines, frontmatter=False):
    """Yield original line indexes, ignoring opted-in frontmatter and fenced code."""
    fence = None
    start = frontmatter_end(lines) if frontmatter else 0
    for i, ln in enumerate(lines):
        if i < start:
            continue
        m = FENCE.match(ln)
        if m:
            mark = m.group(1)
            if fence is None:
                fence = mark[0] * len(mark)
            elif mark.startswith(fence):
                fence = None
            continue
        if fence is None and (h := HEAD.match(ln)):
            yield i, len(h.group(1)), h.group(2)


def section(src, root=None, scope=None, strip_default=False):
    """Return one source. A source's stripFrontmatter (else the config default) drops
    a closed leading frontmatter envelope from the output and from heading discovery."""
    root = ROOT if root is None else root
    scope = scope or PhysicalPath(root)
    frontmatter = src.get('frontmatter', False)
    if not isinstance(frontmatter, bool):
        raise ValueError(f'{src["path"]}: frontmatter: expected a boolean')
    strip = src.get('stripFrontmatter', strip_default)
    if not isinstance(strip, bool):
        where = f'{src["path"]}: ' if 'stripFrontmatter' in src else ''
        raise ValueError(f'{where}stripFrontmatter: expected a boolean')
    frontmatter = frontmatter or strip
    path = os.path.realpath(os.path.join(root, src['path'].replace('\\', '/')))
    if not inside_root(path, scope):
        raise ValueError(f'{src["path"]}: outside repo')
    if not stat.S_ISREG(os.stat(path).st_mode):
        raise ValueError(f'{src["path"]}: expected a regular file')
    lines = read_text(path, root, f'{src["path"]}: outside repo', scope=scope).split('\n')
    if 'heading' not in src:
        return '\n'.join(lines[frontmatter_end(lines) if strip else 0:]).strip()
    hs = list(headings(lines, frontmatter=frontmatter))
    hits = [(i, lv) for i, lv, t in hs if t == src['heading']]
    if len(hits) != 1:  # fail closed: a renamed or duplicated heading must not load the wrong text
        raise ValueError(f'{src["path"]}: heading {src["heading"]!r} found {len(hits)}x')
    start, level = hits[0]
    end = next((i for i, lv, _ in hs if i > start and lv <= level), len(lines))
    return '\n'.join(lines[start:end]).strip()


# A plain relative path: no spaces, escapes, entities, percent-encoding or code
# markers, so the text is the path it names.
PATH_LINK = re.compile(r'\[([A-Za-z0-9._~/+-]+)\]\(([A-Za-z0-9._~/+-]+)\)')


# Links resolve from the configured source path, not a symlink's target, as link_problems does.
def compact_path_links(body, source, root=None, display_root=None):
    """Print parser-recognized plain path links as their root-relative paths."""
    owner = ROOT if root is None else root
    base = owner_relative(os.path.dirname(os.path.abspath(os.path.join(owner, source.replace('\\', '/')))),
                          owner).replace(os.sep, '/')
    lines = body.split('\n')
    # The block scanner expands tabs in container prefixes before computing spans.
    offsets, original, expanded = [], 0, 0
    for line in lines:
        lead = line[:CONTAINER_LEAD.match(line).end()]
        width = len(lead.expandtabs(4)) - len(lead)
        offsets.append(original - expanded - width)
        original += len(line) + 1
        expanded += len(line) + width + 1
    pieces, last = [], 0
    for number, _, start, end in link_destinations(lines, spans=True):
        start, end = start + offsets[number - 1], end + offsets[number - 1]
        match = PATH_LINK.fullmatch(body[start:end])
        if not match:
            continue
        path, dest = match.groups()
        if (path.startswith('/') or
                posixpath.normpath(path) != posixpath.normpath(posixpath.join(base, dest))):
            continue
        path = posixpath.normpath(path)
        if display_root is not None:
            path = os.path.relpath(os.path.join(owner, path), display_root).replace(os.sep, '/')
        if '`' in path:
            continue  # A mount directory name with a backtick cannot print as a plain code span.
        pieces.append(body[last:start])
        if ''.join(pieces[-2:]).endswith('`'):
            pieces.append('<!-- -->')  # Keep adjacent code delimiters distinct.
        pieces.append(f'`{path}`' + '<!-- -->' * (body[end:end + 1] == '`'))
        last = end
    pieces.append(body[last:])
    return ''.join(pieces)


def render(cfg, name, root=None, display_root=None, scope=None, seen=None):
    """Render one topic. With seen, omit exact sources an earlier topic already printed."""
    out, current = [], set()
    for s in cfg['topics'][name]['sources']:
        where = s['path']
        if display_root is not None:
            where = os.path.relpath(os.path.join(ROOT if root is None else root,
                                               where.replace('\\', '/')), display_root).replace(os.sep, '/')
        where += f' § {s["heading"]}' if 'heading' in s else ''
        body = section(s, root=root, scope=scope,
                       strip_default=cfg.get('stripFrontmatter', False))  # validate even when omitted
        if cfg.get('compactPathLinks', False):
            body = compact_path_links(body, s['path'], root=root, display_root=display_root)
        # Same owner root and identical source entry only: overlapping sections,
        # other path spellings and repeats inside one topic are kept.
        key = (ROOT if root is None else root, json.dumps(s, sort_keys=True))
        current.add(key)
        if seen is None or key not in seen:
            out.append(f'<!-- {where} -->\n{body}')
    if seen is not None:
        seen.update(current)
    return '\n\n'.join(out)


def indexed_prefixes(indexed):
    """The literal text each indexed pattern starts with; every match starts with it."""
    return [os.path.normcase(re.split(r'[*?\[]', p, maxsplit=1)[0]) for p in indexed]


def may_hold_indexed(rel_dir, prefixes):
    """Whether a file below repo-relative rel_dir could match an indexed pattern."""
    path = os.path.normcase(rel_dir + '/')
    return any(path.startswith(p) or p.startswith(path) for p in prefixes)


def skip_patterns(cfg):
    """Configured skipDirs as forward-slash patterns, or None when the value is invalid."""
    value = cfg.get('skipDirs', [])
    if not isinstance(value, list) or any(not isinstance(p, str) for p in value):
        return None
    return [p.replace('\\', '/').rstrip('/') for p in value]


def wiki_path(rel, wiki, traversing=False, root=None):
    """Wiki membership, optionally including ancestors needed for traversal."""
    if root is not None:
        rel = os.path.normcase(rel).replace(os.sep, '/')
        wiki = inventory_name(wiki, root)
    return ((root is not None and wiki == '.') or rel == wiki or rel.startswith(wiki + '/')
            or (traversing and wiki.startswith(rel + '/')))


def skipped_dir(rel, patterns, wiki, traversing=False, root=None):
    """Whether a directory is skipped; traversal may retain the path to the wiki."""
    if wiki_path(rel, wiki, traversing=traversing, root=root):
        return False
    parts = rel.split('/')
    return any(path == p or fnmatch.fnmatchcase(path, p)
               for path in ('/'.join(parts[:i]) for i in range(1, len(parts) + 1)) for p in patterns)


def child_dir(base, name):
    """The repo-relative path of directory name under walk directory base."""
    return name if base == '.' else f'{base}/{name}'


def inventory_exemptions(paths, owner):
    exemptions = {inventory_name(path, owner) for path in paths}
    for path in paths:
        path = os.path.join(owner, path.replace('\\', '/'))
        # Resolve parent aliases but retain the configured file's own name.
        path = os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path))
        exemptions.add(os.path.normcase(owner_relative(path, owner, preserve_name=True))
                       .replace(os.sep, '/'))
    return exemptions


def history_indexed(path, rel, wiki, router_text, cfg, root=None):
    references = [os.path.relpath(rel, wiki).replace(os.sep, '/'), rel]
    if root is not None:
        configured_wiki = cfg.get('wikiDir', 'wiki')
        configured_history = cfg.get('historyDir', f'{configured_wiki}/history')
        lexical_wiki, lexical_history = (os.path.abspath(os.path.join(root, name.replace('\\', '/')))
                                         for name in (configured_wiki, configured_history))
        lexical = os.path.join(lexical_history, owner_relative(path, lexical_history))
        relative = owner_relative(lexical, root)
        references += [os.path.relpath(relative, owner_relative(lexical_wiki, root)).replace(os.sep, '/'),
                       relative.replace(os.sep, '/')]
    return any(reference in router_text for reference in references)


def orphans(cfg, reference_text='', root=None, excluded_roots=(), scope=None):
    """Docs that exist on disk but that no agent can reach through the router."""
    owner = ROOT if root is None else root
    scope = scope or PhysicalPath(owner)
    excluded_roots = tuple(path if isinstance(path, PhysicalPath) else PhysicalPath(path)
                           for path in excluded_roots)
    indexed = cfg.get('indexed', [])
    if not isinstance(indexed, list) or any(not isinstance(p, str) for p in indexed):
        return ['indexed: expected a list of strings']
    skip_dirs = skip_patterns(cfg)
    if skip_dirs is None:
        return ['skipDirs: expected a list of strings']
    wiki = cfg.get('wikiDir', 'wiki')
    okf = cfg.get('okfReservedPages', False)
    history = cfg.get('historyDir', f'{wiki}/history')
    router = cfg.get('routerFile', f'{wiki}/README.md')
    root_file = cfg.get('rootInstructions', 'AGENTS.md')
    routed = {s['path'].replace('\\', '/') for t in cfg['topics'].values() for s in t['sources']}
    if root is not None:
        try:
            for field, value in [('wikiDir', wiki), ('historyDir', history)]:
                configured_path(value, owner, field, allow_root=True)
        except ValueError as error:
            return [str(error)]
        exemptions = inventory_exemptions((root_file, router), owner)
        routed = {inventory_name(path, owner) for path in routed}
        wiki, history, root_file = (inventory_name(path, owner) for path in (wiki, history, root_file))
    allowed = {p.replace('\\', '/'): reason for p, reason in cfg.get('unrouted', {}).items()}
    try:
        router_text = section({'path': router}, root=root, scope=scope)
    except (ValueError, OSError):
        router_text = ''  # link_problems reports the invalid or unreadable router.
    reference_text += '\n' + router_text
    if root is not None:
        router = inventory_name(router, owner)
    bad = []
    skip = {'.git', 'node_modules', 'dist', 'build', 'vendor', '.venv', 'target'}
    prefixes = indexed_prefixes(indexed)
    def walk_error(error):
        rel = os.path.relpath(error.filename or owner, owner).replace(os.sep, '/')
        bad.append(f'{rel}: cannot scan directory: {error}')
    for d, dirs, files in os.walk(owner, onerror=walk_error if root is not None else None):
        base = os.path.relpath(d, owner).replace(os.sep, '/')
        dirs[:] = [x for x in dirs if x != '.git' and
                   not excluded_path(os.path.join(d, x), excluded_roots) and
                   (root is None or inside_root(os.path.join(d, x), scope, allow_root=True)) and
                   ((root is not None and wiki_path(child_dir(base, x), wiki, traversing=True, root=root)) or
                    (x not in skip and not x.startswith('.')) or
                    may_hold_indexed(child_dir(base, x), prefixes)) and
                   not skipped_dir(child_dir(base, x), skip_dirs, wiki, traversing=True, root=root)]
        if base != '.' and skipped_dir(base, skip_dirs, wiki, root=root):
            continue
        for f in files:
            path = os.path.join(d, f)
            if excluded_path(path, excluded_roots):
                continue
            rel = os.path.relpath(path, owner).replace(os.sep, '/')
            if not f.endswith('.md'):
                continue
            identity = rel if root is None else inventory_name(path, owner)
            scanned = rel if root is None else os.path.normcase(rel).replace(os.sep, '/')
            reasons = [reason for pattern, reason in allowed.items()
                       if rel == pattern or fnmatch.fnmatchcase(rel, pattern)]
            if (any(fnmatch.fnmatch(rel, pattern) for pattern in indexed)
                    and identity not in routed and rel not in reference_text
                    and not any(isinstance(reason, str) and reason.strip() for reason in reasons)):
                bad.append(f'{rel}: indexed page not named (name it in a topic page, route it, or list it under "unrouted" with a reason)')
            if (reasons or (not (root is not None and wiki_path(scanned, wiki, root=root))
                            and any(x in skip or x.startswith('.') for x in rel.split('/')[:-1]))):
                continue
            # Membership and exemptions follow the scanned path, not its target.
            if root is not None and scanned in exemptions:
                continue
            if okf and f in ('index.md', 'log.md') and wiki_path(scanned, wiki, root=root):
                continue
            if scanned.startswith(history + '/') or (root is not None and history == '.'):
                if not history_indexed(path, rel, wiki, router_text, cfg, root=root):
                    bad.append(f'{rel}: history file not indexed in {router}')
            elif scanned.startswith(wiki + '/') or (root is not None and wiki == '.'):
                if (scanned != router and identity not in routed
                        and (root is None or scanned != root_file)):
                    bad.append(f'{rel}: wiki page no topic loads (map it, or list it under "unrouted" with a reason)')
            elif f == 'AGENTS.md' and scanned != root_file and identity not in routed:
                bad.append(f'{rel}: scoped instructions no topic loads')
    return bad


MARKDOWN_ESCAPE = re.compile(r'\\([' + re.escape(PUNCTUATION) + r'])|&(?:\#(?:[xX][0-9A-Fa-f]{1,6}|[0-9]{1,7})|[A-Za-z][A-Za-z0-9]{1,31});')


def decode_markdown_token(match):
    """Decode a Markdown escape or a complete, recognized character reference."""
    token = match.group()
    if match.group(1):
        return match.group(1)
    return unescape(token) if token.startswith('&#') or token[1:] in html5 else token


def markdown_unescape(value):
    return MARKDOWN_ESCAPE.sub(decode_markdown_token, value)


def destination(text, start, end=None):
    """Read an angle-wrapped or balanced bare Markdown destination."""
    end = len(text) if end is None else end
    start = WHITESPACE.match(text, start, end).end()
    angle = text[start:start + 1] == '<'
    pos, depth = start + angle, 0
    begin = pos
    while pos < end:
        char = text[pos]
        if char == '\\' and pos + 1 < end and text[pos + 1] in PUNCTUATION:
            pos += 2
            continue
        if angle:
            if char == '>':
                return text[begin:pos], pos + 1
            if char in '<\n':
                break
        else:
            if char.isspace() or (char == ')' and depth == 0):
                return (text[begin:pos], pos) if depth == 0 else None
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
        pos += 1
    if not angle and depth == 0:
        return text[begin:pos], pos
    return None


def reference_definition(text):
    """Read one complete definition and its exact consumed line count."""
    match = DEFINITION_START.match(text)
    found = destination(text, match.end()) if match and valid_label(match[1]) else None
    # Only <> may be empty; a definition needs a bare destination.
    if not found or (not found[0] and not text[:found[1]].endswith('>')) or BLANK_LINE.search(text, 0, found[1]):
        return None
    tail = DEFINITION_END.match(text, found[1], len(text))
    if tail:
        end = tail.end()
        return match[1], found[0], text.count('\n', 0, end) + (text[end - 1:end] != '\n')
    return None


def indent_prefix(text, minimum=None, start=0):
    """Return consumed characters and indentation columns without expanding text."""
    pos, column = 0, start
    while pos < len(text) and text[pos] in ' \t' and (minimum is None or column - start < minimum):
        column += 1 if text[pos] == ' ' else 4 - column % 4
        pos += 1
    return pos, column - start


def list_padding(content, marker, base=0):
    """Return marker prefix, list indentation, and any partially consumed tab."""
    start = re.match(r'^ {0,3}(?:[-+*]|[0-9]{1,9}[.)])', content).end()
    padding, columns = indent_prefix(content[start:marker.end()], start=base + start)
    if columns <= 4:
        return marker.end(), base + start + max(columns, 1), base + start + columns, 0
    first_columns = indent_prefix(content[start:start + 1], start=base + start)[1]
    return start + 1, base + start + 1, base + start + first_columns, first_columns - 1


def list_interrupts(content, marker):
    """A new list interrupts a paragraph only with content and start number 1."""
    if not content[marker.end():].strip():
        return False
    ordered = re.match(r'([0-9]{1,9})[.)]', content.lstrip())
    return not ordered or ordered[1].lstrip('0') == '1'


def title_continuations(lines):
    """A title continuation cannot consume a line starting a new block."""
    for line in lines:
        fence = LINK_FENCE.match(line)
        if (BLOCK_HEADING.match(line) or THEMATIC.fullmatch(line) or LIST_MARKER.match(line)
                or re.fullmatch(r' {0,3}(?:=+|-+)[ \t]*', line)
                or (fence and (fence[1][0] == '~' or '`' not in line[fence.end():]))
                or BLOCK_HTML.match(line)
                or re.match(r'^ {0,3}<(?:pre|script|style|textarea)(?:\s|>|$)', line, re.I)
                or re.match(r'^ {0,3}(?:<!--|<\?|<![A-Z]|<!\[CDATA\[)', line)):
            return
        yield line


def title_closed(line, closing):
    """Match a trailing title delimiter preceded by an even backslash run."""
    line = line.rstrip(' \t')
    if not line.endswith(closing):
        return False
    prefix = line[:-1]
    return (len(prefix) - len(prefix.rstrip('\\'))) % 2 == 0


def definition_candidate(lines, index, content, depth, list_indent):
    """Collect only a possible definition and its optional continuation title."""
    candidate = [content]
    def following():
        for following_index in range(index + 1, len(lines)):
            line = container_prefix(lines[following_index], list_indent)[0]
            quote = re.match(r'^(?: {0,3}>[ \t]?)+', line)
            end = quote.end() if quote else 0
            text = line[end:]
            if line[:end].count('>') != depth or not text.strip():
                return
            characters, columns = indent_prefix(text, list_indent)
            if columns < list_indent:
                return
            yield text[characters:]
    rest = iter(following())
    text = content
    # A label may span lines, but CommonMark limits it to 999 characters.
    while not DEFINITION_START.match(text) and len(text) <= 1002:
        if not text.lstrip().startswith('[') or ']' in re.sub(r'\\.', '', text):
            return None
        next_line = next(rest, None)
        if next_line is None:
            return None
        candidate.append(next_line)
        text = '\n'.join(candidate)
    match = DEFINITION_START.match(text)
    if not match or not valid_label(match[1]):
        return None
    if not text[match.end():].strip():
        next_line = next(rest, None)
        if next_line is not None:
            candidate.append(next_line)
            text = '\n'.join(candidate)
    definition = reference_definition(text)
    if not definition:
        found = destination(text, match.end())
        tail = text[found[1]:].lstrip() if found else ''
        if not tail.startswith(('"', "'", '(')):
            return None
        closing = ')' if tail[0] == '(' else tail[0]
        for next_line in title_continuations(rest):
            candidate.append(next_line)
            if title_closed(next_line, closing):
                break
        return reference_definition('\n'.join(candidate))
    # A title can start on the following line and span more than one line.
    title_rest = iter(title_continuations(rest))
    next_line = next(title_rest, None)
    if next_line is not None and next_line.lstrip().startswith(('"', "'", '(')):
        candidate.append(next_line)
        closing = ')' if next_line.lstrip()[0] == '(' else next_line.lstrip()[0]
        fragment = next_line.lstrip()[1:]
        while not title_closed(fragment, closing):
            next_line = next(title_rest, None)
            if next_line is None:
                break
            candidate.append(next_line)
            fragment = next_line
        extended = reference_definition('\n'.join(candidate))
        if extended:
            return extended
    return definition


def leading_quote(line, list_indent, open_lists=None):
    """Keep an outer quote's indentation ahead of a nested list quote.

    With open_lists, measure against the list opened inside those outer quotes.
    """
    if open_lists is not None:
        ends = [0]
        while True:
            token = re.match(r' {0,3}>[ \t]?', line[ends[-1]:])
            if not token:
                break
            ends.append(ends[-1] + token.end())
        # Try the deepest split first: k outer quotes, then a list's spaces, then another '>'.
        for depth in range(len(ends) - 1, 0, -1):
            space = re.match(r'[ \t]+(?=>)', line[ends[depth]:])
            inside = [width for width, quote_at in open_lists if quote_at == depth]
            if space and inside and indent_prefix(space.group())[1] >= inside[-1]:
                return ends[depth], [line[:ends[depth]]], inside[-1]
        return 0, [], list_indent
    match = re.match(r'^((?: {0,3}>[ \t]?)+)([ \t]+)>', line)
    if match and list_indent and indent_prefix(match[2])[1] >= list_indent:
        return match.end(1), [match[1]], list_indent
    return 0, [], list_indent


def container_prefix(line, list_indent, open_lists=None):
    """Put quote markers before list prefixes while retaining source offsets.

    Also return, per list marker, how many quote markers precede it and its content indent,
    and the length of the quote prefix. open_lists, as (indent, quote depth) pairs, lets
    leading quotes use the list opened inside them; list_indent is the list ahead of them.
    """
    pos, quotes, inner = leading_quote(line, list_indent, open_lists)
    if quotes:  # Spaces after the leading quotes belong to the list inside them.
        list_indent = inner
    lists, saw_list, saw_quote, nested, indentation, markers = [], False, False, False, 0, []
    while pos < len(line):
        start = pos
        pos += indent_prefix(line[pos:])[0]
        space = line[start:pos]
        indentation += indent_prefix(space)[1]
        if line[pos:pos + 1] == '>' and not (list_indent and not saw_list and not saw_quote and
                                             indentation >= list_indent + 4):
            nested |= saw_list or (list_indent > 0 and indentation >= list_indent)
            saw_quote = True
            end = pos + 1
            if line[end:end + 1] in (' ', '\t'):
                end += 1
            keep = indent_prefix(space, list_indent)[0] if list_indent and not lists and not saw_list else len(space)
            quotes.append(space[keep:] + line[pos:end])  # Columns past the list indent stay before the marker.
            lists.append(space[:keep])
            pos = end
        else:
            match = LIST_MARKER.match(line[pos:])
            if not match or (not saw_list and not quotes and indent_prefix(space)[1] >= 4):
                pos = start
                break
            end, width, _, extra = list_padding(line[pos:], match, len(line[:pos].expandtabs(4)))
            lists.append(space + line[pos:pos + end])
            markers.append((len(quotes), width))
            saw_list, pos = True, pos + end
            if extra or end < match.end():
                break
    return (''.join(quotes + lists) + line[pos:] if nested else line), nested, markers, len(''.join(quotes))


def block_regions(result, eligible):
    """Combine adjacent eligible lines belonging to the same paragraph."""
    offsets = [0]
    for ln in result:
        offsets.append(offsets[-1] + len(ln) + 1)
    regions, previous, ended = [], -2, True
    for index, starts, ends in eligible:
        end = offsets[index] + len(result[index])
        if index == previous + 1 and not starts and not ended:
            regions[-1] = (regions[-1][0], end, regions[-1][2])
        else:
            regions.append((offsets[index], end, index + 1))
        previous, ended = index, ends
    return regions


def open_indent(lists):
    """Return the content indent of the innermost open list item, or 0."""
    return lists[-1][0] if lists else 0


def markdown_text(lines):
    """Mask inactive Markdown contexts without changing line numbers."""
    # Expand tabs among leading container markers so block parsing only sees spaces.
    lines = [line[:CONTAINER_LEAD.match(line).end()].expandtabs(4) + line[CONTAINER_LEAD.match(line).end():]
             for line in lines]
    blank = lambda value: re.sub(r'[^\n]', ' ', value)
    result, definitions, eligible = [], [], []
    consumed, owner = 0, (0, 0)
    fence, raw = None, None
    paragraph, quote_depth = False, 0
    lists = []  # (content indent, quote depth it opened at) of open list items, innermost last.
    for line_index, ln in enumerate(lines):
        if line_index < consumed:
            result.append(blank(ln))
            continue
        column = indent_prefix(ln)[1]
        if re.match(r'[ \t]*>', ln) and any(not quote_at and width > column for width, quote_at in lists):
            # A quote marker left of an outer list item closes that item and everything inside it.
            lists = [(width, quote_at) for width, quote_at in lists if not quote_at and width <= column]
            if owner[1] > column:
                fence, raw = None, None
            if quote_depth:  # The quote inside the closed item ends; this line starts another.
                paragraph, quote_depth = False, 0
        outer = [width for width, quote_at in lists if not quote_at]  # Only these sit ahead of the quote markers.
        source = ln
        ln, nested, markers, quote_end = container_prefix(ln, outer[-1] if outer else 0, lists)
        quote = re.match(r'^(?: {0,3}>[ \t]?)+', ln)
        # The regex would read a moved list indent as the optional space after a bare '>'.
        prefix = quote_end if nested else quote.end() if quote else 0
        depth = ln[:prefix].count('>')
        if fence or raw is not None:
            block = ln if owner[0] else source  # A '>' inside a code block outside quotes is literal.
            inside = None
            if depth >= owner[0]:
                inside = (prefix if owner[0] == depth else
                          re.match(r'^(?: {0,3}>[ \t]?){' + str(owner[0]) + '}', block).end())
            rest = block[inside:] if inside is not None else ''
            # A list marker ahead of the quote starts a new item, which ends a block owned by the old quote.
            new_item = nested and markers and markers[0][0] < owner[0]
            if inside is not None and not new_item and not (
                    owner[1] and rest.strip() and indent_prefix(rest)[1] < owner[1]):
                ln, prefix, depth = block, inside, owner[0]
            else:
                fence, raw, paragraph = None, None, False
        content = ln[prefix:]
        indentation = indent_prefix(content)[1]
        base_column, extra_indent = 0, 0
        reopened = bool(nested and markers and markers[0][0] < depth)  # An item opened before its quote.
        if reopened and not (fence or raw is not None):
            paragraph, quote_depth = False, markers[0][0]  # The new item's quote is a new quote.
        lazy = None
        if paragraph and depth < quote_depth and content.strip():
            # A lazy line keeps the quote open but sits outside the lists opened inside it.
            lazy = lists
            lists = [(width, quote_at) for width, quote_at in lists if quote_at <= depth]
        elif depth != quote_depth:
            if not nested:
                # Leaving a quote keeps the items around it; entering one closes the items it interrupts.
                keep = depth if depth < quote_depth else quote_depth - 1
                lists = [(width, quote_at) for width, quote_at in lists if quote_at <= keep]
            paragraph, quote_depth = False, depth
        sibling = indentation < open_indent(lists) or lazy is not None
        if sibling and content.strip():
            if lazy is None and paragraph:
                lazy = lists  # Restored if the line continues the paragraph.
            lists = [(width, quote_at) for width, quote_at in lists if width <= indentation]
        list_indent = open_indent(lists)
        if list_indent:
            characters, columns = indent_prefix(content, list_indent)
            if columns >= list_indent:
                prefix += characters
                base_column, extra_indent = columns, columns - list_indent
                content = ln[prefix:]
        # A marker moved after the quotes can join the quoted text into a false thematic break.
        thematic = THEMATIC.fullmatch(content) and not reopened
        marker = None if thematic else LIST_MARKER.match(content)
        while (marker and not (fence or raw is not None) and
               (not paragraph or sibling or list_interrupts(content, marker))):
            end, list_indent, base_column, extra_indent = list_padding(content, marker, base_column)
            quote_at, width = markers.pop(0) if markers else (depth, list_indent)
            if not quote_at:  # Reordering moves a quote's padding after an enclosing marker; use the source indent.
                list_indent = width
            lists.append((list_indent, quote_at))
            prefix += end
            content = ln[prefix:]
            paragraph = False
            thematic = THEMATIC.fullmatch(content)
            indent = indent_prefix(content, start=base_column)[1] + extra_indent
            marker = None if thematic or indent >= 4 else LIST_MARKER.match(content)
        indent = indent_prefix(content, start=base_column)[1] + extra_indent
        mark = LINK_FENCE.match(content)
        if fence:
            result.append(blank(ln))
            if mark and mark[1].startswith(fence) and not content[mark.end():].strip():
                fence = None
            paragraph = False
            continue
        if raw is not None:
            result.append(blank(ln))
            if (not raw and not content.strip()) or (raw and re.search(raw, content, re.I)):
                raw = None
            continue
        if indent >= 4 and not paragraph:
            result.append(blank(ln))
            continue
        mark = LINK_FENCE.match(content)
        html = re.match(r'^ {0,3}<(pre|script|style|textarea)(?:\s|>|$)', content, re.I)
        if mark and (mark[1][0] == '~' or '`' not in content[mark.end():]):
            fence = mark[1]
            owner = (depth, list_indent)
            result.append(blank(ln))
            paragraph = False
        elif html:
            raw = r'</' + html[1] + r'\s*>'
            owner = (depth, list_indent)
            if re.search(raw, content, re.I):
                raw = None
            result.append(blank(ln))
            paragraph = False
        elif re.match(r'^ {0,3}(?:<!--|<\?|<![A-Z]|<!\[CDATA\[)', content):
            raw = (r'-->' if content.lstrip().startswith('<!--') else r'\?>' if content.lstrip().startswith('<?')
                   else r'\]\]>' if content.lstrip().startswith('<![CDATA[') else '>')
            owner = (depth, list_indent)
            if re.search(raw, content):
                raw = None
            result.append(blank(ln))
            paragraph = False
        elif (BLOCK_HTML.match(content)
              or (not paragraph and HTML_TAG.fullmatch(content.strip()))):
            raw = ''  # Ordinary HTML blocks end at a blank line.
            owner = (depth, list_indent)
            result.append(blank(ln))
            paragraph = False
        else:
            if not paragraph and content.lstrip().startswith('['):
                definition = definition_candidate(lines, line_index, content, depth, list_indent)
                if definition:
                    label, dest, count = definition
                    definitions.append((label, line_index + 1, dest))
                    consumed = line_index + count
                    result.append(blank(ln))
                    continue
            result.append(' ' * prefix + content)
            boundary = (thematic or BLOCK_HEADING.match(content) or
                        (paragraph and lazy is None and re.fullmatch(r' {0,3}(?:=+|-+)[ \t]*', content)))
            if lazy is not None and paragraph and not boundary:
                lists = lazy
            if content.strip():
                eligible.append((line_index, not paragraph or bool(boundary), bool(boundary)))
            paragraph = bool(content.strip()) and not boundary
    return '\n'.join(result), definitions, block_regions(result, eligible)


def link_destinations(lines, spans=False):
    """Resolve inline syntax once, in source order, inside eligible blocks."""
    text, collected, regions = markdown_text(lines)
    normalize = lambda value: re.sub(r'[ \t\r\n]+', ' ', value.strip(' \t\r\n')).casefold()
    definitions, used = {}, set()
    for label, line, dest in collected:
        definitions.setdefault(normalize(label), (line, dest))
    for begin, end, line in regions:
        # Index exact backtick-run closers without assigning token ownership yet.
        closers, latest = {}, {}
        runs = list(BACKTICKS.finditer(text, begin, end))
        for run in reversed(runs):
            size = run.end() - run.start()
            # An escaped first backtick may leave a shorter opening run.
            for width in range(1, size + 1):
                closers[run.end() - width] = latest.get(width)
            latest[size] = run.start()
        stack, generation, pos = [], 0, begin
        while pos < end:
            char, stop = text[pos], pos + 1
            if char == '\\' and pos + 1 < end and text[pos + 1] in PUNCTUATION:
                stop = pos + 2
            elif char == '`':
                run = BACKTICKS.match(text, pos, end)
                close = closers.get(pos)
                stop = close + run.end() - pos if close is not None else run.end()
            elif char == '<':
                token = AUTOLINK.match(text, pos, end) or INLINE_HTML.match(text, pos, end)
                if token:
                    stop = token.end()
            elif char == '[' or (char == '!' and text[pos + 1:pos + 2] == '['):
                image = char == '!'
                opening = pos + image
                stack.append((opening, line, image, generation))
                stop = opening + 1
            elif char == ']' and stack:
                opening, source_line, image, opened_generation = stack.pop()
                if image or opened_generation == generation:
                    target, reference = None, None
                    if stop < end and text[stop] == '(':
                        found = destination(text, stop + 1, end)
                        tail = INLINE_END.match(text, found[1], end) if found else None
                        if tail:
                            target, stop = found[0], tail.end()
                    if target is None:
                        label = reference_label(text, stop, end) if text[stop:stop + 1] == '[' else None
                        own = text[opening + 1:pos] if pos - opening <= 1000 else ''
                        value = (label[0] or own) if label else own
                        if valid_label(value):
                            key = normalize(value)
                            if key in definitions:
                                reference = key
                                if label:
                                    stop = label[1]
                    if target is not None or reference is not None:
                        if not image:
                            generation += 1  # Earlier link openers become inactive; images remain active.
                        if reference is not None:
                            used.add(reference)
                        else:
                            if spans:
                                if not image and not any(item[2] for item in stack):
                                    yield source_line, target, opening, stop
                            else:
                                yield source_line, target
            line += text.count('\n', pos, stop)
            pos = stop
    for name, value in definitions.items():
        if not spans and name in used:
            yield value


def valid_label(value):
    if not value.strip(' \t\r\n') or len(value) > 999 or BLANK_LINE.search(value):
        return False
    pos = 0
    while pos < len(value):
        if value[pos] == '\\' and pos + 1 < len(value) and value[pos + 1] in PUNCTUATION:
            pos += 2
            continue
        if value[pos] in '[]':
            return False
        pos += 1
    return True


def reference_label(text, start, end):
    pos = start + 1
    while pos < end and pos - start <= 1000:
        if text[pos] == '\\' and pos + 1 < end and text[pos + 1] in PUNCTUATION:
            pos += 2
            continue
        if text[pos] == ']':
            value = text[start + 1:pos]
            return (value, pos + 1) if not value or valid_label(value) else None
        if text[pos] == '[':
            break
        pos += 1
    return None


def link_problems(cfg, root=None, excluded_roots=(), scope=None):
    """Check links in routed sources, wiki pages, and indexed pages."""
    owner = ROOT if root is None else root
    scope = scope or PhysicalPath(owner)
    excluded_roots = tuple(path if isinstance(path, PhysicalPath) else PhysicalPath(path)
                           for path in excluded_roots)
    sources = {os.path.abspath(os.path.join(owner, s['path'].replace('\\', '/')))
               for t in cfg['topics'].values() for s in t['sources']}
    wiki = cfg.get('wikiDir', 'wiki')
    router = os.path.abspath(os.path.join(owner, cfg.get('routerFile', f'{wiki}/README.md').replace('\\', '/')))
    paths = sources | {router}
    bad, indexed_paths = [], set()
    indexed = cfg.get('indexed', [])
    if isinstance(indexed, list) and indexed and all(isinstance(pattern, str) for pattern in indexed):
        prefixes, skip_dirs = indexed_prefixes(indexed), skip_patterns(cfg) or []
        def walk_error(error):
            rel = os.path.relpath(error.filename or owner, owner).replace(os.sep, '/')
            bad.append(f'{rel}: cannot scan indexed directory: {error}')
        for directory, dirs, files in os.walk(owner, onerror=walk_error if root is not None else None):
            base = os.path.relpath(directory, owner).replace(os.sep, '/')
            if root is not None:
                for name in dirs:
                    rel = child_dir(base, name)
                    if (name.endswith('.md') and any(fnmatch.fnmatch(rel, pattern) for pattern in indexed)
                            and not excluded_path(os.path.join(directory, name), excluded_roots)
                            and not skipped_dir(rel, skip_dirs, wiki, root=root)):
                        bad.append(f'{rel}: indexed page is not a file inside repo')
            dirs[:] = [name for name in dirs if name != '.git' and
                       not excluded_path(os.path.join(directory, name), excluded_roots) and
                       (root is None or inside_root(os.path.join(directory, name), scope, allow_root=True)) and
                       may_hold_indexed(child_dir(base, name), prefixes) and
                       not skipped_dir(child_dir(base, name), skip_dirs, wiki, traversing=True, root=root)]
            if base != '.' and skipped_dir(base, skip_dirs, wiki, root=root):
                continue
            for name in files:
                if not name.endswith('.md'):
                    continue
                path = os.path.join(directory, name)
                if excluded_path(path, excluded_roots):
                    continue
                rel = os.path.relpath(path, owner).replace(os.sep, '/')
                if any(fnmatch.fnmatch(rel, pattern) for pattern in indexed):
                    paths.add(rel)
                    indexed_paths.add(os.path.abspath(path))
    paths = {os.path.abspath(os.path.join(owner, p)) for p in paths}
    wiki_paths = set()
    pending = [(os.path.join(owner, wiki.replace('\\', '/')), frozenset())]
    while pending:
        directory, ancestors = pending.pop()
        if excluded_path(directory, excluded_roots):
            continue
        canonical = os.path.realpath(directory)
        if not inside_root(directory, scope, allow_root=True):
            bad.append(f'{os.path.relpath(directory, owner).replace(os.sep, "/")}: wiki directory is outside repo')
            continue
        if canonical in ancestors:
            continue
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if excluded_path(entry.path, excluded_roots):
                        continue
                    if entry.is_dir():
                        pending.append((entry.path, ancestors | {canonical}))
                    elif entry.name.endswith('.md'):
                        wiki_paths.add(os.path.abspath(entry.path))
        except OSError as error:
            bad.append(f'{os.path.relpath(directory, owner).replace(os.sep, "/")}: cannot scan wiki directory: {error}')
    for path in sorted(paths | wiki_paths):
        rel = os.path.relpath(path, owner).replace(os.sep, '/')
        if not inside_root(path, scope) or not os.path.isfile(path):
            if path == router:
                bad.append(f'{rel}: router is not a file inside repo')
            elif path in wiki_paths and path not in sources:
                bad.append(f'{rel}: wiki page is not a file inside repo')
            elif root is not None and path in indexed_paths:
                bad.append(f'{rel}: indexed page is not a file inside repo')
            continue  # Rendering retains ownership of invalid configured sources.
        try:
            lines = read_text(path, owner, scope=scope).split('\n')
        except (ValueError, OSError) as error:
            bad.append(f'{rel}: {error}')
            continue
        for line, raw in link_destinations(lines):
            dest = markdown_unescape(raw)
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', dest) or dest.startswith(('/', '\\', '#', '?')):
                continue
            dest = unquote(re.split(r'[?#]', dest, maxsplit=1)[0])
            if not dest:
                continue
            try:
                target = os.path.realpath(os.path.normpath(os.path.join(os.path.dirname(path), dest)))
            except (OSError, ValueError):
                target = ''
            if not inside_root(target, scope) or not os.path.isfile(target):
                bad.append(f'{rel}:{line}: relative link {raw!r} is not a file inside repo')
    return bad


def check(cfg, root=None, excluded_roots=(), namespace='', summary=True):
    owner = ROOT if root is None else root
    scope = PhysicalPath(owner)
    excluded_roots = tuple(path if isinstance(path, PhysicalPath) else PhysicalPath(path)
                           for path in excluded_roots)
    bad = link_problems(cfg, root=root, excluded_roots=excluded_roots, scope=scope)
    budgets = cfg.get('budgets', {})
    root_file = cfg.get('rootInstructions', 'AGENTS.md')
    root_text = ''
    try:
        path = (os.path.join(owner, root_file) if root is None else
                configured_path(root_file, owner, 'rootInstructions'))
        if root is not None and not stat.S_ISREG(os.stat(path).st_mode):
            raise ValueError('expected a regular file')
        # Read the kernel without section stripping; its own whitespace and
        # UTF-8 bytes belong to its budget, not the caller's displayed markers.
        root_text = read_text(path, root, f'rootInstructions {path}: outside root {owner}', scope=scope)
        root_size = len(root_text.encode('utf-8'))
        root_cap = budgets.get('rootInstructionsMaxBytes', 8192)
        print(f'{namespace + root_file:18} {root_size:6} B  (cap {root_cap})')
        if root_size > root_cap:
            bad.append(f'{root_file} {root_size} B > {root_cap}')
    except (ValueError, OSError) as error:
        bad.append(f'{root_file}: {error}')
    reference_text = [root_text]
    for name, t in cfg['topics'].items():
        if f'`{name}`' not in root_text:
            bad.append(f'{name}: not listed in {root_file} (agents will not know it exists)')
        try:
            rendered = render(cfg, name, root=root, scope=scope)
            size = len(rendered.encode())
        except (ValueError, OSError) as e:
            bad.append(f'{name}: {e}')
            continue
        reference_text.append(rendered)
        cap = t.get('maxBytes', budgets.get('defaultTopicMaxBytes', 16384))
        print(f'{namespace + name:18} {size:6} B  (cap {cap})')
        if size > cap:
            bad.append(f'{name}: {size} B > {cap} (split the topic; do not raise the cap)')
    bad = orphans(cfg, '\n'.join(reference_text), root=root, excluded_roots=excluded_roots,
                  scope=scope) + bad
    for b in bad:
        print(f'FAIL mount {diagnostic(namespace[:-1])}: {diagnostic(b)}' if namespace else f'FAIL {b}')
    if summary:
        print('ok' if not bad else f'{len(bad)} problem(s)')
    return 1 if bad else 0


def main(argv):
    sys.stdout.reconfigure(encoding='utf-8')  # section markers and CJK pages break cp1252/cp950 consoles on Windows
    sys.stderr.reconfigure(encoding='utf-8')  # error messages can carry non-ASCII paths
    args = argv[1:] or ['list']
    if args == ['--version']:
        print(f'agents-context-router {VERSION}')
        return 0
    cfg = load_cfg()
    try:
        # Validate the config-wide default up front, as mounted configs are, so a bad
        # value fails even when every source sets its own.
        validate_defaults(cfg)
        entries = mount_entries(cfg)
    except ValueError as error:
        print(f'FAIL {diagnostic(error)}', file=sys.stdout if args == ['check'] else sys.stderr)
        return 1
    namespaces = {entry.name: entry for entry in entries if valid_mount_name(entry.name)}
    if args == ['list']:
        for n, t in cfg['topics'].items():
            if n.split('/', 1)[0] not in namespaces or '/' not in n:
                print(f'{n:18} {t["description"]}')
        failed = False
        for entry in entries:
            try:
                mounted = load_mount(entry)
            except MissingMount as error:
                print(f'NOTICE mount {diagnostic(entry.name)}: {diagnostic(error)}')
                continue
            except (OSError, ValueError) as error:
                print(f'FAIL mount {diagnostic(entry.name)}: {diagnostic(error)}', file=sys.stderr)
                failed = True
                continue
            origin = os.path.relpath(entry.root, ROOT).replace(os.sep, '/')
            for name, topic in mounted['topics'].items():
                print(f'{entry.name + "/" + name:18} {topic["description"]} [{origin}]')
        return int(failed)
    if args == ['check']:
        if not entries:
            return check(cfg)
        excluded = [entry.root for entry in entries if entry.root is not None]
        failed = check(cfg, excluded_roots=excluded, summary=False)
        for entry in entries:
            try:
                mounted = load_mount(entry)
            except (OSError, ValueError) as error:
                print(f'FAIL mount {diagnostic(entry.name)}: {diagnostic(error)}')
                failed += 1
                continue
            failed += check(mounted, root=entry.root, namespace=entry.name + '/', summary=False)
        print(f'{failed} root(s) failed' if failed else 'ok')
        return int(bool(failed))
    # A local topic literally named --dedupe keeps priority over the option.
    dedupe = args[0] == '--dedupe' and '--dedupe' not in cfg['topics']
    if dedupe:
        args = args[1:]
        if not args:
            print('--dedupe requires at least one topic', file=sys.stderr)
            return 1
    loaded, selected = {}, []
    for requested in args:
        prefix, separator, topic = requested.partition('/')
        entry = namespaces.get(prefix) if separator else None
        try:
            if entry is not None:
                if prefix not in loaded:
                    loaded[prefix] = load_mount(entry)
                owner_cfg, owner_root = loaded[prefix], entry.root
            else:
                owner_cfg, owner_root, topic = cfg, None, requested
            if topic not in owner_cfg['topics']:
                print(f'unknown topic {requested!r}; rerun this script with list', file=sys.stderr)
                return 1
            selected.append((requested, owner_cfg, topic, owner_root))
        except (OSError, ValueError) as error:
            print(f'{diagnostic(requested)}: {diagnostic(error)}', file=sys.stderr)
            return 1
    bodies, seen = [], set() if dedupe else None
    for requested, owner_cfg, topic, owner_root in selected:
        try:
            body = render(owner_cfg, topic, root=owner_root,
                          display_root=ROOT if owner_root is not None else None, seen=seen)
            if body or not dedupe:
                bodies.append(body)
        except (OSError, ValueError) as error:
            print(f'{diagnostic(requested)}: {diagnostic(error)}', file=sys.stderr)
            return 1
    print('\n\n'.join(bodies))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
