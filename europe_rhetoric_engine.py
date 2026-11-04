"""
europe_rhetoric_engine.py -- Asifah Analytics -- SHARED MODULE (Europe backend)
v1.0.0-eu -- Nov 4 2026 (night). A port of wha_rhetoric_engine.py v1.0.1, so
the Europe backend gets the same config-driven tracker machinery. Changes from
the WHA original, and nothing else:
  * NewsAPI goes through newsapi_gateway.py (Europe retired NEWSAPI_KEY; the
    gateway owns the daily budget). No gateway -> the lane is skipped.
  * Bluesky comes from bluesky_signals_europe.py.
  * GDELT languages come from the config ('gdelt_langs'); default English only.
  * User-Agent and log tags say Europe.
First consumer: rhetoric_tracker_uk.py. Albania / Belgium / Turkmenistan can
follow as configs.

-- original header --
wha_rhetoric_engine.py -- Asifah Analytics -- SHARED MODULE (WHA backend)
v1.0.1 -- Nov 4 2026 (night)  (v1.0.0 Nov 4 2026 evening)

ONE ENGINE, MANY COUNTRIES
The Chile and Peru trackers are ~1,600 lines each, and ~1,300 of those lines
are the same machinery: fetch, filter, classify, score, grade, write, serve.
Every fix had to be typed twice. This module is that machinery, once. A new
country tracker is now a CONFIG (actors, feeds, red lines, plain-language
meanings, So What rules) plus one register() call.

First consumers: rhetoric_tracker_mexico.py and rhetoric_tracker_argentina.py.
Chile / Peru / Cuba / Venezuela / US keep their own files for now (no reason to
touch working trackers in the same release).

PLATFORM RULINGS THIS ENCODES (via evidence_gate)
  * A keyword is not a war. Volume alone tops out at 'elevated' (L2).
  * L3+ needs 2+ separate OUTLETS reporting the event as fact.
  * One outlet = "approaching" (L2 at most). Hedged / social = rumour lane.
  * Items older than 10 days are dropped.
  * L5 only from kinetic ladders: these trackers cap at L4.
  * Absence-honest: no articles is "unread", never "calm".

OUTPUT CONTRACT (what the page, the WHA BLUF and the GPI read)
  rhetoric:<slug>:latest   full payload (13h TTL)
  rhetoric:<slug>:lastgood same payload (7 days) -- BLUF cold-start fallback
  rhetoric:<slug>:history  canonical snapshots (theatre_level, theatre_score,
                           scanned_at, red_lines_count + vector levels)
  spoke:<hub>:<slug>       for spoke_wheel_reader (30h TTL)
  payload fields: theatre_level (int 0-4), theatre_label, top_signals[]
  (int level + level_name + pressure_type + meaning), top_indicator,
  executive_summary, so_what[], red_lines[] (status BREACHED / APPROACHING /
  RUMOUR / WATCHING), green_lines[], vectors_meta[], actor_order[],
  actor_summaries{}, vector_levels{}, evidence_rules{}.

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

import os
import re
import json
import time
import threading
import unicodedata
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

import requests

__version__ = '1.0.0-eu'   # Nov 4 2026 night: no duplicate So What when an event bullet already covers its vector

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    from evidence_gate import (TripwireLedger, drop_stale, outlet_of, is_hedged,
                               MAX_ARTICLE_AGE_DAYS)
    EVIDENCE_GATE_AVAILABLE = True
except ImportError:                                   # pragma: no cover
    EVIDENCE_GATE_AVAILABLE = False
    MAX_ARTICLE_AGE_DAYS = 10
    def drop_stale(a, max_age_days=10): return list(a), 0
    def outlet_of(a): return str(a.get('source') or 'unknown').lower()
    def is_hedged(t): return False
    class TripwireLedger:
        def __init__(self): self._h = {}
        def add(self, tw, a, text=None): self._h.setdefault(tw, set()).add(outlet_of(a))
        def ids(self): return list(self._h)
        def result(self, tw):
            o = sorted(self._h.get(tw, ()))
            return {'grade': 'corroborated' if len(o) >= 2 else ('single_source' if o else 'none'),
                    'grade_text': '', 'outlets': o, 'rumint_outlets': [], 'items': []}

try:
    from gdelt_gateway import gdelt_fetch as _gw_fetch
    _GDELT_GATEWAY = True
except ImportError:
    _GDELT_GATEWAY = False

try:
    from newsapi_gateway import newsapi_fetch as _napi_fetch
    _NEWSAPI_GATEWAY = True
except ImportError:
    _NEWSAPI_GATEWAY = False

UPSTASH_REDIS_URL = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_REDIS_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN')
NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY')
BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY')

CACHE_TTL_HOURS = 13
LASTGOOD_TTL_HOURS = 24 * 7
SCAN_INTERVAL_HOURS = 12
SPOKE_TTL_HOURS = 30
FORCE_GAP_SECONDS = 15 * 60

LEVEL_NAMES = ['low', 'normal', 'elevated', 'high', 'surge']
LEVEL_INT = {n: i for i, n in enumerate(LEVEL_NAMES)}
ESCALATORY = {'elevated', 'high', 'surge'}
PRIORITY_BY_LEVEL = {0: 2, 1: 4, 2: 7, 3: 10, 4: 12}
WHA_LABEL = {0: 'Monitoring', 1: 'Rhetoric', 2: 'Warning', 3: 'Direct Threat',
             4: 'Imminent Crisis', 5: 'Active Crisis'}
UA = 'Mozilla/5.0 (compatible; AsifahAnalytics-Europe/rhetoric-engine-%s; +https://asifahanalytics.com)' % __version__


# ════════════════════════════════════════════════════════════════════
# TEXT HELPERS
# ════════════════════════════════════════════════════════════════════
def fold(text):
    """Lower-case and strip accents: 'excepción' == 'excepcion'."""
    return ''.join(c for c in unicodedata.normalize('NFKD', text or '')
                   if not unicodedata.combining(c)).lower()


_RX = {}


def has_phrase(text, phrase):
    """Whole-word match on folded text ('kast' never matches 'broadcast')."""
    rx = _RX.get(phrase)
    if rx is None:
        rx = re.compile(r'(?<![a-z0-9])' + re.escape(fold(phrase)) + r'(?![a-z0-9])')
        _RX[phrase] = rx
    return bool(rx.search(text))


def article_text(a):
    """Title + description, folded. The source name is deliberately excluded."""
    return fold(' '.join(str(a.get(k) or '') for k in ('title', 'description', 'snippet')))


def level_max(levels):
    return max(levels, key=lambda lv: LEVEL_INT.get(lv, 0), default='low')


def volume_level(score, baseline):
    ratio = score / max(1, baseline)
    if ratio >= 2.5:
        return 'surge'
    if ratio >= 1.7:
        return 'high'
    if ratio >= 1.1:
        return 'elevated'
    if ratio >= 0.4:
        return 'normal'
    return 'low'


# ════════════════════════════════════════════════════════════════════
# REDIS
# ════════════════════════════════════════════════════════════════════
def redis_get(key):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return None
    try:
        r = requests.get(f'{UPSTASH_REDIS_URL}/get/{key}',
                         headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}, timeout=5)
        raw = r.json().get('result')
        return json.loads(raw) if raw else None
    except Exception:
        return None


def redis_set(key, value, ttl_hours=CACHE_TTL_HOURS):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        r = requests.post(f'{UPSTASH_REDIS_URL}/setex/{key}/{int(ttl_hours * 3600)}',
                          headers={'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'},
                          data=json.dumps(value, default=str), timeout=8)
        return r.status_code == 200
    except Exception:
        return False


def redis_lpush_trim(key, value, max_len=336):
    if not (UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN):
        return False
    try:
        h = {'Authorization': f'Bearer {UPSTASH_REDIS_TOKEN}'}
        r = requests.post(f'{UPSTASH_REDIS_URL}/lpush/{key}', headers=h,
                          data=json.dumps(value, default=str), timeout=8)
        if r.status_code != 200:
            return False
        requests.post(f'{UPSTASH_REDIS_URL}/ltrim/{key}/0/{max_len - 1}', headers=h, timeout=8)
        return True
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════════
# THE TRACKER
# ════════════════════════════════════════════════════════════════════
class CountryRhetoricTracker:
    """A config-driven rhetoric tracker. See rhetoric_tracker_mexico.py for a
    fully commented config."""

    def __init__(self, cfg):
        self.c = cfg
        self.slug = cfg['slug']
        self.name = cfg['name']
        self.version = cfg.get('version', '1.0.0')
        self.tag = '[%s Rhetoric]' % self.name
        self.cache_key = 'rhetoric:%s:latest' % self.slug
        self.lastgood_key = 'rhetoric:%s:lastgood' % self.slug
        self.history_key = 'rhetoric:%s:history' % self.slug
        self.actors = cfg['actors']
        self.vectors = cfg['vectors']
        self._last_forced = [0.0]
        self._lock = threading.Lock()
        self._scan_lock = threading.Lock()

    # ── logging ─────────────────────────────────────────────────────
    def log(self, msg):
        print('%s %s' % (self.tag, msg))

    # ── fetch ───────────────────────────────────────────────────────
    def fetch_rss(self):
        out = []
        if not FEEDPARSER_AVAILABLE:
            return out
        for fid, f in self.c.get('rss_feeds', {}).items():
            try:
                resp = requests.get(f['url'], headers={'User-Agent': UA}, timeout=12)
                parsed = feedparser.parse(resp.content)
                for e in parsed.entries[:f.get('max', 40)]:
                    out.append({'title': (e.get('title') or '')[:300],
                                'description': re.sub(r'<[^>]+>', ' ', e.get('summary') or '')[:500],
                                'url': e.get('link', ''), 'source': f['name'],
                                'language': f.get('language', 'es'),
                                'published': e.get('published') or e.get('updated') or '',
                                'feed_type': 'rss'})
            except Exception as ex:
                self.log('RSS error (%s): %s' % (fid, str(ex)[:100]))
        return out

    def fetch_google(self):
        """Google News search RSS -- free, keyless, multilingual. The <source>
        element names the real outlet, which evidence_gate counts."""
        out = []
        if not FEEDPARSER_AVAILABLE:
            return out
        for q, hl, gl in self.c.get('google_queries', []):
            ceid = '%s:%s' % (gl, hl.split('-')[0] if hl.startswith('en') else hl)
            url = ('https://news.google.com/rss/search?q=%s+when:7d&hl=%s&gl=%s&ceid=%s'
                   % (quote_plus(q), hl, gl, ceid))
            try:
                resp = requests.get(url, headers={'User-Agent': UA}, timeout=12)
                parsed = feedparser.parse(resp.content)
                for e in parsed.entries[:25]:
                    src = (e.get('source') or {}).get('title') if isinstance(e.get('source'), dict) else None
                    title = e.get('title') or ''
                    if not src and ' - ' in title:
                        title, src = title.rsplit(' - ', 1)
                    elif src and title.endswith(' - ' + src):
                        title = title[:-(len(src) + 3)]
                    out.append({'title': title[:300], 'url': e.get('link', ''),
                                'source': src or 'Google News', 'language': hl[:2],
                                'published': e.get('published', ''), 'feed_type': 'google_news'})
            except Exception as ex:
                self.log('Google News error (%s): %s' % (q, str(ex)[:100]))
            time.sleep(0.4)
        return out

    def fetch_gdelt(self, days=7):
        out = []
        for lang, key in (self.c.get('gdelt_langs') or (('eng', 'gdelt_en'),)):
            for q in self.c.get(key, []):
                try:
                    if _GDELT_GATEWAY:
                        raw = _gw_fetch(q, language=lang, timespan='%dd' % days, maxrecords=40,
                                        label='%s/%s' % (self.slug, lang))
                        out.extend({'title': (a.get('title') or '')[:300], 'url': a.get('url', ''),
                                    'source': a.get('source') or 'GDELT', 'language': lang[:2],
                                    'published': a.get('published', ''), 'feed_type': 'gdelt'} for a in raw)
                    else:
                        r = requests.get('https://api.gdeltproject.org/api/v2/doc/doc',
                                         params={'query': q, 'mode': 'ArtList', 'format': 'json',
                                                 'maxrecords': 40, 'timespan': '%dd' % days,
                                                 'sourcelang': lang}, timeout=(5, 15))
                        if r.status_code == 200:
                            out.extend({'title': (a.get('title') or '')[:300], 'url': a.get('url', ''),
                                        'source': a.get('domain', 'GDELT'), 'language': lang[:2],
                                        'published': a.get('seendate', ''), 'feed_type': 'gdelt'}
                                       for a in r.json().get('articles', []))
                except Exception:
                    pass
                time.sleep(0.5)
        return out

    def fetch_newsapi(self, days=7):
        """Through newsapi_gateway (budgeted, fallback-mode). The gateway may
        legitimately return nothing -- that is its budget rule, not 'no news'."""
        if not _NEWSAPI_GATEWAY:
            return []
        out = []
        for q in self.c.get('newsapi_queries', []):
            try:
                arts = _napi_fetch(q, days=days, language='en', page_size=40,
                                   label='rhetoric/%s' % self.slug) or []
                out.extend({'title': (a.get('title') or '')[:300],
                            'description': (a.get('description') or '')[:500],
                            'url': a.get('url', ''),
                            'source': ((a.get('source') or {}).get('name') if isinstance(a.get('source'), dict)
                                       else a.get('source')) or 'NewsAPI',
                            'language': 'en', 'published': a.get('publishedAt') or a.get('published', ''),
                            'feed_type': 'newsapi'} for a in arts)
            except Exception as ex:
                self.log('NewsAPI gateway error: %s' % str(ex)[:80])
        return out

    def fetch_brave(self, weak):
        """Fallback only, when the other sources came back thin."""
        if not BRAVE_API_KEY or not weak:
            return []
        out = []
        for q in self.c.get('brave_queries', []):
            try:
                r = requests.get('https://api.search.brave.com/res/v1/news/search',
                                 params={'q': q, 'count': 20, 'freshness': 'pw'},
                                 headers={'X-Subscription-Token': BRAVE_API_KEY}, timeout=8)
                if r.status_code == 200:
                    out.extend({'title': (a.get('title') or '')[:300], 'url': a.get('url', ''),
                                'source': (a.get('meta_url') or {}).get('hostname', 'Brave'),
                                'language': 'en', 'published': a.get('page_age') or '',
                                'feed_type': 'brave'} for a in r.json().get('results', []))
            except Exception:
                pass
            time.sleep(0.5)
        return out

    def fetch_social(self, days=7):
        """Optional social lane (Bluesky). evidence_gate puts social items in
        the rumour lane: they can never confirm an event on their own."""
        target = self.c.get('bluesky_target')
        if not target:
            return []
        try:
            from bluesky_signals_europe import fetch_bluesky_for_target
            items = fetch_bluesky_for_target(target, days=days) or []
            for it in items:
                it['feed_type'] = 'bluesky'
                if isinstance(it.get('source'), dict):
                    it['source'] = it['source'].get('name', 'Bluesky')
            return items
        except Exception as ex:
            self.log('Bluesky unavailable: %s' % str(ex)[:100])
            return []

    # ── geography gate ──────────────────────────────────────────────
    def scrub(self, text):
        """Remove look-alike names before matching ('New Mexico' is not Mexico;
        the 'Gulf of Mexico' is a sea)."""
        for ph in self.c.get('scrub', ()):
            text = re.sub(r'(?<![a-z0-9])' + re.escape(fold(ph)) + r'(?![a-z0-9])', ' ', text)
        return text

    def is_about_country(self, a, text):
        c = self.c
        if any(has_phrase(text, t) for t in c['context_terms']):
            return True
        src = str(a.get('source') or '').lower()
        url = str(a.get('url') or '').lower()
        own = any(o in src or o in url for o in c.get('own_outlets', ()))
        if not own and c.get('own_tld') and c['own_tld'] in url:
            own = True
        return own and not any(has_phrase(text, f) for f in c.get('foreign_markers', ()))

    # ── classification ──────────────────────────────────────────────
    def classify(self, text):
        hits = []
        for aid, a in self.actors.items():
            gate = a.get('requires_any')
            if gate and not any(has_phrase(text, g) for g in gate):
                continue
            if any(has_phrase(text, k) for k in a['keywords']):
                hits.append(aid)
        return hits

    def tripwires(self, text):
        fired = []
        excl = self.c.get('exclusions', {})
        for aid, a in self.actors.items():
            for tw_id, sev, patterns in a.get('tripwires', []):
                if any(has_phrase(text, x) for x in excl.get(tw_id, ())):
                    continue
                if any(has_phrase(text, p) for p in patterns):
                    fired.append((aid, tw_id, sev))
        return fired

    @staticmethod
    def score(arts):
        w = {'rss': 1.5, 'newsapi': 1.2, 'google_news': 1.2, 'gdelt': 1.0, 'brave': 1.0, 'bluesky': 0.4}
        seen, s = set(), 0.0
        for a in arts:
            u = a.get('url') or a.get('title')
            if u in seen:
                continue
            seen.add(u)
            s += w.get(a.get('feed_type'), 1.0)
        return round(s, 2)

    # ── interpretation helpers ──────────────────────────────────────
    def meaning(self, key):
        return dict((self.c.get('meanings') or {}).get(key) or {})

    def meaning_sentence(self, key):
        m = (self.c.get('meanings') or {}).get(key) or {}
        return ' '.join(b for b in (m.get('plain'), m.get('global') or m.get('regional')) if b)

    def tw_plain(self, tw_id):
        return (self.c.get('tripwire_plain') or {}).get(tw_id, (tw_id.replace('_', ' '), 'governance'))

    def sig(self, category, level, short, long_text, ptype, mkey=None, actor=None,
            sources=None, kind=None, extra=None):
        level = max(0, min(4, int(level)))
        s = {'category': category, 'type': kind or category, 'theatre': self.slug,
             'level': level, 'level_name': LEVEL_NAMES[level],
             'priority': PRIORITY_BY_LEVEL.get(level, 2), 'pressure_type': ptype,
             'short_text': short[:230], 'long_text': long_text, 'actor': actor,
             'sources': sources or []}
        if mkey:
            s['what_it_means'] = self.meaning(mkey)
            s['meaning'] = self.meaning_sentence(mkey)
        if extra:
            s.update(extra)
        return s

    def tripwire_signal(self, tw):
        grade = tw.get('grade')
        what, ptype = self.tw_plain(tw['id'])[:2]
        sev = LEVEL_INT.get(tw.get('severity'), 3)
        outlets = tw.get('outlets') or []
        mk = (self.c.get('tripwire_meaning') or {}).get(tw['id'])
        if grade == 'corroborated':
            level, short = sev, '%s: %s -- reported by %d separate outlets' % (self.name, what, len(outlets) or 2)
        elif grade == 'single_source':
            level, short = min(2, sev), '%s: one outlet reports %s -- not yet corroborated' % (self.name, what)
        else:
            return None
        m = (self.c.get('meanings') or {}).get(mk) or {}
        long_text = ' '.join(x for x in (
            '%s: %s.' % (what[0].upper() + what[1:],
                         'confirmed by ' + ', '.join(outlets[:4]) if grade == 'corroborated' else 'a single report so far'),
            self.meaning_sentence(mk) if mk else '',
            m.get('not_implied', '') if grade != 'corroborated' else '') if x)
        return self.sig('tripwire_' + tw['id'], level, short, long_text, ptype, mk, actor=tw.get('actor'),
                        sources=[{'title': i.get('title'), 'url': i.get('url'), 'source': i.get('outlet')}
                                 for i in (tw.get('items') or [])[:3]],
                        kind='tripwire', extra={'evidence': grade, 'outlets': outlets})

    # ── red / green lines ───────────────────────────────────────────
    def line_status(self, line, tw_by_id):
        hits = [tw_by_id[t] for t in line['tripwires'] if t in tw_by_id]
        grades = {h['grade'] for h in hits}
        if 'corroborated' in grades:
            status = 'BREACHED' if line.get('kind', 'red') == 'red' else 'ACTIVE'
        elif 'single_source' in grades:
            status = 'APPROACHING' if line.get('kind', 'red') == 'red' else 'REPORTED'
        elif 'rumint' in grades:
            status = 'RUMOUR'
        else:
            status = 'WATCHING'
        outlets = sorted({o for h in hits for o in (h.get('outlets') or [])})
        items = [i for h in hits for i in (h.get('items') or [])][:3]
        return {'id': line['id'], 'label': line['label'], 'why': line.get('why', ''),
                'status': status, 'outlets': outlets,
                'items': [{'title': i.get('title'), 'url': i.get('url'), 'source': i.get('outlet')}
                          for i in items]}

    # ── spokes ──────────────────────────────────────────────────────
    def write_spokes(self, summaries, tripwires_global):
        written = []
        now = datetime.now(timezone.utc).isoformat()
        for hub, actor, rel, why in self.c.get('spokes', []):
            a = summaries.get(actor) or {}
            lvl = LEVEL_INT.get(a.get('level', 'low'), 0)
            n = a.get('article_count', 0)
            corro = [t for t in tripwires_global if t.get('actor') == actor and t.get('grade') == 'corroborated']
            hub_name = self.c.get('hub_names', {}).get(hub, hub.upper() if len(hub) <= 3 else hub.title())
            pair = '%s-%s' % (hub_name, self.name)
            if corro:
                top = '%s: confirmed by 2+ outlets -- %s.' % (pair, self.tw_plain(corro[0]['id'])[0])
            elif lvl >= 2:
                top = '%s reporting is busier than usual (%d items).' % (pair, n)
            elif n:
                top = '%s: routine coverage (%d items).' % (pair, n)
            else:
                top = 'No %s reporting reached the scanners this cycle -- unread, not calm.' % pair
            prev = redis_get('spoke:%s:%s' % (hub, self.slug)) or {}
            try:
                p = int(prev.get('level'))
                direction = 'expanding' if lvl > p else ('contracting' if lvl < p else 'holding')
            except (TypeError, ValueError):
                direction = 'holding'
            conf = 'corroborated' if corro else ('reported' if n else 'no_evidence')
            if redis_set('spoke:%s:%s' % (hub, self.slug), {
                    'ts': now, 'hub': hub, 'country': self.slug, 'level': lvl, 'top_signal': top,
                    'why': why, 'items': n, 'relationship': rel,
                    'trajectory': {'direction': direction, 'level': lvl, 'confidence': conf},
                    'source': 'rhetoric_tracker_%s v%s' % (self.slug, self.version)},
                    ttl_hours=SPOKE_TTL_HOURS):
                written.append(hub)
        return written

    # ── the scan ────────────────────────────────────────────────────
    def scan(self, force=False, days=7):
        if not force:
            cached = redis_get(self.cache_key)
            if cached and self._fresh(cached):
                cached['cached'] = True
                return cached
        if not self._scan_lock.acquire(blocking=False):
            cached = redis_get(self.cache_key) or redis_get(self.lastgood_key)
            if cached:
                cached['cached'] = True
                cached['scan_in_progress'] = True
                return cached
            return {'success': True, 'country': self.slug, 'pending': True, 'total_articles_scanned': 0,
                    'top_signals': [], 'top_indicator': 'First scan in progress -- check back in a few minutes.'}
        try:
            return self._scan(days)
        finally:
            self._scan_lock.release()

    def _fresh(self, data):
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(data['scanned_at'])).total_seconds()
            return age < SCAN_INTERVAL_HOURS * 3600
        except Exception:
            return False

    def _scan(self, days):
        t0 = time.time()
        self.log('scan starting')
        rss = self.fetch_rss()
        goog = self.fetch_google()
        gdelt = self.fetch_gdelt(days)
        napi = self.fetch_newsapi(days)
        brave = self.fetch_brave(weak=(len(goog) + len(gdelt) + len(napi)) < 40)
        social = self.fetch_social(days)
        counts = {'rss': len(rss), 'google_news': len(goog), 'gdelt': len(gdelt),
                  'newsapi': len(napi), 'brave': len(brave), 'bluesky': len(social)}
        seen, dedup = set(), []
        for a in rss + goog + gdelt + napi + brave + social:
            k = a.get('url') or a.get('title')
            tk = fold(a.get('title') or '')[:90]
            if k and k not in seen and tk not in seen:
                seen.add(k)
                if tk:
                    seen.add(tk)
                dedup.append(a)
        fresh, stale = drop_stale(dedup, MAX_ARTICLE_AGE_DAYS)
        kept, off = [], 0
        for a in fresh:
            text = self.scrub(article_text(a))
            if self.is_about_country(a, text):
                a['_text'] = text
                a['outlet'] = outlet_of(a)
                kept.append(a)
            else:
                off += 1
        self.log('%d fetched, %d stale, %d not about %s, %d kept'
                 % (len(dedup), stale, off, self.name, len(kept)))

        by_actor = {a: [] for a in self.actors}
        ledgers = {a: TripwireLedger() for a in self.actors}
        sev_of = {}
        for art in kept:
            for aid in self.classify(art['_text']):
                by_actor[aid].append(art)
            for aid, tw_id, sev in self.tripwires(art['_text']):
                ledgers[aid].add(tw_id, art, art['_text'])
                sev_of[(aid, tw_id)] = sev

        tripwires_global = []
        for aid, led in ledgers.items():
            for tw_id in led.ids():
                r = led.result(tw_id)
                if r['grade'] == 'none':
                    continue
                sev = sev_of.get((aid, tw_id), 3)
                tripwires_global.append({
                    'id': tw_id, 'actor': aid, 'severity': LEVEL_NAMES[max(0, min(4, sev))],
                    'grade': r['grade'], 'grade_text': r.get('grade_text', ''),
                    'outlets': r.get('outlets', []), 'rumint_outlets': r.get('rumint_outlets', []),
                    'items': r.get('items', [])})

        # Green-line (cooperation / de-escalation) tripwires never raise a level.
        green_ids = {t for g in self.c.get('green_lines', []) for t in g['tripwires']}
        summaries = {}
        for aid, cfg in self.actors.items():
            arts = by_actor[aid]
            sc = self.score(arts)
            vol = volume_level(sc, cfg['baseline'])
            level = LEVEL_NAMES[min(LEVEL_INT[vol], 2)]
            mine = [t for t in tripwires_global if t['actor'] == aid]
            for tw in mine:
                if tw['id'] in green_ids:
                    continue
                if tw['grade'] == 'corroborated':
                    level = level_max([level, tw['severity']])
                elif tw['grade'] == 'single_source':
                    level = level_max([level, LEVEL_NAMES[min(2, LEVEL_INT[tw['severity']])]])
            top = sorted(arts, key=lambda a: (a.get('feed_type') == 'rss', a.get('published') or ''),
                         reverse=True)[:8]
            summaries[aid] = {
                'name': cfg['name'], 'flag': cfg.get('flag', ''), 'icon': cfg.get('icon', ''),
                'role': cfg.get('role', ''), 'vector': cfg['vector'], 'score': sc,
                'baseline': cfg['baseline'], 'level': level, 'volume_level': vol,
                'article_count': len(arts), 'outlet_count': len({a.get('outlet') for a in arts}),
                'top_articles': [{k: v for k, v in a.items() if k != '_text'} for a in top],
                'tripwires': mine}

        vector_scores, vector_levels = {}, {}
        for vid, v in self.vectors.items():
            vector_scores[vid] = round(sum(summaries[a]['score'] for a in v['actors'] if a in summaries), 2)
            vector_levels[vid] = level_max([summaries[a]['level'] for a in v['actors'] if a in summaries])
        composite_score = round(sum(vector_scores.values()), 2)
        composite_level = level_max([s['level'] for s in summaries.values()])
        theatre_level = min(4, LEVEL_INT[composite_level])     # L5 only from kinetic ladders
        theatre_score = min(100, int(composite_score))
        corro = [t for t in tripwires_global if t['grade'] == 'corroborated' and t['id'] not in green_ids]
        tw_by_id = {}
        rank = {'corroborated': 0, 'single_source': 1, 'rumint': 2}
        for t in tripwires_global:
            cur = tw_by_id.get(t['id'])
            if cur is None or rank.get(t['grade'], 3) < rank.get(cur['grade'], 3):
                tw_by_id[t['id']] = t
        red_lines = [self.line_status(dict(l, kind='red'), tw_by_id) for l in self.c.get('red_lines', [])]
        green_lines = [self.line_status(dict(l, kind='green'), tw_by_id) for l in self.c.get('green_lines', [])]

        extras = {}
        for name, fn in (self.c.get('extra_reads') or {}).items():
            try:
                extras[name] = fn(redis_get)
            except Exception as ex:
                self.log('extra read %s failed: %s' % (name, str(ex)[:80]))

        ctx = {'summaries': summaries, 'tripwires': tripwires_global, 'tw_by_id': tw_by_id,
               'corro_ids': {t['id'] for t in corro},
               'single_ids': {t['id'] for t in tripwires_global if t['grade'] == 'single_source'},
               'vector_levels': vector_levels, 'red_lines': red_lines, 'green_lines': green_lines,
               'extras': extras, 'articles': len(kept), 'green_ids': green_ids}
        drift = self.alignment_drift(ctx)
        ctx['drift'] = drift
        top_signals = self.build_top_signals(ctx)
        top_indicator = self.build_top_indicator(ctx)
        executive_summary = self.build_executive_summary(ctx)
        so_what = self.build_so_what(ctx)

        short, long_ = self.theatre_text(theatre_level, vector_levels, ctx)
        vp = self.c.get('vector_pressure', {})
        hottest = max(vector_levels, key=lambda v: (LEVEL_INT[vector_levels[v]], vector_scores[v]), default=None)
        lead_pressure = vp.get(hottest, 'composite') if hottest and vector_levels[hottest] in ESCALATORY else 'composite'
        # a confirmed kinetic tripwire always makes the read kinetic
        if any(self.tw_plain(t)[1] == 'kinetic' for t in ctx['corro_ids'] if t not in green_ids):
            lead_pressure = 'kinetic'
        theatre_sig = {'priority': PRIORITY_BY_LEVEL.get(theatre_level, 2), 'category': 'theatre_high',
                       'type': 'theatre_read', 'theatre': self.slug, 'level': theatre_level,
                       'level_name': LEVEL_NAMES[theatre_level], 'pressure_type': lead_pressure,
                       'icon': '🔴' if theatre_level >= 4 else '🟠',
                       'color': '#ef4444' if theatre_level >= 4 else '#f97316',
                       'short_text': short, 'long_text': long_}
        top_signals = [theatre_sig] + top_signals

        spokes = self.write_spokes(summaries, tripwires_global)
        for key, ids in (self.c.get('fingerprints') or {}).items():
            hit = [i for i in ids if i in ctx['corro_ids']]
            if hit:
                redis_set(key, {'active': True, 'tripwires': hit,
                                'scanned_at': datetime.now(timezone.utc).isoformat()})

        now = datetime.now(timezone.utc).isoformat()
        breached = sum(1 for r in red_lines if r['status'] == 'BREACHED')
        result = {
            'success': True, 'country': self.slug, 'name': self.name, 'flag': self.c.get('flag', ''),
            'composite_score': composite_score, 'composite_level': composite_level,
            'theatre_level': theatre_level, 'raw_theatre_level': LEVEL_INT[composite_level],
            'theatre_score': theatre_score, 'theatre_label': WHA_LABEL[theatre_level],
            'source_class': self.c.get('source_class', 'absorber'),
            'l5_gate': {'kinetic': False, 'humanitarian': False, 'economic': False, 'diplomatic': False,
                        'any': False, 'reason': 'L5 comes only from kinetic ladders; this tracker caps at L4'},
            'l5_capped': False,
            'signal_text_short': short, 'signal_text_long': long_,
            'vector_scores': vector_scores, 'vector_levels': vector_levels,
            'vectors_meta': [{'id': vid, 'name': v['name'], 'plain': v.get('plain', ''), 'actors': v['actors']}
                             for vid, v in self.vectors.items()],
            'actor_order': list(self.actors.keys()),
            'actor_summaries': summaries, 'tripwires_global': tripwires_global,
            'red_lines': red_lines, 'green_lines': green_lines, 'red_lines_breached': breached,
            'top_signals': top_signals[:14], 'top_indicator': top_indicator, 'bluf': top_indicator,
            'executive_summary': executive_summary, 'so_what': so_what, 'alignment_drift': drift,
            'extras': extras, 'spokes_written': spokes,
            'evidence_rules': {
                'stale_dropped': stale, 'not_about_country': off, 'articles_kept': len(kept),
                'corroborated_tripwires': len(corro), 'gate_available': EVIDENCE_GATE_AVAILABLE,
                'note': ('Only articles about %s count. Busier-than-usual reporting tops out at elevated; '
                         'a high-impact event needs two separate outlets to count in full; one outlet reads '
                         'as approaching; rumour, social posts and hedged wording never lift the level.'
                         % self.name)},
            'source_counts': counts, 'total_articles_scanned': len(kept),
            'total_articles': len(kept), 'red_lines_count': breached,     # names the WHA landing banner reads
            'articles_fetched': len(dedup), 'scan_time_seconds': round(time.time() - t0, 1),
            'scanned_at': now, 'last_updated': now, 'cached': False,
            'version': self.version, 'engine_version': __version__,
            'facts_as_of': self.c.get('facts_as_of', ''),
        }
        redis_set(self.cache_key, result, CACHE_TTL_HOURS)
        if kept:
            redis_set(self.lastgood_key, result, LASTGOOD_TTL_HOURS)
        snap = {'theatre_level': theatre_level, 'theatre_score': theatre_score, 'scanned_at': now,
                'red_lines_count': breached}
        snap.update(vector_levels)
        redis_lpush_trim(self.history_key, snap)
        self.log('scan complete: L%d (%s), %d articles, %ss'
                 % (theatre_level, composite_level, len(kept), result['scan_time_seconds']))
        return result

    # ════════════════════════════════════════════════════════════════
    # INTERPRETATION (plain language; config supplies the facts)
    # ════════════════════════════════════════════════════════════════
    def theatre_text(self, level, vector_levels, ctx):
        names = {vid: v.get('plain') or v['name'].lower() for vid, v in self.vectors.items()}
        busy = [names[v] for v, lv in vector_levels.items() if lv in ESCALATORY]
        hot = [names[v] for v, lv in vector_levels.items() if lv in ('high', 'surge')]
        if hot:
            short = '%s: confirmed high-impact reporting on %s' % (self.name, ' and '.join(hot[:2]))
        elif busy:
            short = '%s: busier than usual on %s -- more news, nothing high-impact confirmed' % (
                self.name, ' and '.join(busy[:2]))
        elif ctx['articles'] < 15:
            short = '%s: thin coverage this cycle -- unread, not calm' % self.name
        else:
            short = '%s: quiet -- nothing high-impact confirmed' % self.name
        parts = ['%s reads level %d this cycle.' % (self.name, level)]
        if busy:
            parts.append('Reporting is above its usual level on ' + ', '.join(busy) + '.')
        parts.append('At least one high-impact event is confirmed by more than one outlet.' if hot else
                     'Volume alone never lifts %s above "elevated"; nothing high-impact is confirmed.' % self.name)
        return short[:230], ' '.join(parts)

    def build_top_signals(self, ctx):
        sigs = []
        for tw in ctx['tw_by_id'].values():
            if tw['id'] in ctx['green_ids']:
                continue
            s = self.tripwire_signal(tw)
            if s:
                sigs.append(s)
        # green lines that are ACTIVE are worth a signal (de-escalation), capped at L1
        for g in ctx['green_lines']:
            if g['status'] in ('ACTIVE', 'REPORTED'):
                sigs.append(self.sig('green_' + g['id'], 1,
                                     '%s: %s (%s)' % (self.name, g['label'],
                                                      'confirmed by 2+ outlets' if g['status'] == 'ACTIVE'
                                                      else 'one outlet'),
                                     g.get('why', ''), 'diplomatic', kind='off_ramp',
                                     sources=g.get('items', []), extra={'green': True}))
        # convergence: 2+ vectors busy at once
        vl = ctx['vector_levels']
        busy = [v for v, lv in vl.items() if lv in ESCALATORY]
        if len(busy) >= 2:
            names = [self.vectors[v]['name'] for v in busy]
            vp = self.c.get('vector_pressure', {})
            ptypes = {vp.get(v, 'governance') for v in busy}
            sigs.append(self.sig('convergence', min(3, max(LEVEL_INT[vl[v]] for v in busy)),
                                 '%s: several areas are busier than usual at once -- %s' % (
                                     self.name, ' and '.join(names[:3])),
                                 'More than one part of the %s picture is active in the same week: %s. '
                                 'Pressures that usually move separately are moving together.' % (
                                     self.name, ', '.join(names)),
                                 ptypes.pop() if len(ptypes) == 1 else ('kinetic' if 'kinetic' in ptypes else 'governance'),
                                 kind='convergence'))
        covered = {t['actor'] for t in ctx['tw_by_id'].values()
                   if t['grade'] in ('corroborated', 'single_source') and t['id'] not in ctx['green_ids']}
        ameaning = self.c.get('actor_meaning') or {}
        for aid, a in ctx['summaries'].items():
            if a['level'] not in ESCALATORY or aid in covered:
                continue
            mk = ameaning.get(aid)
            m = (self.c.get('meanings') or {}).get(mk) or {}
            long_text = ' '.join(x for x in (
                'Coverage of %s is running above its usual weekly level. This counts reporting, not events: '
                'it says something is happening there, not how serious it is.' % a['name'],
                self.meaning_sentence(mk) if mk else '', m.get('not_implied', '')) if x)
            ptype = self.c.get('vector_pressure', {}).get(a['vector'], 'governance')
            sigs.append(self.sig('actor_volume', LEVEL_INT[a['level']],
                                 '%s: more reporting than usual on %s (%d items from %d outlet%s)' % (
                                     self.name, a['name'], a['article_count'], a['outlet_count'],
                                     '' if a['outlet_count'] == 1 else 's'),
                                 long_text, ptype, mk, actor=aid, kind='actor_signal',
                                 sources=[{'title': x.get('title'), 'url': x.get('url'),
                                           'source': x.get('outlet') or x.get('source')}
                                          for x in a['top_articles'][:3]]))
        if ctx.get('drift') and ctx['drift'].get('band') not in (None, 'US-anchored'):
            d = ctx['drift']
            sigs.append(self.sig('alignment_drift', d['level'],
                                 '%s: China and the US competing for influence -- %s' % (self.name, d['band'].lower()),
                                 (d['so_what_factor'] + ' ' + d['disclaimer'])[:480], 'diplomatic',
                                 self.c.get('drift_meaning'), kind='alignment_drift'))
        for fn in (self.c.get('extra_signals') or []):
            try:
                sigs.extend(fn(self, ctx) or [])
            except Exception as ex:
                self.log('extra signal error: %s' % str(ex)[:100])
        sigs.sort(key=lambda s: (-s['level'], -len(s.get('sources') or [])))
        return sigs[:13]

    def build_top_indicator(self, ctx):
        corro = [t for t in ctx['tw_by_id'].values() if t['grade'] == 'corroborated' and t['id'] not in ctx['green_ids']]
        single = [t for t in ctx['tw_by_id'].values() if t['grade'] == 'single_source' and t['id'] not in ctx['green_ids']]
        busy = sorted(((k, a) for k, a in ctx['summaries'].items() if a['level'] in ESCALATORY),
                      key=lambda kv: -kv[1]['score'])
        breached = [r for r in ctx['red_lines'] if r['status'] == 'BREACHED']
        if breached:
            r = breached[0]
            main = 'Red line crossed, confirmed by more than one outlet: %s. %s' % (
                r['label'][0].lower() + r['label'][1:], r.get('why', ''))
        elif corro:
            t = max(corro, key=lambda x: LEVEL_INT.get(x['severity'], 3))
            mk = (self.c.get('tripwire_meaning') or {}).get(t['id'])
            m = (self.c.get('meanings') or {}).get(mk) or {}
            main = 'Confirmed by more than one outlet: %s. %s' % (self.tw_plain(t['id'])[0],
                                                                  m.get('global') or m.get('plain') or '')
        elif busy:
            main = ('Nothing high-impact is confirmed in %s. Reporting is busier than usual on %s -- '
                    'more news, not a crisis.' % (self.name, ' and '.join(a['name'] for _, a in busy[:2])))
        else:
            main = '%s reads quiet: nothing high-impact is confirmed and no area is unusually busy.' % self.name
        if single and not corro:
            main += ' Watching: one outlet reports %s, not yet corroborated.' % self.tw_plain(single[0]['id'])[0]
        act = [g for g in ctx['green_lines'] if g['status'] == 'ACTIVE']
        if act:
            main += ' Cooperation signal: %s.' % act[0]['label'].lower()
        if ctx['articles'] < 30 and not corro:
            main += ' Coverage is thin this cycle, so quiet may be unread rather than calm.'
        return main.strip()

    def build_executive_summary(self, ctx):
        parts = []
        corro = sorted({self.tw_plain(t)[0] for t in ctx['corro_ids'] if t not in ctx['green_ids']})
        busy = [self.vectors[v].get('plain') or self.vectors[v]['name'].lower()
                for v, lv in ctx['vector_levels'].items() if lv in ESCALATORY]
        if corro:
            parts.append('High-impact events confirmed by more than one outlet: ' + '; '.join(corro[:3]) + '.')
        if busy:
            parts.append('Reporting is busier than usual on ' + ', '.join(busy) + '.')
        if not corro and not busy:
            parts.append('%s reads quiet this cycle: no area is unusually busy and nothing high-impact is confirmed.'
                         % self.name)
        single = sorted({self.tw_plain(t)[0] for t in ctx['single_ids'] if t not in ctx['green_ids']})
        if single:
            parts.append('Single-outlet reports not yet corroborated: ' + ', '.join(single[:3]) + '.')
        if self.c.get('background'):
            parts.append(self.c['background'])
        return ' '.join(parts)

    def build_so_what(self, ctx):
        bullets = []
        covered_vectors = set()        # v1.0.1: an event bullet already speaks for its vector
        for rule in self.c.get('so_what_rules', []):
            ids = set(rule['tripwires'])
            hit = (ids & ctx['corro_ids']) or (ids & ctx['single_ids'] if rule.get('single') else set())
            if ids & ctx['corro_ids']:
                bullets.append({'bullet': rule['confirmed'], 'weight': rule.get('weight', 5.0)})
            elif ids & ctx['single_ids'] and rule.get('single'):
                bullets.append({'bullet': rule['single'], 'weight': rule.get('weight', 5.0) - 1.2})
            for t in hit:
                aid = (ctx['tw_by_id'].get(t) or {}).get('actor')
                if aid in self.actors:
                    covered_vectors.add(self.actors[aid]['vector'])
        d = ctx.get('drift')
        if d and d.get('band') in ('Contested', 'Drifting', 'Realigning'):
            bullets.append({'bullet': 'China and the US: ' + d['so_what_factor'], 'weight': 5.0})
        for vid, (w, text) in (self.c.get('vector_so_what') or {}).items():
            if ctx['vector_levels'].get(vid) in ESCALATORY and vid not in covered_vectors:
                bullets.append({'bullet': text, 'weight': w})
        for fn in (self.c.get('extra_so_what') or []):
            try:
                bullets.extend(fn(self, ctx) or [])
            except Exception as ex:
                self.log('extra so-what error: %s' % str(ex)[:100])
        if not bullets:
            bullets.append({'bullet': self.c.get('quiet_so_what', '%s reads quiet this cycle.' % self.name),
                            'weight': 1.0})
        # The standing structural So What always closes the list (the unasked question).
        for s in self.c.get('standing_so_what', []):
            bullets.append({'bullet': s, 'weight': 0.5, 'standing': True})
        bullets.sort(key=lambda b: -b['weight'])
        return bullets[:8]

    def alignment_drift(self, ctx):
        p = self.c.get('drift_profile')
        if not p:
            return None
        s = ctx['summaries']
        inroad = LEVEL_INT.get((s.get(p['inroad_actor']) or {}).get('level', 'low'), 0)
        counter = LEVEL_INT.get((s.get(p['counter_actor']) or {}).get('level', 'low'), 0)
        i_tw = [t for t in p['inroad_tripwires'] if t in ctx['corro_ids']]
        c_tw = [t for t in p['counter_tripwires'] if t in ctx['corro_ids']]
        inroad += len(i_tw)
        counter += len(c_tw)
        if inroad <= 1:
            band = 'US-anchored'
        elif inroad >= 2 and counter >= 2:
            band = 'Contested'
        elif inroad - counter >= 3 and inroad >= 4:
            band = 'Realigning'
        elif inroad - counter >= 2:
            band = 'Drifting'
        elif counter >= 2:
            band = 'Contested'
        else:
            band = 'US-anchored'
        meta = {'US-anchored': (1, '#38bdf8', 4), 'Contested': (2, '#f59e0b', 7),
                'Drifting': (3, '#f97316', 8), 'Realigning': (4, '#dc2626', 11)}[band]
        return {'id': 'bri_inroad_' + self.slug, 'country': self.slug, 'band': band,
                'inroad_power': 'China', 'incumbent_power': 'the US',
                'inroad_score': inroad, 'counter_score': counter, 'net': inroad - counter,
                'active_inroad_tripwires': i_tw, 'active_counter_tripwires': c_tw,
                'so_what_factor': p['so_what'][band],
                'leading_indicators': list(p['leading_indicators']),
                'disclaimer': ('A convergence / influence indicator, not a prediction of realignment. '
                               '%s keeps full agency over its partners.' % self.name),
                'level': meta[0], 'color': meta[1], 'priority': meta[2], 'icon': '🧭'}

    # ════════════════════════════════════════════════════════════════
    # FLASK
    # ════════════════════════════════════════════════════════════════
    def _local_force_ok(self):
        with self._lock:
            now = time.time()
            if now - self._last_forced[0] < FORCE_GAP_SECONDS:
                return False
            self._last_forced[0] = now
            return True

    def register(self, app, force_gate=None, start_background=True, warmup_seconds=180):
        from flask import jsonify, request
        slug = self.slug

        def _view():
            if request.method == 'OPTIONS':
                return '', 200
            try:
                force = request.args.get('refresh', request.args.get('force', 'false')).lower() in ('true', '1', 'yes')
                if force:
                    ok = force_gate('rhetoric/%s' % slug) if force_gate else True
                    force = ok and self._local_force_ok()
                return jsonify(self.scan(force=force))
            except Exception as ex:
                return jsonify({'success': False, 'country': slug, 'error': str(ex)[:200]}), 500

        def _debug():
            cached = redis_get(self.cache_key)
            return jsonify({
                'version': self.version, 'engine_version': __version__, 'cache_key': self.cache_key,
                'actors': len(self.actors), 'vectors': len(self.vectors),
                'rss_feeds': list(self.c.get('rss_feeds', {}).keys()),
                'google_queries': len(self.c.get('google_queries', [])),
                'gdelt_queries': len(self.c.get('gdelt_en', [])) + len(self.c.get('gdelt_es', [])),
                'newsapi_gateway': _NEWSAPI_GATEWAY, 'brave_configured': bool(BRAVE_API_KEY),
                'redis_configured': bool(UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN),
                'feedparser': FEEDPARSER_AVAILABLE, 'evidence_gate': EVIDENCE_GATE_AVAILABLE,
                'last_scan': (cached or {}).get('scanned_at'),
                'last_level': (cached or {}).get('theatre_level'),
                'source_counts': (cached or {}).get('source_counts'),
            })

        app.add_url_rule('/api/rhetoric/%s' % slug, 'rhetoric_%s' % slug, _view, methods=['GET', 'OPTIONS'])
        app.add_url_rule('/api/rhetoric/%s/debug' % slug, 'rhetoric_%s_debug' % slug, _debug, methods=['GET'])

        if start_background:
            def _loop():
                time.sleep(warmup_seconds)
                while True:
                    try:
                        self.scan(force=True)
                    except Exception as ex:
                        self.log('background scan error: %s' % str(ex)[:200])
                    time.sleep(SCAN_INTERVAL_HOURS * 3600)
            threading.Thread(target=_loop, daemon=True, name='%sRhetoricBG' % self.name).start()
        self.log('endpoints registered: /api/rhetoric/%s (+/debug)' % slug)
