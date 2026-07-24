"""
========================================
BLUESKY — Executive & Government Statement Monitor (v1.0.0)
========================================
Drop-in replacement for the deprecated Nitter module (April 2026).

Bluesky's public AppView API (https://public.api.bsky.app) requires NO auth
and exposes a stable JSON endpoint at:
    /xrpc/app.bsky.feed.getAuthorFeed?actor={handle}&limit={N}

We track two types of accounts:
  1. Native Bluesky accounts — official gov/institutional accounts that
     migrated to Bluesky (StateDept, NATO, etc.)
  2. govmirrors.com mirrors — volunteer-run project that mirrors X posts
     to Bluesky for government accounts that haven't migrated. Lets us
     retain signal from holdouts like Russian MoD, Trump, etc.

Architecture mirrors the old Nitter module:
  - NITTER_ACCOUNTS_EUROPE  →  BLUESKY_ACCOUNTS_EUROPE
  - fetch_nitter_account()  →  fetch_bluesky_account()
  - fetch_nitter_for_target()  →  fetch_bluesky_for_target()

Returns the same article dict shape so downstream scoring code
works unchanged. Only the module name and source field differ.
"""

import requests
import time
from datetime import datetime, timezone, timedelta

# Public AppView — no auth required for read-only
BLUESKY_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"

# Timeout for individual account fetches (seconds)
# Bluesky is fast — public API typically responds in <500ms.
BLUESKY_TIMEOUT = 8

