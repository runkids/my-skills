#!/usr/bin/env python3
"""Print only the doc sections a task needs.

usage: ai-context.py list | <topic> [<topic>...] | check | --version

Topics live in wiki/ai-context.json. A source is a whole file or one exact
heading (the section runs to the next heading of the same or higher level).
check also fails on orphans, so docs cannot silently drift out of the router:
wiki pages no topic loads, history files missing from the router index, and
nested AGENTS.md files no topic loads, opted-in indexed pages no instructions name, and relative Markdown links are checked.
List bulky trees that hold no instructions under "skipDirs" (exact paths or
case-sensitive fnmatch globs) to keep check from walking them; the wiki is always walked.
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
import fnmatch, json, os, re, sys
from urllib.parse import unquote
from html import unescape
from html.entities import html5

VERSION = '0.2.1'  # x-release-please-version


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


def load_cfg():
    if not os.path.exists(CFG_PATH):
        sys.exit(f'missing {CFG_PATH}; copy this script to <repo>/scripts/ and create wiki/ai-context.json, or set AI_CONTEXT_ROOT and AI_CONTEXT_CONFIG for a shared installation')
    with open(CFG_PATH, encoding='utf-8') as f:
        return json.load(f)


def headings(lines):
    """Yield (index, level, text), skipping headings inside fenced code (e.g. shell comments)."""
    fence = None
    for i, ln in enumerate(lines):
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


def section(src):
    path = os.path.realpath(os.path.join(ROOT, src['path'].replace('\\', '/')))
    if not path.startswith(os.path.join(ROOT, '')):
        raise ValueError(f'{src["path"]}: outside repo')
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    if 'heading' not in src:
        return '\n'.join(lines).strip()
    hs = list(headings(lines))
    hits = [(i, lv) for i, lv, t in hs if t == src['heading']]
    if len(hits) != 1:  # fail closed: a renamed or duplicated heading must not load the wrong text
        raise ValueError(f'{src["path"]}: heading {src["heading"]!r} found {len(hits)}x')
    start, level = hits[0]
    end = next((i for i, lv, _ in hs if i > start and lv <= level), len(lines))
    return '\n'.join(lines[start:end]).strip()


def render(cfg, name):
    out = []
    for s in cfg['topics'][name]['sources']:
        where = s['path'] + (f' § {s["heading"]}' if 'heading' in s else '')
        out.append(f'<!-- {where} -->\n{section(s)}')
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


def skipped_dir(rel, patterns, wiki, traversing=False):
    """Whether a directory is skipped; traversal may retain the path to the wiki."""
    if (rel == wiki or rel.startswith(wiki + '/')
            or (traversing and wiki.startswith(rel + '/'))):
        return False
    parts = rel.split('/')
    return any(path == p or fnmatch.fnmatchcase(path, p)
               for path in ('/'.join(parts[:i]) for i in range(1, len(parts) + 1)) for p in patterns)


def child_dir(base, name):
    """The repo-relative path of directory name under walk directory base."""
    return name if base == '.' else f'{base}/{name}'


def orphans(cfg, reference_text=''):
    """Docs that exist on disk but that no agent can reach through the router."""
    indexed = cfg.get('indexed', [])
    if not isinstance(indexed, list) or any(not isinstance(p, str) for p in indexed):
        return ['indexed: expected a list of strings']
    skip_dirs = skip_patterns(cfg)
    if skip_dirs is None:
        return ['skipDirs: expected a list of strings']
    wiki = cfg.get('wikiDir', 'wiki')
    history = cfg.get('historyDir', f'{wiki}/history')
    router = cfg.get('routerFile', f'{wiki}/README.md')
    root_file = cfg.get('rootInstructions', 'AGENTS.md')
    routed = {s['path'].replace('\\', '/') for t in cfg['topics'].values() for s in t['sources']}
    allowed = {p.replace('\\', '/'): reason for p, reason in cfg.get('unrouted', {}).items()}
    try:
        router_text = section({'path': router})
    except (ValueError, OSError):
        router_text = ''  # link_problems reports the invalid or unreadable router.
    reference_text += '\n' + router_text
    bad = []
    skip = {'.git', 'node_modules', 'dist', 'build', 'vendor', '.venv', 'target'}
    prefixes = indexed_prefixes(indexed)
    for d, dirs, files in os.walk(ROOT):
        base = os.path.relpath(d, ROOT).replace(os.sep, '/')
        dirs[:] = [x for x in dirs if x != '.git' and
                   ((x not in skip and not x.startswith('.')) or
                    may_hold_indexed(child_dir(base, x), prefixes)) and
                   not skipped_dir(child_dir(base, x), skip_dirs, wiki, traversing=True)]
        if base != '.' and skipped_dir(base, skip_dirs, wiki):
            continue
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')
            if not f.endswith('.md'):
                continue
            reasons = [reason for pattern, reason in allowed.items()
                       if rel == pattern or fnmatch.fnmatchcase(rel, pattern)]
            if (any(fnmatch.fnmatch(rel, pattern) for pattern in indexed)
                    and rel not in routed and rel not in reference_text
                    and not any(isinstance(reason, str) and reason.strip() for reason in reasons)):
                bad.append(f'{rel}: indexed page not named (name it in a topic page, route it, or list it under "unrouted" with a reason)')
            if (reasons or any(x in skip or x.startswith('.') for x in rel.split('/')[:-1])):
                continue
            if rel.startswith(history + '/'):
                if os.path.relpath(rel, wiki).replace(os.sep, '/') not in router_text and rel not in router_text:
                    bad.append(f'{rel}: history file not indexed in {router}')
            elif rel.startswith(wiki + '/'):
                if rel != router and rel not in routed:
                    bad.append(f'{rel}: wiki page no topic loads (map it, or list it under "unrouted" with a reason)')
            elif f == 'AGENTS.md' and rel != root_file and rel not in routed:
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


def link_destinations(lines):
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
                            yield source_line, target
            line += text.count('\n', pos, stop)
            pos = stop
    for name, value in definitions.items():
        if name in used:
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


def link_problems(cfg):
    """Check links in routed sources, wiki pages, and indexed pages."""
    paths = {s['path'].replace('\\', '/') for t in cfg['topics'].values() for s in t['sources']}
    sources = {os.path.abspath(os.path.join(ROOT, p)) for p in paths}
    wiki = cfg.get('wikiDir', 'wiki')
    router = os.path.abspath(os.path.join(ROOT, cfg.get('routerFile', f'{wiki}/README.md')))
    paths.add(router)
    indexed = cfg.get('indexed', [])
    if isinstance(indexed, list) and indexed and all(isinstance(pattern, str) for pattern in indexed):
        prefixes, skip_dirs = indexed_prefixes(indexed), skip_patterns(cfg) or []
        for directory, dirs, files in os.walk(ROOT):
            base = os.path.relpath(directory, ROOT).replace(os.sep, '/')
            dirs[:] = [name for name in dirs if name != '.git' and
                       may_hold_indexed(child_dir(base, name), prefixes) and
                       not skipped_dir(child_dir(base, name), skip_dirs, wiki, traversing=True)]
            if base != '.' and skipped_dir(base, skip_dirs, wiki):
                continue
            for name in files:
                if not name.endswith('.md'):
                    continue
                rel = os.path.relpath(os.path.join(directory, name), ROOT).replace(os.sep, '/')
                if any(fnmatch.fnmatch(rel, pattern) for pattern in indexed):
                    paths.add(rel)
    paths = {os.path.abspath(os.path.join(ROOT, p)) for p in paths}
    wiki_paths, bad = set(), []
    pending = [(os.path.join(ROOT, wiki), frozenset())]
    while pending:
        directory, ancestors = pending.pop()
        canonical = os.path.realpath(directory)
        if not (canonical == ROOT or canonical.startswith(os.path.join(ROOT, ''))):
            bad.append(f'{os.path.relpath(directory, ROOT).replace(os.sep, "/")}: wiki directory is outside repo')
            continue
        if canonical in ancestors:
            continue
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_dir():
                        pending.append((entry.path, ancestors | {canonical}))
                    elif entry.name.endswith('.md'):
                        wiki_paths.add(os.path.abspath(entry.path))
        except OSError as error:
            bad.append(f'{os.path.relpath(directory, ROOT).replace(os.sep, "/")}: cannot scan wiki directory: {error}')
    for path in sorted(paths | wiki_paths):
        rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
        canonical = os.path.realpath(path)
        if not canonical.startswith(os.path.join(ROOT, '')) or not os.path.isfile(path):
            if path == router:
                bad.append(f'{rel}: router is not a file inside repo')
            elif path in wiki_paths and path not in sources:
                bad.append(f'{rel}: wiki page is not a file inside repo')
            continue  # Rendering retains ownership of invalid configured sources.
        try:
            with open(path, encoding='utf-8') as source:
                lines = source.read().split('\n')
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
            if not target.startswith(os.path.join(ROOT, '')) or not os.path.isfile(target):
                bad.append(f'{rel}:{line}: relative link {raw!r} is not a file inside repo')
    return bad


def check(cfg):
    bad = link_problems(cfg)
    budgets = cfg.get('budgets', {})
    root_file = cfg.get('rootInstructions', 'AGENTS.md')
    root_text = open(os.path.join(ROOT, root_file), encoding='utf-8').read()
    reference_text = [root_text]
    root_size = len(root_text.encode())
    root_cap = budgets.get('rootInstructionsMaxBytes', 8192)
    print(f'{root_file:18} {root_size:6} B  (cap {root_cap})')
    if root_size > root_cap:
        bad.append(f'{root_file} {root_size} B > {root_cap}')
    for name, t in cfg['topics'].items():
        if f'`{name}`' not in root_text:
            bad.append(f'{name}: not listed in {root_file} (agents will not know it exists)')
        try:
            rendered = render(cfg, name)
            size = len(rendered.encode())
        except (ValueError, OSError) as e:
            bad.append(f'{name}: {e}')
            continue
        reference_text.append(rendered)
        cap = t.get('maxBytes', budgets.get('defaultTopicMaxBytes', 16384))
        print(f'{name:18} {size:6} B  (cap {cap})')
        if size > cap:
            bad.append(f'{name}: {size} B > {cap} (split the topic; do not raise the cap)')
    bad = orphans(cfg, '\n'.join(reference_text)) + bad
    for b in bad:
        print('FAIL', b)
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
    if args == ['list']:
        for n, t in cfg['topics'].items():
            print(f'{n:18} {t["description"]}')
        return 0
    if args == ['check']:
        return check(cfg)
    unknown = [a for a in args if a not in cfg['topics']]
    if unknown:
        sys.exit(f'unknown topic {unknown[0]!r}; rerun this script with list')
    print('\n\n'.join(render(cfg, a) for a in args))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
