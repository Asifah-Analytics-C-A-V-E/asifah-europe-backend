"""
europe_feeds.py -- v1.0.0 -- November 3, 2026
Asifah Analytics -- Europe backend (shared fetch helper, no Flask)

ONE place for the plumbing the Greenland / Cyprus / Azerbaijan trackers each
re-implemented (and Russia / Hungary / the rest can adopt next):

  fetch_rss_items(url, tracker)   RSS / Google News -> items whose 'source' is the
                                  PUBLISHER. The old trackers stored the FEED URL
                                  as the source, so six Google News feeds counted
                                  as six "sources" and no red line could ever
                                  count outlets.
  fetch_gdelt_items(q, lang, ...) GDELT through gdelt_gateway (paced, circuit
                                  breaker). Returns (items, sensed) -- sensed=False
                                  means we never got to look, not "quiet".
  gnews_url(query, lang)          Google News search URL builder.
  user_agent(tracker)             honest, descriptive UA (browser impersonation
                                  is what Reddit and others 403).

Every item: {title, url, published, source, feed, body, description}
  'body' is lower-cased title + description (the trackers' scoring field).
"""

import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse

import requests

FEEDS_VERSION = '1.0.0'

try:
    from gdelt_gateway import gdelt_fetch_probed as _gw_fetch_probed
    GDELT_GATEWAY = True
except ImportError:
    GDELT_GATEWAY = False

_TAG = re.compile(r'<[^>]+>')


def user_agent(tracker):
    return (f'AsifahAnalytics-Europe-{tracker}/1.1 '
            f'(OSINT monitoring tool; +https://asifahanalytics.com)')


def gnews_url(query, lang='en'):
    region = {'en': ('en-US', 'US', 'US:en'), 'da': ('da', 'DK', 'DK:da'), 'tr': ('tr', 'TR', 'TR:tr'),
              'el': ('el', 'GR', 'GR:el'), 'ru': ('ru', 'RU', 'RU:ru'), 'az': ('az', 'AZ', 'AZ:az')}
    hl, gl, ceid = region.get(lang, region['en'])
    return (f'https://news.google.com/rss/search?q={quote_plus(query + " when:7d")}'
            f'&hl={hl}&gl={gl}&ceid={ceid}')


def _host_name(url):
    host = urlparse(url or '').netloc.lower()
    return host[4:] if host.startswith('www.') else host


def _pub(text):
    if not text:
        return ''
    try:
        return parsedate_to_datetime(text).isoformat()
    except Exception:
        return text


def fetch_rss_items(url, tracker, max_items=15, timeout=10, topic_terms=None):
    """RSS or Google News feed -> (items, ok). The publisher is read from the
    item's <source> element or the ' - Outlet' title suffix (Google News), else
    the feed's host name. topic_terms: if given, only items mentioning one pass."""
    items = []
    is_gnews = 'news.google.com' in (url or '')
    try:
        resp = requests.get(url, headers={'User-Agent': user_agent(tracker)}, timeout=timeout)
        if resp.status_code != 200:
            print(f'[{tracker} RSS] HTTP {resp.status_code} -- {url[:70]}')
            return items, False
        root = ET.fromstring(resp.content)
        feed_host = _host_name(url)
        for item in root.findall('.//item')[:max(max_items, 40 if topic_terms else max_items)]:
            title = (item.findtext('title') or '').strip()
            if not title:
                continue
            link = (item.findtext('link') or '').strip()
            desc = _TAG.sub(' ', item.findtext('description') or '')[:400]
            if topic_terms:
                blob = (title + ' ' + desc).lower()
                if not any(t in blob for t in topic_terms):
                    continue
            if is_gnews:
                src_el = item.find('source')
                publisher = (src_el.text or '').strip() if src_el is not None else ''
                if not publisher and ' - ' in title:
                    publisher = title.rsplit(' - ', 1)[1].strip()
                desc = ''          # Google News descriptions are just the title again, as HTML
            else:
                publisher = feed_host
            items.append({
                'title': title, 'url': link, 'published': _pub(item.findtext('pubDate')),
                'source': publisher or feed_host or 'unknown',
                'feed': 'gnews' if is_gnews else 'rss',
                'description': desc,
                'body': f'{title} {desc}'.lower(),
            })
            if len(items) >= max_items:
                break
        return items, True
    except Exception as e:
        print(f'[{tracker} RSS] {type(e).__name__}: {str(e)[:90]} -- {url[:70]}')
        return items, False


def fetch_gdelt_items(query, tracker, lang='eng', days=5, maxrecords=50):
    """GDELT through the shared gateway. -> (items, sensed)."""
    out = []
    if GDELT_GATEWAY:
        raw, probe = _gw_fetch_probed(query, language=lang, timespan=f'{days * 24}h',
                                      maxrecords=maxrecords, label=f'{tracker.lower()}/{lang}')
        sensed = bool(probe.get('sensed'))
    else:
        try:
            r = requests.get('https://api.gdeltproject.org/api/v2/doc/doc',
                             params={'query': query, 'mode': 'artlist', 'maxrecords': maxrecords,
                                     'timespan': f'{days}d', 'sourcelang': lang, 'format': 'json'},
                             headers={'User-Agent': user_agent(tracker)}, timeout=(10, 25))
            raw = (r.json().get('articles') or []) if r.status_code == 200 else []
            sensed = r.status_code == 200
        except Exception:
            raw, sensed = [], False
    for a in raw or []:
        title = a.get('title', '') or ''
        url = a.get('url', '') or ''
        out.append({
            'title': title, 'url': url,
            'published': a.get('published') or a.get('seendate', ''),
            'source': a.get('domain') or a.get('source') or _host_name(url),
            'feed': 'gdelt', 'description': '',
            'body': f'{title} {url.replace("-", " ")}'.lower(),
        })
    return out, sensed