# ────────────────────────────────────────────────────────────────
# ACCOUNT DIRECTORY (mirrors shape of NITTER_ACCOUNTS_EUROPE)
# ────────────────────────────────────────────────────────────────
# (handle, weight, targets[], description)
#
# handle:  Bluesky handle WITHOUT the @ prefix
#          e.g. "state-department.bsky.social"
#          govmirrors: "statedept.govmirrors.com" (mirror of @StateDept)
#
# weight:  1.2 = head of state / direct govt statement
#          1.1 = minister / senior official / MFA
#          1.0 = institutional / military command
#          0.9 = multilateral / monitoring / analytical
#
# targets: list of Europe backend target keys this account is relevant to.
#          Use ['*'] for all targets (worldwide-caution scope).
#
# A note on govmirrors.com:
#   This is a volunteer-run project (https://govmirrors.com) that mirrors
#   X/Twitter government accounts onto Bluesky. It's not official, but it
#   provides a legal, stable path to monitor accounts that haven't left X.
#   Mirrors can go dark — if fetches fail consistently, comment the handle.
# ────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════
# DEAD-HANDLE PRUNE -- July 23 2026
# ═══════════════════════════════════════════════════════════════════════
# 14 handles removed after a live Europe scan returned HTTP 400 for every one
# -- 70% of the queried roster. Each was costing a failed request per theatre,
# and Europe queries 13 theatres, so a single dead handle was burning up to 13
# requests per cycle.
#
# WHAT THIS COST:
#   * natohq, euvsdisinfo, potus, secrubio -- queried for nearly every theatre.
#   * The entire Ukrainian official layer: mfa.gov.ua, defenceu, zelensky-repost.
#   * The entire Russian official layer: mfarussia, modrussia.
#   * Belarus opposition: tsikhanouskaya. Poland: sikorskiradek, defence24.
#   * Greece/Cyprus MFAs -- both theatres lost their only national source.
#
# Removed:
#   cyprusmfa.bsky.social
#   defence24.bsky.social
#   defenceu.govmirrors.com
#   euvsdisinfo.bsky.social
#   euvsdisinfo.bsky.social
#   greekmfa.bsky.social
#   mfa.gov.ua
#   mfarussia.govmirrors.com
#   modrussia.govmirrors.com
#   natohq.bsky.social
#   potus.govmirrors.com
#   secrubio.govmirrors.com
#   sikorskiradek.bsky.social
#   tsikhanouskaya.bsky.social
#   zelensky-repost.bsky.social
#
# STILL ALIVE (do not remove):
#   donaldtusk.bsky.social, notesfrompoland.bsky.social,
#   realdonaldtrump.govmirrors.com, state-department.bsky.social,
#   statedept.govmirrors.com
#
# ALIVE BUT EMPTY: azerbaijanmfa.bsky.social returns 200 with no posts. Kept --
# an empty feed is a real observation; a 400 is not.
#
# NOT replaced with guesses: ~70% of this roster failed, so an invented handle
# is more likely to add another 400 than a source. Verify before adding.
# ═══════════════════════════════════════════════════════════════════════
BLUESKY_ACCOUNTS_EUROPE = [
    # ── Poland (v1.1 — Jul 12 2026) ───────────────────────────
    # The Poland tracker measures the TAPE (Russia never claims), so what we
    # need from Bluesky is ATTRIBUTION and ANALYSIS, not adversary posturing.
    # Polish officials naming Moscow in public is scored as RESILIENCE by the
    # consensus-integrity model -- these handles are how we hear it.
    #
    # ⚠️ HANDLES UNVERIFIED ON FIRST DEPLOY. The fetcher soft-fails per account
    # (a dead handle returns [] and logs, it does not crash the scan), so this
    # is safe to ship. Check the boot log for which resolve; the Cuba
    # dead-handle sweep is the precedent for pruning what doesn't.
    ('notesfrompoland.bsky.social',   1.0, ['poland'],
        'Notes from Poland — English-language Polish analysis'),
    ('donaldtusk.bsky.social',        1.1, ['poland', 'russia', 'ukraine'],
        'Donald Tusk (PM) — names Russia publicly; attribution = resilience'),

    # ── US government — native Bluesky ────────────────────────
    ('state-department.bsky.social',  1.0, ['*'],
        'US State Department (official) — travel advisories, diplomatic signals'),

    # ── US government — govmirrors (X-sourced) ─────────────────
    # Use mirrors ONLY if native Bluesky account does not exist.
    ('statedept.govmirrors.com',      0.9, ['*'],
        'StateDept (X mirror) — redundant with native, kept as backup'),

    # ── NATO / EU institutions — native Bluesky ────────────────

    # ── Ukraine — native Bluesky + verified mirrors ────────────
    # v1.1.0 (May 24 2026): Replaced unverified zelenskyyua.bsky.social
    # with verified zelensky-repost.bsky.social (volunteer-run mirror of
    # Zelensky's X account, maintained by @hbouwmeester.bsky.social).
    # The native account does not exist; original handle was 404ing
    # silently every scan, losing all Zelensky signal.
    # Trade-off: lower post volume vs. X (mirror lag ~minutes), but
    # captures all public Zelensky statements including pre-strike
    # warnings (e.g. May 23 2026 Oreshnik warning).
    # Ukraine MoD via govmirrors (unverified — comment out if 404s)

    # ── European institutions — where available ────────────────
    # Many European institutional accounts are on Mastodon/EU Voice rather
    # than Bluesky. Keep this list minimal and verified; add handles as
    # they're confirmed live. Unknown handles will 404 harmlessly.

    # ── Belarus opposition — native Bluesky (v1.0.0 Apr 29 2026) ──
    # Tikhanovskaya's office is the primary international voice of the
    # Belarusian democratic movement. Handle is unverified — if it 404s,
    # remove with no impact (graceful degradation pattern).

    # ── govmirrors fallbacks for X-only accounts ──────────────
    ('realdonaldtrump.govmirrors.com', 1.2, ['greenland', 'ukraine', 'russia', 'poland', 'hungary', 'belarus', 'greece', 'cyprus', 'azerbaijan'],
        'Trump (X mirror) — Greenland/Ukraine/NATO/Belarus statements'),

    # -- Eastern Mediterranean / Caucasus spoke (Greece, Cyprus, Azerbaijan) --
    # Turkey-spoke + Iran-spoke expansion (Jun 2026). The '*' accounts above
    # (State Dept, NATO) plus the now-extended Rubio/Trump mirrors already give
    # these trackers real coverage. The country-specific MFA handles below are
    # unverified candidates and 404 harmlessly (graceful degradation pattern).
    ('azerbaijanmfa.bsky.social',     0.9, ['azerbaijan'],
        'Azerbaijan MFA (if native, unverified) -- Caucasus, Iran-border, Karabakh'),
]


