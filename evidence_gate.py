"""
evidence_gate.py -- Asifah Analytics -- SHARED MODULE (WHA backend)
v1.0.1 -- Nov 4 2026 (pm): outlet_of treats 'news.google.com' (any name containing
          'google') as the aggregator, not the outlet. v1.0.0 Nov 4 2026.

One set of evidence rules for every rhetoric tracker, so "a keyword is not a
war" is enforced the same way everywhere instead of re-typed per tracker.
First extracted from the Venezuela v1.1.0 evidence layer; Peru 1.1.0 and
Cuba 1.4.0 are the first consumers.

PLATFORM RULINGS THIS ENCODES
  * A keyword is not a war. A high-impact phrase in ONE headline is a claim.
  * L3+ needs 2+ distinct OUTLETS (not 2 articles from one wire).
  * Hedged wording ("could", "warns", "rumours") is a possibility, not an event.
  * Rumour is in scope, but in its own labelled lane until corroborated.
  * Stale evidence is dropped: an old story recirculating is not news.

PUBLIC API
  is_hedged(text)                       -> bool
  outlet_of(article)                    -> str  (lower-case outlet name)
  parse_date(value)                     -> datetime | None
  drop_stale(articles, max_age_days)    -> (fresh, dropped_count)
  grade(outlets, social_outlets)        -> 'corroborated'|'single_source'|'rumint'|'none'
  TripwireLedger                        -> collects hits per tripwire, grades them
  ladder_detect(articles, ladder, ...)  -> (level, signals)   per-rung corroboration

Deliberately dependency-free (stdlib only) so it can be deployed byte-identical
to any backend.
"""

import re
from datetime import datetime, timezone

__version__ = '1.0.1'

MAX_ARTICLE_AGE_DAYS = 10
CORROBORATION = 2
SOCIAL_FEED_TYPES = ('reddit', 'bluesky', 'telegram', 'social')

_HEDGE_RX = re.compile(
    r"\b(could|may|might|would|warns?|warning of|fears?|feared|risk of|"
    r"threat(?:ens)? to|possible|possibly|potential|rumou?rs?|rumou?red|"
    r"reportedly considering|weighs|mulls|if\b|unconfirmed|alleged plan|"
    r"podr[íi]a|podr[íi]an|posible|posiblemente|advierte|advierten|teme|temen|"
    r"rumores?|presunto plan|no confirmad[oa]|eventual|amenaza con|amenazan con)\b",
    re.IGNORECASE)
# "May" the month is not a hedge.
_MONTH_MAY_RX = re.compile(
    r"\b(?:in|of|since|by|until|early|late|mid-?|next|last|this|on)\s+May\b|\bMay\s+\d",
    re.IGNORECASE)


def is_hedged(text):
    return bool(_HEDGE_RX.search(_MONTH_MAY_RX.sub(' ', text or '')))


def _text(article):
    return ' '.join(str(article.get(k) or '') for k in ('title', 'description', 'snippet'))


def outlet_of(article):
    """The real outlet behind an item.

    Google News RSS names itself as the source; the true outlet is in the
    item's <source> tag ('outlet' if the fetcher captured it) or the
    ' - Outlet' title suffix. Without this, one Google feed counts as one
    outlet no matter how many papers it carries.
    """
    o = str(article.get('outlet') or '').strip()
    if o:
        return o.lower()
    src = article.get('source')
    name = src.get('name') if isinstance(src, dict) else src
    name = str(name or '').strip()
    title = str(article.get('title') or '')
    # Aggregator labels name the PIPE, not the paper: "NewsAPI (Reuters)" ->
    # reuters; "GDELT (eng)" / "Brave" -> the article's own domain.
    m = re.match(r'(?i)newsapi\s*\((.+)\)$', name)
    if m:
        return m.group(1).strip().lower()
    if re.match(r'(?i)^(gdelt|brave|newsapi|rss)\b', name):
        name = ''
    if not name or 'google' in name.lower():
        m = re.search(r'\s[-–—]\s([^-–—]{2,40})$', title)
        if m:
            return m.group(1).strip().lower()
    if not name:
        url = str(article.get('url') or article.get('link') or '')
        m = re.match(r'https?://(?:www\.)?([^/]+)', url)
        if m:
            return m.group(1).lower()
    return (name or 'unknown').lower()


_DATE_FORMATS = ('%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
                 '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S.%fZ',
                 '%Y-%m-%d %H:%M:%S', '%Y%m%dT%H%M%SZ', '%Y%m%d%H%M%S', '%Y-%m-%d')


