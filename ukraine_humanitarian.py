"""
Ukraine Humanitarian Data Module v1.1.0
November 3, 2026   (v1.0.0 March 2026)

v1.1.0 (Nov 3 2026)
  * The news feed's three GDELT calls now go through gdelt_gateway. They were
    direct calls on the same IP as every tracker, outside the circuit breaker --
    part of the load that keeps tripping it.
  * Honest User-Agent on RSS / GDELT / Reddit (was 'Mozilla/5.0' -- a browser
    impersonation; Reddit 403s it).
  * Static notes dated to what is actually known: EU temporary protection runs
    to March 2027 (extended June 2025); the peace-talks line is no longer the
    March 2026 "postponed due to Iran crisis".

Fetches humanitarian crisis data from:
  - IOM DTM API v3 (displacement/IDP tracking - DYNAMIC)
  - ReliefWeb API (OCHA reports - DYNAMIC)
  - Static reference data (casualties, energy, infrastructure - updated manually)

Provides /api/ukraine/humanitarian endpoint for the Ukraine stability page.

Env vars required (set on Europe backend):
  - DTM_API_KEY: IOM DTM API v3 subscription key
  - UPSTASH_REDIS_URL: Redis cache URL
  - UPSTASH_REDIS_TOKEN: Redis cache token

Pattern: Redis-first caching with 6-hour TTL + background refresh.
"""

import os
import json
import requests
import threading
import time
from flask import request, jsonify
from datetime import datetime, timezone, timedelta

# ========================================
# CONFIGURATION
# ========================================

DTM_API_KEY = os.environ.get('DTM_API_KEY')
DTM_BASE_URL = 'https://dtmapi.iom.int/v3'

# ReliefWeb API (open, no key needed)
RELIEFWEB_API_URL = 'https://api.reliefweb.int/v1'

# Redis (same env vars as Europe backend app.py)
UPSTASH_URL = os.environ.get('UPSTASH_REDIS_URL')
UPSTASH_TOKEN = os.environ.get('UPSTASH_REDIS_TOKEN')
CACHE_KEY = 'ukraine_humanitarian'
NEWS_CACHE_KEY = 'ukraine_news'

HONEST_UA = 'AsifahAnalytics-Europe-UkraineHumanitarian/1.1 (OSINT monitoring tool; +https://asifahanalytics.com)'

try:
    from gdelt_gateway import gdelt_fetch_probed as _gw_fetch_probed
    GDELT_GATEWAY = True
except ImportError:
    GDELT_GATEWAY = False

# Background refresh interval (6 hours)
REFRESH_INTERVAL_SECONDS = 6 * 3600


# ========================================
# REDIS HELPERS
# ========================================

def _redis_available():
    return bool(UPSTASH_URL and UPSTASH_TOKEN)


def _redis_get(key):
    try:
        response = requests.get(
            f"{UPSTASH_URL}/get/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            timeout=5
        )
        data = response.json()
        if data.get('result'):
            return json.loads(data['result'])
        return None
    except Exception as e:
        print(f"[Ukraine Redis] GET error: {str(e)[:100]}")
        return None


def _redis_set(key, value):
    try:
        response = requests.post(
            f"{UPSTASH_URL}",
            headers={
                "Authorization": f"Bearer {UPSTASH_TOKEN}",
                "Content-Type": "application/json"
            },
            json=["SET", key, json.dumps(value)],
            timeout=5
        )
        result = response.json()
        if result.get('result') == 'OK':
            print(f"[Ukraine Redis] Saved key: {key}")
            return True
        return False
    except Exception as e:
        print(f"[Ukraine Redis] SET error: {str(e)[:100]}")
        return False


# ========================================
# DTM API — IDP DISPLACEMENT DATA
# ========================================