def fetch_bluesky_account(handle, weight=1.0, limit=20, timeout=BLUESKY_TIMEOUT):
    """
    Fetch recent posts from a single Bluesky account.

    Uses the public AppView API — no authentication required.
    Returns list of article dicts matching the Europe backend schema.

    On 404 (handle doesn't exist) → logs and returns []
    On 429 (rate limit) → logs and returns []
    On network/parse error → logs and returns []
    """
    headers = {
        'User-Agent': 'AsifahAnalytics/1.0 (+https://asifahanalytics.com)',
        'Accept': 'application/json',
    }
    params = {'actor': handle, 'limit': limit}

    try:
        resp = requests.get(BLUESKY_API, headers=headers, params=params, timeout=timeout)

        if resp.status_code == 404:
            print(f'[Bluesky] @{handle}: handle not found (404) — consider removing from list')
            return []
        if resp.status_code == 429:
            print(f'[Bluesky] @{handle}: rate-limited (429) — backing off')
            return []
        if resp.status_code != 200:
            print(f'[Bluesky] @{handle}: HTTP {resp.status_code}')
            return []

        data = resp.json()
        feed = data.get('feed', [])
        articles = []

        for item in feed:
            post = item.get('post', {})
            record = post.get('record', {})
            author = post.get('author', {})

            text = record.get('text', '') or ''
            if not text.strip():
                continue

            # Bluesky timestamps are ISO-8601 UTC
            pub = record.get('createdAt') or post.get('indexedAt') or ''

            # Construct canonical post URL from DID + rkey
            # Format: https://bsky.app/profile/{handle}/post/{rkey}
            post_uri = post.get('uri', '')
            rkey = post_uri.rsplit('/', 1)[-1] if post_uri else ''
            url = f'https://bsky.app/profile/{handle}/post/{rkey}' if rkey else f'https://bsky.app/profile/{handle}'

            # Description = first 400 chars of text (Bluesky is short-form)
            desc = text[:400]

            articles.append({
                'title':       text[:200],
                'description': desc,
                'url':         url,
                'publishedAt': pub,
                'source':      {'name': f'Bluesky @{handle}'},
                'content':     text[:500],
                'language':    'en',
                '_bluesky_weight':  weight,
                '_bluesky_author':  author.get('displayName', handle),
            })

        if articles:
            print(f'[Bluesky] @{handle}: {len(articles)} posts')
        else:
            # v1.2 (May 24 2026): diagnostic — was silent on empty feeds, which
            # made it impossible to distinguish "account returned 200 but no
            # recent posts" from "account 404'd" from "account threw exception
            # silently". Now logs zero-result cases too. If you see lots of
            # "0 posts (200 OK, empty feed)" lines, the handle is probably
            # dead or the account has gone inactive — flag for removal.
            print(f'[Bluesky] @{handle}: 0 posts (200 OK, empty feed)')
        return articles

    except requests.exceptions.Timeout:
        print(f'[Bluesky] @{handle}: timeout after {timeout}s')
        return []
    except Exception as e:
        print(f'[Bluesky] @{handle}: {str(e)[:80]}')
        return []