def gather(tracker, rss_feeds, gdelt_queries, days=5, topic_terms=None, gdelt_pause=0.0):
    """Fetch every feed and query, de-duplicate by URL. -> (articles, sensing)."""
    articles, seen = [], set()
    sensing = {'rss': {'attempted': 0, 'ok': 0, 'items': 0},
               'gnews': {'attempted': 0, 'ok': 0, 'items': 0},
               'gdelt': {'attempted': 0, 'sensed': 0, 'items': 0}}
    for url in rss_feeds:
        fam = 'gnews' if 'news.google.com' in url else 'rss'
        sensing[fam]['attempted'] += 1
        got, ok = fetch_rss_items(url, tracker, topic_terms=None if fam == 'gnews' else topic_terms)
        if ok:
            sensing[fam]['ok'] += 1
        for a in got:
            if a['url'] and a['url'] not in seen:
                seen.add(a['url'])
                articles.append(a)
                sensing[fam]['items'] += 1
        time.sleep(0.3)
    for q, lang in gdelt_queries:
        sensing['gdelt']['attempted'] += 1
        got, sensed = fetch_gdelt_items(q, tracker, lang=lang, days=days)
        if sensed:
            sensing['gdelt']['sensed'] += 1
        for a in got:
            if a['url'] and a['url'] not in seen:
                seen.add(a['url'])
                articles.append(a)
                sensing['gdelt']['items'] += 1
        if gdelt_pause:
            time.sleep(gdelt_pause)
    sensing['any_sensed'] = bool(sensing['rss']['ok'] or sensing['gnews']['ok'] or sensing['gdelt']['sensed'])
    sensing['degraded'] = (sensing['gdelt']['attempted'] > 0 and sensing['gdelt']['sensed'] == 0) \
        or not sensing['any_sensed']
    print(f"[{tracker}] Sources: RSS {sensing['rss']['ok']}/{sensing['rss']['attempted']}, "
          f"GNews {sensing['gnews']['ok']}/{sensing['gnews']['attempted']}, "
          f"GDELT {sensing['gdelt']['sensed']}/{sensing['gdelt']['attempted']} sensed -> {len(articles)} articles")
    return articles, sensing


# ---------------------------------------------------------------------------
# Evidence-capped actor scoring (shared by the inverted / vectored trackers)
# ---------------------------------------------------------------------------
def breadth_cap(n_outlets):
    """Volume can never climb above evidence. Distinct publishers -> max level:
    0 -> 0, 1 -> 1, 2 -> 2, 3-4 -> 3, 5+ -> 4. Nothing reaches L5 on breadth --
    only kinetic ladders may assert L5 (L5 assertion rule)."""
    if n_outlets <= 0:
        return 0
    if n_outlets == 1:
        return 1
    if n_outlets == 2:
        return 2
    if n_outlets <= 4:
        return 3
    return 4


def volume_level(raw_score):
    if raw_score >= 85:
        return 5
    if raw_score >= 65:
        return 4
    if raw_score >= 45:
        return 3
    if raw_score >= 28:
        return 2
    if raw_score >= 12:
        return 1
    return 0


_TIERS_THAT_COUNT = {'official', 'wire', 'mainstream', 'aggregator', 'aligned', 'state'}


def score_actor(actor_id, actor_cfg, articles, telegram_msgs, escalation_levels):
    """The trackers' shared actor scorer, with the evidence cap applied.
    raw_score (volume) is kept for the composite so history stays comparable;
    `level` is min(volume level, breadth cap)."""
    keywords = [kw.lower() for kw in actor_cfg['keywords']]
    hits, hit_count, outlets = [], 0, set()
    for art in articles:
        body = (art.get('body') or '').lower()
        matched = [kw for kw in keywords if kw in body]
        if matched:
            hit_count += len(matched)
            outlets.add(str(art.get('source') or '').lower())
            hits.append({'title': (art.get('title') or '')[:150], 'url': art.get('url', ''),
                         'source': art.get('source', ''), 'published': art.get('published', ''),
                         'matched_keywords': matched[:5]})
    tg_hits = 0
    for msg in telegram_msgs or []:
        body = (msg.get('title') or '').lower()
        matched = [kw for kw in keywords if kw in body]
        if matched:
            tg_hits += len(matched)
            hit_count += len(matched)
            if msg.get('source_tier') in _TIERS_THAT_COUNT:
                outlets.add(str(msg.get('source') or '').lower())
    outlets.discard('')
    baseline = actor_cfg.get('baseline_statements_per_week', 8)
    weight = actor_cfg.get('weight', 1.0)
    raw_score = min(100, int((hit_count / max(baseline, 1)) * 25 * weight))
    vol = volume_level(raw_score)
    level = min(vol, breadth_cap(len(outlets)))
    info = escalation_levels[level]
    return {
        'actor': actor_id, 'name': actor_cfg['name'], 'flag': actor_cfg['flag'], 'icon': actor_cfg['icon'],
        'color': actor_cfg['color'], 'role': actor_cfg['role'],
        'raw_score': raw_score, 'level': level, 'volume_level': vol, 'outlet_count': len(outlets),
        'capped': level < vol,
        'label': info['label'], 'escalation_color': info['color'], 'description': info['description'],
        'article_hits': len(hits), 'keyword_hits': hit_count, 'telegram_hits': tg_hits,
        'top_articles': hits[:5],
    }