def fetch_dtm_displacement():
    """
    Fetch Ukraine IDP data from IOM DTM API v3.
    IOM has extensive Ukraine data (22+ rounds since 2022).
    Returns country-level and oblast-level displacement figures.
    """
    if not DTM_API_KEY:
        print("[Ukraine DTM] No DTM_API_KEY configured")
        return None

    headers = {
        'Ocp-Apim-Subscription-Key': DTM_API_KEY,
        'Accept': 'application/json'
    }

    result = {
        'source': 'IOM DTM API v3',
        'source_url': 'https://dtm.iom.int/ukraine',
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'country_level': None,
        'oblast_level': [],
        'error': None
    }

    # Country-level (Admin 0)
    try:
        print("[Ukraine DTM] Fetching country-level IDP data...")
        params = {
            'CountryName': 'Ukraine',
            'FromReportingDate': '2024-01-01',
            'ToReportingDate': datetime.now().strftime('%Y-%m-%d')
        }
        response = requests.get(
            f'{DTM_BASE_URL}/displacement/admin0',
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                latest = sorted(data, key=lambda x: x.get('reportingDate', ''), reverse=True)
                if latest:
                    most_recent = latest[0]
                    result['country_level'] = {
                        'total_idps': most_recent.get('numPresentIdpInd', 0),
                        'reporting_date': most_recent.get('reportingDate', ''),
                        'round_number': most_recent.get('roundNumber', ''),
                        'operation': most_recent.get('operation', ''),
                        'displacement_reason': most_recent.get('displacementReason', ''),
                        'males': most_recent.get('numberMales', 0),
                        'females': most_recent.get('numberFemales', 0),
                    }
                    print(f"[Ukraine DTM] Country-level: {most_recent.get('numPresentIdpInd', 0):,} IDPs (Round {most_recent.get('roundNumber', '?')})")
            else:
                print("[Ukraine DTM] Country-level: No data returned")
        else:
            print(f"[Ukraine DTM] Country-level: HTTP {response.status_code}")
            result['error'] = f"HTTP {response.status_code}"

    except Exception as e:
        result['error'] = f"DTM country-level error: {str(e)[:200]}"
        print(f"[Ukraine DTM] Country error: {str(e)[:200]}")

    # Oblast-level (Admin 1)
    try:
        print("[Ukraine DTM] Fetching oblast-level IDP data...")
        params = {
            'CountryName': 'Ukraine',
            'FromReportingDate': '2024-01-01',
            'ToReportingDate': datetime.now().strftime('%Y-%m-%d')
        }
        response = requests.get(
            f'{DTM_BASE_URL}/displacement/admin1',
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                admin1_latest = {}
                for entry in data:
                    admin1 = entry.get('admin1Name', 'Unknown')
                    date = entry.get('reportingDate', '')
                    if admin1 not in admin1_latest or date > admin1_latest[admin1].get('reportingDate', ''):
                        admin1_latest[admin1] = entry

                for admin1, entry in sorted(admin1_latest.items()):
                    result['oblast_level'].append({
                        'oblast': admin1,
                        'idps': entry.get('numPresentIdpInd', 0),
                        'reporting_date': entry.get('reportingDate', ''),
                        'round': entry.get('roundNumber', ''),
                    })

                total_oblast = sum(g['idps'] for g in result['oblast_level'])
                print(f"[Ukraine DTM] Oblast-level: {len(result['oblast_level'])} oblasts, {total_oblast:,} total")
        else:
            print(f"[Ukraine DTM] Oblast-level: HTTP {response.status_code}")

    except Exception as e:
        print(f"[Ukraine DTM] Oblast error: {str(e)[:200]}")

    return result


# ========================================
# RELIEFWEB API — OCHA/UN REPORTS
# ========================================

def fetch_reliefweb_updates():
    """Fetch latest OCHA/UN reports for Ukraine from ReliefWeb."""
    result = {
        'source': 'ReliefWeb API',
        'source_url': 'https://reliefweb.int/country/ukr',
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'reports': [],
        'error': None
    }

    try:
        print("[Ukraine ReliefWeb] Fetching reports...")
        params = {
            'appname': 'asifah-analytics',
            'query[value]': 'Ukraine displacement IDP humanitarian energy attacks',
            'query[operator]': 'AND',
            'sort[]': 'date:desc',
            'limit': 8,
            'fields[include][]': ['title', 'date.created', 'url_alias', 'source.name'],
        }

        response = requests.get(
            f'{RELIEFWEB_API_URL}/reports',
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            reports = data.get('data', [])
            for report in reports[:8]:
                fields = report.get('fields', {})
                result['reports'].append({
                    'title': fields.get('title', ''),
                    'date': fields.get('date', {}).get('created', ''),
                    'url': f"https://reliefweb.int{fields.get('url_alias', '')}",
                    'source': fields.get('source', [{}])[0].get('name', 'OCHA') if fields.get('source') else 'OCHA',
                })
            print(f"[Ukraine ReliefWeb] Found {len(result['reports'])} reports")
        else:
            result['error'] = f"HTTP {response.status_code}"

    except Exception as e:
        result['error'] = str(e)[:200]
        print(f"[Ukraine ReliefWeb] Error: {str(e)[:200]}")

    return result


# ========================================
# NEWS FEED (backend-cached, 4-hour TTL)
# ========================================

def _gdelt(query, lang, maxrecords):
    """GDELT through the shared gateway (paced, circuit-breaker). Returns a list of
    article dicts with title/url/seendate/domain, or None when GDELT did not answer."""
    if GDELT_GATEWAY:
        raw, probe = _gw_fetch_probed(query, language=lang, timespan='72h', maxrecords=maxrecords,
                                      label=f'ukraine_news/{lang}')
        if not probe.get('sensed'):
            return None
        return [{'title': a.get('title', ''), 'url': a.get('url', ''),
                 'seendate': a.get('published') or a.get('seendate', ''),
                 'domain': a.get('domain') or a.get('source', '')} for a in (raw or [])]
    try:
        r = requests.get('https://api.gdeltproject.org/api/v2/doc/doc',
                         params={'query': query, 'mode': 'ArtList', 'maxrecords': maxrecords, 'format': 'json',
                                 'sort': 'DateDesc', 'timespan': '3d', 'sourcelang': lang},
                         timeout=(10, 25), headers={'User-Agent': HONEST_UA})
        return (r.json().get('articles') or []) if r.status_code == 200 else None
    except Exception:
        return None


def fetch_ukraine_news():
    """
    Fetch Ukraine conflict news from multiple sources.
    Redis-cached with 4-hour TTL.
    Sources: Ukrinform RSS, Kyiv Independent, GDELT, Reddit
    """
    print("[Ukraine News] Fetching articles...")

    all_articles = {
        'ukrinform': [],
        'kyiv_independent': [],
        'english': [],
        'ukrainian': [],
        'russian': [],
        'reddit': [],
    }

    import xml.etree.ElementTree as ET

    # ── 1. Ukrinform RSS (English) ──
    try:
        response = requests.get(
            'https://www.ukrinform.net/rss/block-lastnews',
            timeout=10,
            headers={'User-Agent': HONEST_UA}
        )
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            for item in items[:15]:
                title = item.find('title')
                link = item.find('link')
                pub = item.find('pubDate')
                if title is not None:
                    all_articles['ukrinform'].append({
                        'title': title.text or '',
                        'url': link.text if link is not None else '',
                        'published': pub.text if pub is not None else '',
                        'source': 'Ukrinform'
                    })
            print(f"[Ukraine News] Ukrinform: {len(all_articles['ukrinform'])} articles")
    except Exception as e:
        print(f"[Ukraine News] Ukrinform error: {str(e)[:80]}")

    # ── 2. Ukrainska Pravda (English) + Kyiv Post RSS ──
    for rss_name, rss_url in [('Ukrainska Pravda', 'https://www.pravda.com.ua/eng/rss/view_news/'), ('Kyiv Post', 'https://www.kyivpost.com/feed')]:
        try:
            response = requests.get(
                rss_url,
                timeout=10,
                headers={'User-Agent': HONEST_UA}
            )
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                for item in items[:10]:
                    title = item.find('title')
                    link = item.find('link')
                    pub = item.find('pubDate')
                    if title is not None:
                        all_articles['kyiv_independent'].append({
                            'title': title.text or '',
                            'url': link.text if link is not None else '',
                            'published': pub.text if pub is not None else '',
                            'source': rss_name
                        })
                print(f"[Ukraine News] {rss_name}: {len(items[:10])} articles")
        except Exception as e:
            print(f"[Ukraine News] {rss_name} error: {str(e)[:80]}")

    # ── 3. GDELT English ──
    try:
        _arts = _gdelt('ukraine war conflict', 'eng', 15)
        if _arts is not None:
            for article in _arts[:15]:
                # Exclude Ukrainian sources (already covered by RSS)
                domain = article.get('domain', '')
                if 'ukrinform' in domain or 'kyivindependent' in domain:
                    continue
                all_articles['english'].append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'published': article.get('seendate', ''),
                    'source': article.get('domain', 'GDELT')
                })
            print(f"[Ukraine News] GDELT EN: {len(all_articles['english'])} articles")
    except Exception as e:
        print(f"[Ukraine News] GDELT EN error: {str(e)[:80]}")

    # ── 4. GDELT Ukrainian ──
    try:
        _arts = _gdelt('ukraine OR Україна OR війна', 'ukr', 10)
        if _arts is not None:
            for article in _arts[:10]:
                all_articles['ukrainian'].append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'published': article.get('seendate', ''),
                    'source': article.get('domain', 'GDELT-UK')
                })
            print(f"[Ukraine News] GDELT UK: {len(all_articles['ukrainian'])} articles")
    except Exception as e:
        print(f"[Ukraine News] GDELT UK error: {str(e)[:80]}")

    # ── 5. GDELT Russian ──
    try:
        _arts = _gdelt('Украина война', 'rus', 10)
        if _arts is not None:
            for article in _arts[:10]:
                all_articles['russian'].append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'published': article.get('seendate', ''),
                    'source': article.get('domain', 'GDELT-RU')
                })
            print(f"[Ukraine News] GDELT RU: {len(all_articles['russian'])} articles")
    except Exception as e:
        print(f"[Ukraine News] GDELT RU error: {str(e)[:80]}")

    # ── 6. Reddit ──
    subreddits = ['ukraineconflict', 'ukraine', 'UkrainianConflict', 'geopolitics']
    for sub in subreddits:
        try:
            response = requests.get(
                f'https://www.reddit.com/r/{sub}/new.json?limit=10',
                timeout=10,
                headers={'User-Agent': HONEST_UA}
            )
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                for post in posts:
                    pd = post.get('data', {})
                    title = pd.get('title', '')
                    # Filter: must mention Ukraine
                    if 'ukrain' in title.lower() or 'київ' in title.lower() or 'kyiv' in title.lower():
                        all_articles['reddit'].append({
                            'title': title,
                            'url': f"https://reddit.com{pd.get('permalink', '')}",
                            'published': datetime.fromtimestamp(pd.get('created_utc', 0), tz=timezone.utc).isoformat() if pd.get('created_utc') else '',
                            'source': f'r/{sub}',
                            'score': pd.get('score', 0),
                        })
        except Exception as e:
            print(f"[Ukraine News] Reddit r/{sub} error: {str(e)[:80]}")
            continue

    print(f"[Ukraine News] Reddit: {len(all_articles['reddit'])} posts")

    # ── Build result ──
    total = sum(len(v) for v in all_articles.values())
    result = {
        'success': True,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'total_articles': total,
        'articles': all_articles,
        'counts': {k: len(v) for k, v in all_articles.items()},
    }

    # Cache to Redis
    if _redis_available():
        _redis_set(NEWS_CACHE_KEY, result)
        print(f"[Ukraine News] Cached {total} articles to Redis")

    return result


