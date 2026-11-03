"""
europe_evidence.py -- v1.1.0 -- November 3, 2026   (v1.1.0: reads the trackers' 'body' field)
Asifah Analytics -- Europe backend (shared helper, no Flask, no network)

WHY THIS EXISTS
  The Ukraine and Moldova interpreters scored red lines by pooling every headline
  into ONE string and counting how many trigger phrases appeared anywhere in it.
  Two phrases from one blog post = BREACHED. Nothing recorded which story did it.

  This module scores a red line PER ARTICLE and counts PUBLISHERS:
    BREACHED     a breach phrase carried by 2+ different outlets
    APPROACHING  a breach phrase from 1 outlet, or approach phrases from 2+ outlets
    WATCHING     an approach phrase from 1 outlet, or social chatter only
    INACTIVE     nothing
  ...and keeps the evidence (title, outlet, phrase) so the page can show its work.

  Matching stays SUBSTRING-based on lower-cased, accent-stripped text, so every
  existing trigger list keeps the meaning it had. What changes is the counting.

  corpus_health() is the thin-read test: a scan with too few articles or outlets
  is UNDER-READ, and the interpreter must say so in its headline -- not print a
  calm baseline.
"""

import unicodedata
from urllib.parse import urlparse

EVIDENCE_VERSION = '1.1.0'

# Telegram tiers that may count as an outlet. 'unverified' never corroborates.
_COUNTED_TIERS = {'official', 'wire', 'mainstream', 'aggregator', 'aligned', 'state', None, ''}
_SOCIAL_TYPES = {'reddit', 'bluesky'}


def norm(text):
    t = str(text or '').replace('’', "'").replace('‘', "'")
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def outlet_of(a):
    """The PUBLISHER, never the feed. A Google News title ends ' - Outlet'."""
    src = a.get('source')
    if isinstance(src, dict):
        src = src.get('name') or src.get('title')
    src = str(src or '').strip()
    feed = str(a.get('feed') or '').lower()
    if feed == 'gnews' or src.lower().startswith(('gnews', 'google news')):
        title = str(a.get('title') or '')
        if ' - ' in title:
            tail = title.rsplit(' - ', 1)[1].strip()
            if 0 < len(tail) <= 60:
                return tail.lower()
    if src and not src.lower().startswith(('gdelt', 'http')):
        return src.lower()
    host = urlparse(str(a.get('url') or a.get('link') or '')).netloc.lower().replace('www.', '')
    return host or 'unknown'