def parse_date(value):
    """Read a date in any format the feeds use. None when unreadable --
    never 'now', because the stale filter must not mistake unknown for fresh."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    try:
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def article_date(article):
    for k in ('publishedAt', 'published', 'pubDate', 'date', 'seendate', 'published_at'):
        d = parse_date(article.get(k))
        if d:
            return d
    return None


def drop_stale(articles, max_age_days=MAX_ARTICLE_AGE_DAYS):
    """Remove items whose readable date is older than the window.
    Undated items are kept (we only remove what we can prove is old)."""
    now = datetime.now(timezone.utc)
    fresh, dropped = [], 0
    for a in articles or []:
        d = article_date(a)
        if d is not None and (now - d).total_seconds() > max_age_days * 86400:
            dropped += 1
            continue
        fresh.append(a)
    return fresh, dropped


def grade(outlets, social_outlets=()):
    """Who reported it -> how much it counts."""
    outlets = set(outlets or ())
    if len(outlets) >= CORROBORATION:
        return 'corroborated'
    if outlets:
        return 'single_source'
    if social_outlets:
        return 'rumint'
    return 'none'


GRADE_TEXT = {
    'corroborated':  'confirmed by 2+ separate outlets',
    'single_source': 'reported by one outlet, not yet corroborated',
    'rumint':        'rumour or hedged wording only',
    'none':          'not reported',
}


class TripwireLedger:
    """Collect tripwire hits across a scan, then grade each one.

        led = TripwireLedger()
        led.add('state_of_emergency', article)      # per matching article
        led.result('state_of_emergency')            # -> {'grade', 'outlets', ...}

    Hedged or social items go to the rumour lane automatically.
    """

    def __init__(self):
        self._hits = {}

    def add(self, tw_id, article, text=None):
        rec = self._hits.setdefault(tw_id, {'outlets': set(), 'rumint': set(), 'items': []})
        t = text if text is not None else _text(article)
        o = outlet_of(article)
        if is_hedged(t) or str(article.get('feed_type') or '').lower() in SOCIAL_FEED_TYPES:
            rec['rumint'].add(o)
        else:
            rec['outlets'].add(o)
        if len(rec['items']) < 4:
            rec['items'].append({'title': str(article.get('title') or '')[:160], 'outlet': o,
                                 'url': article.get('url') or article.get('link') or ''})

    def ids(self):
        return list(self._hits.keys())

    def result(self, tw_id):
        rec = self._hits.get(tw_id)
        if not rec:
            return {'grade': 'none', 'outlets': [], 'rumint_outlets': [], 'items': []}
        g = grade(rec['outlets'], rec['rumint'])
        return {'grade': g, 'grade_text': GRADE_TEXT[g],
                'outlets': sorted(rec['outlets'])[:8],
                'rumint_outlets': sorted(rec['rumint'])[:8],
                'items': rec['items']}


def ladder_detect(articles, ladder, max_signals=10, text_fn=None):
    """Read a 1-5 phrase ladder with per-rung corroboration.

    * hedged text counts only toward L1-L2
    * a rung at L3+ needs CORROBORATION distinct outlets
    * a rung at L3+ with one outlet reads as L2 and is flagged 'uncorroborated'
    Returns (level, signals).
    """
    text_fn = text_fn or (lambda a: _text(a).lower())
    firm, soft, first = {}, {}, {}
    for lvl in sorted(ladder.keys(), reverse=True):
        for phrase in ladder[lvl]:
            ph = phrase.lower()
            for art in articles or []:
                t = text_fn(art)
                if ph not in t:
                    continue
                o = outlet_of(art)
                hedged = is_hedged(t)
                (soft if hedged else firm).setdefault(lvl, set()).add(o)
                first.setdefault((lvl, o), {
                    'article': str(art.get('title') or '')[:160], 'level': lvl,
                    'phrase': phrase, 'outlet': o, 'hedged': hedged,
                    'url': art.get('url') or art.get('link') or '',
                    'published': art.get('publishedAt') or art.get('published') or ''})
    level = 0
    for lvl in sorted(ladder.keys(), reverse=True):
        n = len(firm.get(lvl, ()))
        if lvl >= 3 and n >= CORROBORATION:
            level = lvl
            break
        if lvl >= 3 and n == 1:
            level = max(level, 2)
        elif lvl <= 2 and (n or soft.get(lvl)):
            level = max(level, lvl)
    if level == 0 and any(l >= 3 for l in soft):
        level = 1
    sigs = []
    for (lvl, o), s in first.items():
        n = len(firm.get(lvl, ()))
        s['evidence'] = ('hedged' if s['hedged'] else
                         ('corroborated' if n >= CORROBORATION else 'uncorroborated') if lvl >= 3
                         else 'reported')
        sigs.append(s)
    sigs.sort(key=lambda x: (-x['level'], x['evidence'] != 'corroborated'))
    return level, sigs[:max_signals]