def get_ukraine_news(force_refresh=False):
    """Get Ukraine news — Redis-first with 4-hour TTL."""
    if not force_refresh and _redis_available():
        cached = _redis_get(NEWS_CACHE_KEY)
        if cached:
            cached_at = cached.get('fetched_at', '')
            if cached_at:
                try:
                    cached_time = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
                    age_hours = (datetime.now(timezone.utc) - cached_time).total_seconds() / 3600
                    if age_hours < 4:
                        print(f"[Ukraine News] Using cached data ({age_hours:.1f}h old)")
                        cached['from_cache'] = True
                        cached['cache_age_hours'] = round(age_hours, 1)
                        return cached
                except:
                    pass

    return fetch_ukraine_news()


# ========================================
# STATIC HUMANITARIAN DATA
# ========================================

# Sources: IOM DTM Round 22 (Jan 2026), OCHA HNRP 2026, UNICEF HAC 2026,
# UN HRMMU (2025 annual), Ukrinform (daily casualty tracker)
# Last updated: March 10, 2026

STATIC_HUMANITARIAN = {
    'last_manual_update': '2026-03-10',
    'data_period': 'Full-scale invasion since Feb 24, 2022; Year 4 ongoing',
    'note': 'Static figures from IOM DTM R22, OCHA, UNICEF, and UN HRMMU. Updated manually.',

    'displacement': {
        'total_idps': 3712000,
        'returnees': 4405000,
        'idps_in_frontline_raions': 1279000,
        'idps_pct_of_population': 11.9,
        'top_hosting_oblasts': [
            {'oblast': 'Dnipropetrovska', 'idps': 560000, 'pct': 15},
            {'oblast': 'Kharkivska', 'idps': 463000, 'pct': 12},
            {'oblast': 'Kyiv City', 'idps': 341000, 'pct': 9},
            {'oblast': 'Kyivska', 'idps': 311000, 'pct': 8},
        ],
        'top_origin_oblasts': ['Donetska (22%)', 'Kharkivska', 'Zaporizka', 'Luhanska'],
        'protracted_displacement_pct': 71,
        'returned_from_abroad_still_idp': 372000,
        'source': 'IOM DTM General Population Survey Round 22 (Jan 2026)',
        'source_url': 'https://dtm.iom.int/ukraine',
        'as_of': '2025-12-31',
        'note': '71% of IDPs have been displaced for over 2 years. 34% of all IDPs live in frontline raions.'
    },

    'refugees_abroad': {
        'total_refugees_europe': 6300000,
        'eu_temporary_protection': True,
        'tp_expiry': '2027-03-04',          # extended by the EU Council in June 2025
        'tp_extension_uncertain': False,
        'top_hosting_countries': [
            {'country': 'Poland', 'refugees': 960000},
            {'country': 'Germany', 'refugees': 1200000},
            {'country': 'Czech Republic', 'refugees': 380000},
            {'country': 'United Kingdom', 'refugees': 250000},
            {'country': 'Spain', 'refugees': 200000},
        ],
        'return_intention_pct': 60,
        'source': 'UNHCR / IOM DTM',
        'source_url': 'https://data.unhcr.org/en/situations/ukraine',
        'as_of': '2025-12-31',
        'note': '60% of refugees surveyed expressed intention to return when conditions allow.'
    },

    'civilian_casualties': {
        'killed_2025': 2500,
        'injured_2025': 12000,
        'change_vs_2024': '+31%',
        'children_killed_verified_total': 745,
        'children_injured_verified_total': 2375,
        'child_casualties_increase_2025': '+160% in Kyiv vs 2024',
        'deadliest_year_note': '2025 was the deadliest year for civilians since the full-scale invasion began',
        'source': 'UN Human Rights Monitoring Mission in Ukraine (HRMMU)',
        'source_url': 'https://ukraine.un.org/en/268922',
        'as_of': '2025-12-31',
        'note': 'Short-range drones are primary cause of civilian casualties in frontline areas.'
    },

    'russian_losses': {
        'total_casualties_approx': 1275000,
        'daily_average_recent': 950,
        'source': 'Ukrainian Armed Forces General Staff via Ukrinform',
        'source_url': 'https://www.ukrinform.net/rubric-ato',
        'as_of': '2026-03-10',
        'note': 'Ukrainian estimates. Western intelligence estimates may differ. Includes killed and wounded.'
    },

    'energy_infrastructure': {
        'energy_capacity_destroyed_pct': 50,
        'attacks_escalated_since': 'October 2025',
        'systematic_targeting': True,
        'affected_cities': ['Kyiv', 'Kharkiv', 'Odesa', 'Dnipro', 'Zaporizhzhia', 'Kryvyi Rih', 'Chernihiv'],
        'heated_safe_spaces_kyiv': 1200,
        'source': 'OCHA / UNICEF HAC 2026',
        'source_url': 'https://www.unocha.org/ukraine',
        'as_of': '2026-01-13',
        'note': 'Systematic targeting of energy infrastructure violates IHL. Cascading failures in heating, water, electricity.'
    },

    'humanitarian_response': {
        'people_in_need_2026': 10800000,
        'target_2026': 4100000,
        'hnrp_funding_required_billions': 2.3,
        'hnrp_2025_funded_pct': 52,
        'unicef_appeal_millions': 388,
        'unicef_target_people': 4300000,
        'unicef_target_children': 725000,
        'reconstruction_cost_billions': 486,
        'reconstruction_timeline': '10 years',
        'source': 'OCHA HNRP 2026 / UNICEF HAC 2026 / World Bank',
        'source_url': 'https://www.unocha.org/ukraine',
        'as_of': '2026-01-13',
        'note': '$486B reconstruction needed over next decade — 2.8x Ukraine 2023 GDP.'
    },

    'frontline_situation': {
        'most_affected_oblasts': ['Donetska', 'Kharkivska', 'Khersonska', 'Zaporizka', 'Sumska'],
        'occupied_territories': ['Parts of Donetska', 'Parts of Luhanska', 'Parts of Zaporizka', 'Parts of Khersonska', 'Crimea'],
        'primary_casualty_cause': 'Short-range drones (frontline), missiles/drones (rear areas)',
        'access_constraints': 'Humanitarian access severely limited in frontline and occupied areas',
        'kursk_incursion_note': 'Ukrainian forces maintain positions in Russias Kursk Oblast since August 2024',
        'peace_talks_status': ('Trilateral technical talks (Ukraine-US-Russia) expected in November 2026 '
                               '(energy ceasefire, Black Sea grain, prisoner exchanges); nothing signed as of Nov 3 2026. '
                               'The live read is on the Ukraine rhetoric tracker.'),
        'source': 'OCHA / Ukrainian General Staff / Kyiv Independent',
        'as_of': '2026-11-03'
    },

    'source_links': {
        'iom_dtm': {
            'label': 'IOM DTM Ukraine',
            'url': 'https://dtm.iom.int/ukraine',
            'icon': '📊'
        },
        'ocha': {
            'label': 'OCHA Ukraine',
            'url': 'https://www.unocha.org/ukraine',
            'icon': '🏛️'
        },
        'reliefweb': {
            'label': 'ReliefWeb Ukraine',
            'url': 'https://reliefweb.int/country/ukr',
            'icon': '📰'
        },
        'unhcr': {
            'label': 'UNHCR Ukraine Situation',
            'url': 'https://data.unhcr.org/en/situations/ukraine',
            'icon': '🛡️'
        },
        'unicef': {
            'label': 'UNICEF Ukraine',
            'url': 'https://www.unicef.org/ukraine/',
            'icon': '👶'
        },
        'hrmmu': {
            'label': 'UN Human Rights (HRMMU)',
            'url': 'https://ukraine.un.org/en/268922',
            'icon': '⚖️'
        },
        'ukrinform': {
            'label': 'Ukrinform (War)',
            'url': 'https://www.ukrinform.net/rubric-ato',
            'icon': '🇺🇦'
        },
        'kyiv_independent': {
            'label': 'Kyiv Independent',
            'url': 'https://kyivindependent.com/',
            'icon': '📰'
        },
        'who': {
            'label': 'WHO Ukraine',
            'url': 'https://www.who.int/countries/ukr',
            'icon': '🏥'
        }
    }
}