def _item_text(a):
    parts = [a.get(k) or '' for k in ('title', 'description', 'summary', 'content', 'text', 'body')]
    url = str(a.get('url') or a.get('link') or '')
    if url and not url.startswith('https://t.me'):
        parts.append(url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    return norm(' '.join(str(p) for p in parts))


def build_corpus(scan_data, article_keys=('articles_en', 'articles_uk', 'articles_ru', 'articles_ro', 'articles_pl'),
                 telegram_key='telegram_messages', social_keys=('reddit_signals', 'bluesky_signals')):
    """-> list of {text, title, url, outlet, kind}. kind: news | telegram | social.
    De-duplicates by normalised title so one wire story syndicated twice under the
    same headline is one item (it still counts each distinct publisher once)."""
    out, seen = [], set()

    def add(a, kind):
        title = str(a.get('title') or a.get('text') or '')[:300]
        outlet = outlet_of(a) if kind != 'telegram' else str(a.get('source') or 'telegram').lower()
        key = (norm(title)[:160], outlet)
        if not title.strip() or key in seen:
            return
        seen.add(key)
        out.append({'text': _item_text(a), 'title': title, 'url': a.get('url') or a.get('link') or '',
                    'outlet': outlet, 'kind': kind,
                    'tier': a.get('source_tier') if kind == 'telegram' else None})

    for k in article_keys:
        for a in scan_data.get(k) or []:
            if isinstance(a, dict):
                add(a, 'social' if a.get('source_type') in _SOCIAL_TYPES else 'news')
    for a in scan_data.get(telegram_key) or []:
        if isinstance(a, dict):
            add(a, 'telegram')
    for k in social_keys:
        for a in scan_data.get(k) or []:
            if isinstance(a, dict):
                add(a, 'social')
    return out


def _counts(item):
    return item['kind'] in ('news',) or (item['kind'] == 'telegram' and item.get('tier') in _COUNTED_TIERS)


def find(corpus, terms, max_evidence=4):
    """Items carrying any of `terms`. -> {outlets:set, phrases:set, social:int, evidence:[...]}"""
    terms = [norm(t) for t in (terms or []) if t]
    res = {'outlets': set(), 'phrases': set(), 'social': 0, 'evidence': []}
    if not terms:
        return res
    for it in corpus:
        hit = next((t for t in terms if t in it['text']), None)
        if not hit:
            continue
        res['phrases'].update(t for t in terms if t in it['text'])
        if _counts(it):
            if it['outlet'] not in res['outlets'] and len(res['evidence']) < max_evidence:
                res['evidence'].append({'title': it['title'][:180], 'outlet': it['outlet'],
                                        'url': it['url'], 'phrase': hit})
            res['outlets'].add(it['outlet'])
        else:
            res['social'] += 1
    return res


def score_line(corpus, breach_terms, approach_terms):
    """The corroboration ladder for one red line (see module docstring)."""
    b = find(corpus, breach_terms)
    a = find(corpus, approach_terms)
    nb, na = len(b['outlets']), len(a['outlets'])
    if nb >= 2:
        status = 'BREACHED'
    elif nb == 1 or na >= 2:
        status = 'APPROACHING'
    elif na == 1 or b['social'] or a['social']:
        status = 'WATCHING'
    else:
        status = 'INACTIVE'
    ev = (b['evidence'] + [e for e in a['evidence'] if e['outlet'] not in b['outlets']])[:4]
    return {'status': status,
            'breached_hits': len(b['phrases']), 'approaching_hits': len(a['phrases']),
            'breach_outlets': nb, 'approach_outlets': na, 'evidence': ev}


def score_green(corpus, active_terms, signaled_terms):
    """Green lines: de-escalation never inflates a risk read, so ONE outlet may
    activate it -- but the outlet is still recorded."""
    act = find(corpus, active_terms)
    sig = find(corpus, signaled_terms)
    if act['outlets']:
        status = 'ACTIVE'
    elif sig['outlets'] or act['social'] or sig['social']:
        status = 'SIGNALED'
    else:
        status = 'DORMANT'
    return {'status': status, 'active_hits': len(act['phrases']), 'signaled_hits': len(sig['phrases']),
            'active_outlets': len(act['outlets']), 'signaled_outlets': len(sig['outlets']),
            'evidence': (act['evidence'] + sig['evidence'])[:3]}


def outlet_level(n_outlets, cap=3):
    """Breadth -> 0..cap. 1 outlet = 1, 2 = 2, 3+ = 3. Breadth, never volume."""
    return min(cap, n_outlets)


def phrase_count(corpus, terms):
    """Distinct phrases present anywhere (the old diplomatic-track arithmetic)."""
    return len(find(corpus, terms)['phrases'])


def corpus_health(scan_data, corpus, min_articles, min_outlets=4):
    """Is this scan an under-read? -> {thin, articles, outlets, reason}."""
    news = [c for c in corpus if c['kind'] in ('news', 'telegram')]
    outlets = {c['outlet'] for c in news}
    sensing = scan_data.get('sensing') or {}
    any_sensed = sensing.get('any_sensed', True) if isinstance(sensing, dict) else True
    reasons = []
    if not any_sensed:
        reasons.append('no source family answered')
    if len(news) < min_articles:
        reasons.append(f'{len(news)} articles (thin below {min_articles})')
    if len(outlets) < min_outlets:
        reasons.append(f'{len(outlets)} outlets (thin below {min_outlets})')
    gd = sensing.get('gdelt') if isinstance(sensing, dict) else None
    partial = bool(isinstance(gd, dict) and gd.get('attempted') and not gd.get('sensed'))
    return {'thin': bool(reasons), 'articles': len(news), 'outlets': len(outlets),
            'reason': '; '.join(reasons), 'partial_sources': partial}


STATUS_LEVEL = {'INACTIVE': 0, 'WATCHING': 2, 'APPROACHING': 3, 'BREACHED': 4}