def fetch_bluesky_for_target(target, days=7, max_posts_per_account=20):
    """
    Fetch Bluesky posts relevant to a specific Europe target.

    Filters by:
      - target key (account must have '*' or target in its targets list)
      - recency (post must be within last {days} days)
      - deduplication (URL-based)

    Returns list of article dicts ready for downstream scoring.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_posts = []
    seen_urls = set()
    accounts_queried = 0
    posts_filtered_by_recency = 0   # v1.2 diagnostic
    posts_filtered_by_dedup    = 0   # v1.2 diagnostic
    posts_returned_raw         = 0   # v1.2 diagnostic

    for handle, weight, targets, desc in BLUESKY_ACCOUNTS_EUROPE:
        # Skip accounts not relevant to this target
        if '*' not in targets and target not in targets:
            continue

        accounts_queried += 1
        posts = fetch_bluesky_account(handle, weight=weight, limit=max_posts_per_account)
        posts_returned_raw += len(posts)

        for p in posts:
            if p['url'] in seen_urls:
                posts_filtered_by_dedup += 1
                continue

            # Recency filter
            try:
                pub_str = p['publishedAt'].replace('Z', '+00:00')
                pub = datetime.fromisoformat(pub_str)
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub < cutoff:
                    posts_filtered_by_recency += 1
                    continue
            except Exception:
                # If date parsing fails, keep the post (better than losing signal)
                pass

            seen_urls.add(p['url'])
            all_posts.append(p)

        # Light politeness delay — Bluesky public API is fast but we
        # don't want to look abusive
        time.sleep(0.2)

    # v1.2 (May 24 2026): expanded summary log so we can see WHERE posts
    # are being filtered out — by recency? dedup? Or did the API return
    # zero raw posts to begin with? Each scenario points to a different fix.
    print(
        f'[Bluesky] {target}: {len(all_posts)} posts kept '
        f'(raw={posts_returned_raw}, '
        f'cut_recency={posts_filtered_by_recency}, '
        f'cut_dedup={posts_filtered_by_dedup}) '
        f'from {accounts_queried} accounts queried'
    )
    return all_posts

# ────────────────────────────────────────────────────────────────
# NAMED WRAPPER FUNCTIONS (called by rhetoric trackers)
# ────────────────────────────────────────────────────────────────
# Each rhetoric tracker imports a named function for its target.
# These are thin wrappers around fetch_bluesky_for_target() to
# match the import contract used by tracker files.

def fetch_belarus_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to Belarus tracker."""
    return fetch_bluesky_for_target('belarus',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_ukraine_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to Ukraine tracker."""
    return fetch_bluesky_for_target('ukraine',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_hungary_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to Hungary tracker (v1.0.0 May 17 2026).

    Currently surfaces Hungary mentions via existing govmirror accounts
    (potus.govmirrors.com, realdonaldtrump.govmirrors.com, secrubio,
    euvsdisinfo) that already have 'hungary' in their targets list.
    Hungary-specific native accounts (Tisza party, opposition voices,
    Hungarian MFA) can be added to BLUESKY_ACCOUNTS_EUROPE in C2.5
    when those accounts are verified live on Bluesky.
    """
    return fetch_bluesky_for_target('hungary',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_poland_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to the Poland consensus tracker (v1.0.0 Jul 12 2026).

    Surfaces Polish attribution voices (Tusk, Sikorski), Polish analytical media
    (Notes from Poland, Defence24), and EU disinformation tracking -- plus the
    existing govmirror accounts that already carry 'poland' in their targets.

    The tracker calls fetch_bluesky_for_target('poland') directly, so this
    wrapper exists for symmetry with the other theatres.
    """
    return fetch_bluesky_for_target('poland',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_russia_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to Russia tracker (for future use)."""
    return fetch_bluesky_for_target('russia',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_greenland_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to Greenland tracker (for future use)."""
    return fetch_bluesky_for_target('greenland',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_greece_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to the Greece tracker (Aegean/Greece-Turkey,
    Eastern Med). Surfaced via '*' accounts (State Dept, NATO) + Rubio/Trump
    mirrors; native greekmfa handle activates if/when verified live."""
    return fetch_bluesky_for_target('greece',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_cyprus_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to the Cyprus tracker (SBA/Akrotiri, buffer
    zone, Eastern-Med hydrocarbons, Greece deployments)."""
    return fetch_bluesky_for_target('cyprus',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)


def fetch_azerbaijan_bluesky_signals(days=7, max_posts_per_account=20):
    """Bluesky posts relevant to the Azerbaijan tracker (Iran-border/
    Nakhchivan, Karabakh/Zangezur, Israel ties, BTC pipeline)."""
    return fetch_bluesky_for_target('azerbaijan',
                                    days=days,
                                    max_posts_per_account=max_posts_per_account)