# ========================================
# COMBINED HUMANITARIAN FETCH
# ========================================

def _fetch_all_humanitarian():
    """Fetch all humanitarian data, combine DTM + ReliefWeb + static."""
    print("[Ukraine Humanitarian] Fetching fresh data...")

    dtm_data = fetch_dtm_displacement()
    reliefweb_data = fetch_reliefweb_updates()

    # If DTM returned fresh IDP numbers, overlay on static displacement card
    displacement_data = dict(STATIC_HUMANITARIAN['displacement'])
    if dtm_data and dtm_data.get('country_level'):
        dtm_idps = dtm_data['country_level'].get('total_idps', 0)
        if dtm_idps > 0:
            displacement_data['dtm_api_idps'] = dtm_idps
            displacement_data['dtm_reporting_date'] = dtm_data['country_level'].get('reporting_date', '')
            displacement_data['dtm_round'] = dtm_data['country_level'].get('round_number', '')
            displacement_data['dtm_source'] = 'IOM DTM API v3 (live)'

    result = {
        'success': True,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'from_cache': False,
        'data_period': STATIC_HUMANITARIAN['data_period'],
        'last_manual_update': STATIC_HUMANITARIAN['last_manual_update'],

        'displacement': displacement_data,
        'refugees_abroad': STATIC_HUMANITARIAN['refugees_abroad'],
        'civilian_casualties': STATIC_HUMANITARIAN['civilian_casualties'],
        'russian_losses': STATIC_HUMANITARIAN['russian_losses'],
        'energy_infrastructure': STATIC_HUMANITARIAN['energy_infrastructure'],
        'humanitarian_response': STATIC_HUMANITARIAN['humanitarian_response'],
        'frontline_situation': STATIC_HUMANITARIAN['frontline_situation'],

        'dtm_raw': dtm_data,
        'reliefweb_reports': reliefweb_data.get('reports', []) if reliefweb_data else [],

        'source_links': STATIC_HUMANITARIAN['source_links'],
    }

    # Cache to Redis
    if _redis_available():
        _redis_set(CACHE_KEY, result)
        print("[Ukraine Humanitarian] Cached to Redis")

    return result


def get_humanitarian_data(force_refresh=False):
    """
    Get Ukraine humanitarian data — Redis-first with 6-hour TTL.
    """
    # Check cache (unless force refresh)
    if not force_refresh and _redis_available():
        cached = _redis_get(CACHE_KEY)
        if cached:
            cached_at = cached.get('fetched_at', '')
            if cached_at:
                try:
                    cached_time = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
                    age_hours = (datetime.now(timezone.utc) - cached_time).total_seconds() / 3600
                    if age_hours < 6:
                        print(f"[Ukraine Humanitarian] Using cached data ({age_hours:.1f}h old)")
                        cached['from_cache'] = True
                        cached['cache_age_hours'] = round(age_hours, 1)
                        return cached
                except:
                    pass

    return _fetch_all_humanitarian()


# ========================================
# BACKGROUND REFRESH THREAD
# ========================================

def _background_humanitarian_refresh():
    """Background thread: refresh Ukraine humanitarian + news data every 6 hours."""
    print("[Ukraine Humanitarian] Background refresh thread started (6h cycle)")
    # Initial delay — let the main app start first
    time.sleep(90)
    while True:
        try:
            print("[Ukraine Humanitarian] Running background refresh...")
            _fetch_all_humanitarian()
            fetch_ukraine_news()
            print("[Ukraine Humanitarian] Background refresh complete")
        except Exception as e:
            print(f"[Ukraine Humanitarian] Background refresh error: {str(e)[:200]}")
        time.sleep(REFRESH_INTERVAL_SECONDS)


# ========================================
# REGISTER FLASK ENDPOINTS
# ========================================

def register_ukraine_humanitarian_endpoints(app):
    """Register Ukraine humanitarian endpoints on the Flask app."""

    @app.route('/api/ukraine/humanitarian', methods=['GET'])
    def api_ukraine_humanitarian():
        """
        Ukraine humanitarian crisis data.
        Query params: ?force=true to bypass cache.
        """
        force = request.args.get('force', 'false').lower() == 'true'
        try:
            data = get_humanitarian_data(force_refresh=force)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)[:200],
                'static_fallback': {
                    'displacement': STATIC_HUMANITARIAN['displacement'],
                    'civilian_casualties': STATIC_HUMANITARIAN['civilian_casualties'],
                    'source_links': STATIC_HUMANITARIAN['source_links'],
                }
            }), 200

    @app.route('/api/ukraine/humanitarian/sources', methods=['GET'])
    def api_ukraine_humanitarian_sources():
        """Return all Ukraine humanitarian data source links."""
        return jsonify({
            'success': True,
            'sources': STATIC_HUMANITARIAN['source_links'],
        })

    @app.route('/api/ukraine/news', methods=['GET'])
    def api_ukraine_news():
        """
        Ukraine news feed from Ukrinform, Kyiv Independent, GDELT, Reddit.
        Redis-cached with 4-hour TTL.
        """
        force = request.args.get('force', 'false').lower() == 'true'
        try:
            data = get_ukraine_news(force_refresh=force)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)[:200]
            }), 200

    @app.route('/debug/ukraine-dtm', methods=['GET'])
    def debug_ukraine_dtm():
        """Debug: test DTM API connection for Ukraine."""
        dtm_data = fetch_dtm_displacement()
        return jsonify({
            'dtm_api_key_set': bool(DTM_API_KEY),
            'dtm_base_url': DTM_BASE_URL,
            'result': dtm_data
        })

    # Start background refresh thread
    thread = threading.Thread(target=_background_humanitarian_refresh, daemon=True)
    thread.start()

    print("[Ukraine Humanitarian] Endpoints registered + background refresh started")
