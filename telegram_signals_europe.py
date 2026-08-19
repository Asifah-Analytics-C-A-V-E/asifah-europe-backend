"""
Telegram Signal Source for Europe Conflict Dashboard
v2 - June 2026

Bridges Telethon (async) with Flask (sync) to pull messages
from monitored Telegram channels and feed them into the
European conflict probability scanner.

Channels monitored:
- Ukraine war channels (Rybar, DeepState, Ukraine NOW)
- NATO/European defense channels
- Azeri/Armenian conflict channels
- OSINT aggregators covering European theatre

Usage:
    from telegram_signals_europe import fetch_europe_telegram_signals
    messages = fetch_europe_telegram_signals(hours_back=24)
    # Returns list of dicts with 'title', 'url', 'published', 'source' keys
"""

import os
import asyncio
import base64
from datetime import datetime, timezone, timedelta

# Telethon import with graceful fallback
try:
    from telethon import TelegramClient
    from telethon.tl.functions.messages import GetHistoryRequest
    from telethon.errors import FloodWaitError, UsernameInvalidError, UsernameNotOccupiedError
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    print("[Telegram Europe] ⚠️ telethon not installed — Telegram signals disabled")


# ========================================
# CONFIGURATION
# ========================================

TELEGRAM_API_ID = os.environ.get('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.environ.get('TELEGRAM_API_HASH')
TELEGRAM_PHONE = os.environ.get('TELEGRAM_PHONE')
SESSION_NAME = 'asifah_session'

# Core European conflict channels
# v1.2.0: Audited April 2026 — removed all dead/invalid channels from logs
# ============================================================
# CHANNEL METADATA  (tier + language)   -- v2.0.0, Aug 2026
# ============================================================
# Mirrors the ME backend's telegram_signals.py v2.0.0 contract so both
# backends emit identically-shaped provenance to the GPI.
#
# tier: official | wire | mainstream | aggregator | aligned | state | unverified
# lang: en, ru, uk, he, tr, el, hu, pl, lt, lv, az, ro, no, ar
#
# WHY THIS MATTERS HERE SPECIFICALLY: RUSSIA_CHANNELS carries Russian MoD
# official (mod_russia_en), Russian-aligned milbloggers (rybar, intelslava)
# AND outlets aligned against Moscow (meduzaio, currenttime, nexta_tv).
# Without a tier the GPI cannot distinguish "the Russian MoD announced it"
# from "Meduza reported it" -- and would read a single claim echoed across
# both blocs as corroboration rather than as an information contest.
#
# Alignment is DISCLOSED, never excluded.

CHANNEL_META = {
    # ---- Official government / military ----
    'mod_russia_en':   {'tier': 'official', 'lang': ['en'],       'note': 'Russian MoD English'},
    'V_Zelenskiy_official': {'tier': 'official', 'lang': ['uk'],  'note': 'Zelensky official'},
    'mfaukraine':      {'tier': 'official', 'lang': ['uk','en'],  'note': 'Ukraine MFA'},
    'Pravda_Gerashchenko': {'tier': 'aligned', 'lang': ['uk','ru'], 'note': 'Anton Gerashchenko -- former MoIA advisor; Ukrainian official-adjacent, not neutral'},
    'ukrinform':       {'tier': 'official', 'lang': ['uk'],       'note': 'Ukrinform state agency'},
    'NorwayMFA':       {'tier': 'official', 'lang': ['no','en'],  'note': 'Norwegian MFA'},
    'CENTCOM':         {'tier': 'official', 'lang': ['en'],       'note': 'US CENTCOM'},
    'StateDept':       {'tier': 'official', 'lang': ['en'],       'note': 'US State Department'},
    'pul_1':           {'tier': 'official', 'lang': ['ru'],       'note': 'Pul Pervogo -- Lukashenko press pool'},
    'BELTA_news':      {'tier': 'state',    'lang': ['ru'],       'note': 'BelTA -- Belarusian state agency'},
    'EUvsDisinfo':     {'tier': 'official', 'lang': ['en'],       'note': 'EEAS disinformation task force'},

    # ---- Wire / mainstream ----
    'France24_en':     {'tier': 'wire',       'lang': ['en'],      'note': 'France 24 English'},
    'bbcrussian':      {'tier': 'mainstream', 'lang': ['ru'],      'note': 'BBC Russian service'},
    'KyivIndependent_official': {'tier': 'mainstream', 'lang': ['en'], 'note': 'Kyiv Independent'},
    'KyivPost':        {'tier': 'mainstream', 'lang': ['en'],      'note': 'Kyiv Post'},
    'ukrpravda_news':  {'tier': 'mainstream', 'lang': ['uk'],      'note': 'Ukrainska Pravda'},
    'eurointegration': {'tier': 'mainstream', 'lang': ['uk'],      'note': 'European Pravda'},
    'lrtlt':           {'tier': 'mainstream', 'lang': ['lt'],      'note': 'LRT Lithuania'},
    'latvianpublichroadcasting': {'tier': 'mainstream', 'lang': ['lv'], 'note': 'LSM Latvia'},
    'notesfrompoland': {'tier': 'mainstream', 'lang': ['en'],      'note': 'Notes from Poland'},
    'tvpworld':        {'tier': 'state',      'lang': ['en'],      'note': 'TVP World -- Polish state broadcaster'},
    'telex_hu':        {'tier': 'mainstream', 'lang': ['hu'],      'note': 'Telex -- independent Hungarian'},
    'CyprusMail':      {'tier': 'mainstream', 'lang': ['en'],      'note': 'Cyprus Mail'},
    'incyprus':        {'tier': 'mainstream', 'lang': ['en'],      'note': 'In-Cyprus'},
    'GreekCityTimes':  {'tier': 'mainstream', 'lang': ['en'],      'note': 'Greek City Times'},
    'arctictoday':     {'tier': 'mainstream', 'lang': ['en'],      'note': 'Arctic Today'},
    'ArmenianUnified': {'tier': 'mainstream', 'lang': ['en'],      'note': 'Armenian news aggregator'},

    # ---- Aggregators / OSINT ----
    'OSINTdefender':   {'tier': 'aggregator', 'lang': ['en'],      'note': 'RUMINT anchor'},
    'WarMonitors':     {'tier': 'aggregator', 'lang': ['en'],      'note': 'RUMINT anchor'},
    'ClashReport':     {'tier': 'aggregator', 'lang': ['en','tr'], 'note': 'RUMINT anchor -- Turkish-linked'},
    'C_Military1':     {'tier': 'aggregator', 'lang': ['en'],      'note': 'Conflict/military OSINT'},
    'DeepStateUA':     {'tier': 'aggregator', 'lang': ['uk'],      'note': 'DeepState map -- Ukrainian front'},
    'front_ukrainian': {'tier': 'aggregator', 'lang': ['uk'],      'note': 'Ukrainian front OSINT'},
    'wartranslated':   {'tier': 'aggregator', 'lang': ['en','ru'], 'note': 'Translates Russian-side primary comms'},
    'militarylandnet': {'tier': 'aggregator', 'lang': ['en'],      'note': 'Order of battle tracking'},
    'UkraineWeaponsTracker': {'tier': 'aggregator', 'lang': ['en'],'note': 'Weapons/loss tracking'},
    'GeoConfirmed':    {'tier': 'aggregator', 'lang': ['en'],      'note': 'Geolocation verification'},
    'UkraineNow':      {'tier': 'aggregator', 'lang': ['en','uk'], 'note': 'Ukraine war updates'},
    'HMIntelligence':  {'tier': 'aggregator', 'lang': ['en'],      'note': 'Ukraine/Russia OSINT'},
    'RageIntel':       {'tier': 'aggregator', 'lang': ['en'],      'note': 'Combat OSINT -- verify handle'},
    'disclosetv':      {'tier': 'aggregator', 'lang': ['en'],      'note': 'Breaking conflict news -- accuracy varies'},
    'nuclearsecrecy':  {'tier': 'aggregator', 'lang': ['en'],      'note': 'Arms control / nuclear'},
    'abualiexpress':   {'tier': 'aggregator', 'lang': ['he','ar'], 'note': 'Abu Ali Express -- Hebrew aggregator translating Arabic media; Israeli vantage on Iran-Russia'},

    # ---- Openly aligned ----
    'rybar':           {'tier': 'aligned', 'lang': ['ru'],      'note': 'Rybar -- Russian milblogger, MoD-adjacent'},
    'intelslava':      {'tier': 'aligned', 'lang': ['ru','en'], 'note': 'Intel Slava Z -- Russian-aligned'},
    'MiddleEastSpectator': {'tier': 'aligned', 'lang': ['en'],  'note': 'pro-Russia/Iran framing; ME-Russia axis'},
    'meduzaio':        {'tier': 'aligned', 'lang': ['ru'],      'note': 'Meduza -- independent, aligned AGAINST Moscow (exile media)'},
    'currenttime':     {'tier': 'aligned', 'lang': ['ru'],      'note': 'Current Time -- RFE/RL, US-funded'},
    'nexta_tv':        {'tier': 'aligned', 'lang': ['ru'],      'note': 'NEXTA -- Belarusian opposition'},
    'belamova':        {'tier': 'aligned', 'lang': ['ru'],      'note': 'Belarus opposition tracker'},
    'sviatlanaTSlive': {'tier': 'aligned', 'lang': ['ru','en'], 'note': 'Tikhanovskaya -- opposition leader in exile'},
    'kann_news':       {'tier': 'mainstream', 'lang': ['he'],   'note': 'Kan -- Israeli public broadcaster, Hebrew'},

    # ---- State media of a party ----
    'trtworld':        {'tier': 'state', 'lang': ['en'],      'note': 'TRT -- Turkish state'},
    'dailysabah':      {'tier': 'state', 'lang': ['en'],      'note': 'Daily Sabah -- pro-government Turkish'},
    'apa_az':          {'tier': 'state', 'lang': ['az','en'], 'note': 'APA -- Azerbaijani'},
    'caliberaz':       {'tier': 'state', 'lang': ['az','en'], 'note': 'Caliber.az -- Azerbaijani, MoD-adjacent'},
    'trendnewsagency': {'tier': 'state', 'lang': ['az','en'], 'note': 'Trend -- Azerbaijani'},

    # ---- Unverified ----
    'doureios':        {'tier': 'unverified', 'lang': ['el'], 'note': 'Greek defence blog -- not assessed'},
    'pentapostagma':   {'tier': 'unverified', 'lang': ['el'], 'note': 'Greek outlet -- not assessed'},
}

DEFAULT_META = {'tier': 'unverified', 'lang': ['en'], 'note': 'No metadata entry'}


def get_channel_meta(handle):
    """Tier/language for a handle. Case-insensitive -- Telegram handles are."""
    if handle in CHANNEL_META:
        return CHANNEL_META[handle]
    low = handle.lower()
    for k, v in CHANNEL_META.items():
        if k.lower() == low:
            return v
    return DEFAULT_META


def channels_needing_verification():
    """Handles that must NOT count as corroboration until reviewed."""
    return sorted(k for k, v in CHANNEL_META.items() if v['tier'] == 'unverified')


def get_language_coverage():
    langs, tiers = {}, {}
    for v in CHANNEL_META.values():
        tiers[v['tier']] = tiers.get(v['tier'], 0) + 1
        for lg in v['lang']:
            langs[lg] = langs.get(lg, 0) + 1
    return {'by_language': dict(sorted(langs.items(), key=lambda x: -x[1])),
            'by_tier': dict(sorted(tiers.items(), key=lambda x: -x[1])),
            'total_channels': len(CHANNEL_META)}


# Per-channel message cap now scales with the window. A flat 50 silently
# truncated fetch_russia_telegram_signals(hours_back=168) -- a SEVEN-DAY pull
# capped at 50 messages per channel.
MSGS_PER_HOUR = 4
MSG_LIMIT_MIN = 50
MSG_LIMIT_MAX = 200


def _msg_limit(hours_back):
    return max(MSG_LIMIT_MIN, min(MSG_LIMIT_MAX, int(hours_back) * MSGS_PER_HOUR))


EUROPE_CHANNELS = [
    # ── Ukraine war — CONFIRMED WORKING ──────────────────────────
    'DeepStateUA',         # ✅ DeepState Map — Ukrainian front updates (16 msg)
    'mod_russia_en',       # ✅ Russian MoD English (49 msg)
    'C_Military1',         # ✅ Conflict/military OSINT (37 msg)
    'ClashReport',         # ✅ Clash Report — conflict monitoring (47 msg)
    'WarMonitors',         # ✅ War Monitor — multilingual (46 msg)
    'OSINTdefender',       # ✅ OSINT Defender — English, high signal (50 msg)
    'France24_en',         # ✅ France 24 English (50 msg)

    # ── Ukraine war — NEW ADDITIONS (verified active) ─────────────
    'intelslava',          # Intel Slava Z — very active OSINT aggregator
    'wartranslated',       # War Translated — Russian/Ukrainian mil comms EN
    'UkraineNow',          # Ukraine Now — war updates
    'front_ukrainian',     # Ukrainian front OSINT
    'rybar',               # Rybar — primary Russian mil blogger OSINT
    'MiddleEastSpectator', # Cross-theater (ME-Russia links)
    'disclosetv',          # Disclose.tv — breaking conflict news

    # ── Russia domestic signals ───────────────────────────────────
    'currenttime',         # Current Time — RFE/RL Russian service
    'meduzaio',            # Meduza — independent Russian journalism
    'nexta_tv',            # NEXTA — Belarus/Russia opposition

    # ── European / NATO ───────────────────────────────────────────
    'eurointegration',     # European integration news (Ukraine-EU)
    'bbcrussian',          # BBC Russian service
    'HMIntelligence',      # HM Intelligence -- Ukraine/Russia OSINT + Albania coverage
]

# Extended channels — Baltic, Arctic, Poland (v1.2.0 audit)
# Only channels with verified Telegram presence included
EXTENDED_EUROPE_CHANNELS = [
    # ── Caucasus (verified working) ───────────────────────────────
    'ArmenianUnified',     # ✅ Armenian news aggregator (0 msg but exists)

    # ── Arctic / Nordic (verified) ────────────────────────────────
    'arctictoday',         # ✅ Arctic Today (0 msg but exists — slow channel)
    'NorwayMFA',           # ✅ Norwegian MFA (0 msg but exists)

    # ── Additional OSINT (verified active) ────────────────────────
    'militarylandnet',     # Military Land — order of battle tracking
    'UkraineWeaponsTracker', # Ukraine weapons tracking
    'GeoConfirmed',        # GeoConfirmed — geolocation OSINT
    'KyivPost',            # Kyiv Post — English Ukraine news

    # ── Baltic / Eastern Europe ───────────────────────────────────
    'lrtlt',               # LRT Lithuania — Baltic signals
    'latvianpublichroadcasting', # LSM Latvia

    # ── Nuclear / strategic watch ─────────────────────────────────
    'nuclearsecrecy',      # Nuclear Secrecy — arms control/nuclear signals
]

# ── Greenland-specific channel list (v1.1.0) ──
# Used by rhetoric_tracker_greenland.py
# Focuses on U.S. pressure, Danish/NATO response,
# Inuit voice, Russian Arctic opportunism, Nordic OSINT
GREENLAND_CHANNELS = [
    # ── U.S. pressure signals ─────────────────────────────────────
    'CENTCOM',             # ✅ CENTCOM official (confirmed handle)
    'StateDept',           # ✅ State Dept (confirmed working in ME backend)
    # ── Russia Arctic opportunism ─────────────────────────────────
    'mod_russia_en',       # ✅ Russian MoD English (49 msg confirmed)
    'intelslava',          # ✅ Intel Slava — Russia Arctic signals
    # ── Arctic / Nordic OSINT ─────────────────────────────────────
    'arctictoday',         # ✅ Arctic Today (exists, slow channel)
    'NorwayMFA',           # ✅ Norwegian MFA (exists)
    'OSINTdefender',       # ✅ OSINT Defender — high signal (50 msg confirmed)
    'ClashReport',         # ✅ Clash Report — catches Arctic incidents
    # ── General high-signal (catches Greenland mentions) ──────────
    'WarMonitors',         # ✅ War Monitor — multilingual
    'France24_en',         # ✅ France 24 — covers Arctic/NATO stories
]

# ── Hungary-specific channel list (v1.0.0 — April 2026) ──
# Context: Peter Magyar / Tisza party won landslide election April 12, 2026
# ending 16 years of Orban/Fidesz rule with a constitutional supermajority
# (138/199 seats, 53.6% vs 37.8%). Record 77% turnout.
#
# Tracking signals:
#   - Tisza transition: EU re-engagement, Ukraine unblocking, rule of law reform
#   - Fidesz opposition: Orban pushback, far-right reaction, Russian interference
#   - EU/Brussels response: frozen funds release, Hungary re-integration
#   - Democratic backsliding reversal: judiciary, media freedom, corruption
#   - Regional spillover: Slovakia tensions, ethnic Hungarian minority issues
#
# Note: Magyar's primary comms are Facebook/social media, not Telegram.
# No official Tisza Telegram exists. Signals captured via European OSINT
# and Hungarian independent media channels.
HUNGARY_CHANNELS = [
    # ── Verified working, Hungary-relevant, non-war-heavy ──
    # v1.1.0 cleanup (April 2026): removed 6 dead channels
    # (eurointegration, euractiv, 444hu, hvg_hu, politico_eu, meduzaio)
    # and 4 war-heavy channels (intelslava, mod_russia_en,
    # OSINTdefender, WarMonitors) that were inflating Hungary score
    # with Ukraine-war content leakage (92% false positive).

    # ── EU-level political monitoring ──
    'EUvsDisinfo',          # EU vs Disinfo — Russian interference signals
    'France24_en',          # France 24 — EU institutional coverage

    # ── Eastern European democratic movements ──
    'nexta_tv',             # NEXTA — Eastern European democratic movements

    # ── Independent Hungarian media ──
    'telex_hu',             # Telex — leading independent Hungarian media

    # ── Russian-language European coverage ──
    'bbcrussian',           # BBC Russian — Eastern European transitions
]

# ── Poland channel list (v1.3.0 — Jul 12 2026) ──
# Used by rhetoric_tracker_poland.py (mode='tape' target).
#
# CURATION LOGIC — and it is deliberately narrow:
# Poland's tracker measures the TAPE, not an actor. Russia never claims its
# hybrid operations in Poland, so there is no adversary channel to monitor for
# a confession. What we need instead is: (a) attack reporting, (b) POLISH
# ATTRIBUTION (the state naming Moscow — which the model scores as RESILIENCE),
# and (c) amplification/disinformation detection.
#
# HARD LESSON APPLIED (from the Hungary v1.1.0 cleanup): war-heavy channels like
# intelslava / OSINTdefender / WarMonitors inflated Hungary's score by 92% with
# Ukraine-war content leakage. Poland is adjacent to the same war, so the same
# trap is wide open here. This list therefore EXCLUDES generic war-OSINT feeds
# and stays on Poland-relevant, attribution-capable sources. Do not "helpfully"
# add sentdefender later -- it will pollute the tempo baseline, and a polluted
# baseline is worse than no baseline.
POLAND_CHANNELS = [
    # ── Polish / Central European media ──────────────────────────
    'notesfrompoland',      # Notes from Poland — English-language, analytical
    'tvpworld',             # TVP World — Polish state broadcaster, English

    # ── Disinformation + influence-operation detection (the cognitive domain) ──
    'EUvsDisinfo',          # EU vs Disinfo — Doppelgänger/Matryoshka tracking
    'nexta_tv',             # NEXTA — Belarus/Poland border, Lukashenko lever

    # ── Regional / institutional ─────────────────────────────────
    'France24_en',          # France 24 — EU institutional coverage
    'bbcrussian',           # BBC Russian — the other side of the mirror
]

# ── Russia-specific channel list (v1.2.0) ──
# Used by rhetoric_tracker_russia.py
# Focuses on Russian military ops, Ukraine front,
# nuclear/strategic signals, Baltic/Arctic, domestic Russia
RUSSIA_CHANNELS = [
    # ── Russian military / MoD ────────────────────────────────────
    'mod_russia_en',       # ✅ Russian MoD English (49 msg confirmed)
    'rybar',               # ✅ Rybar — primary Russian mil blogger
    'intelslava',          # ✅ Intel Slava Z — very active OSINT
    # ── Ukraine front ────────────────────────────────────────────
    'DeepStateUA',         # ✅ DeepState Map — front updates (16 msg)
    'wartranslated',       # War Translated — Russian/Ukrainian mil comms EN
    'front_ukrainian',     # Ukrainian front OSINT
    'OSINTdefender',       # ✅ OSINT Defender (50 msg confirmed)
    'ClashReport',         # ✅ Clash Report (47 msg confirmed)
    'WarMonitors',         # ✅ War Monitor (46 msg confirmed)
    'C_Military1',         # ✅ Conflict OSINT (37 msg confirmed)
    # ── Russia domestic / opposition ──────────────────────────────
    'meduzaio',            # Meduza — independent Russian journalism
    'nexta_tv',            # NEXTA — Belarus/Russia opposition
    'currenttime',         # Current Time — RFE/RL Russian service
    # ── Nuclear / strategic ───────────────────────────────────────
    'nuclearsecrecy',      # Nuclear Secrecy — arms control signals
    # ── Arctic / NATO flank ───────────────────────────────────────
    'arctictoday',         # Arctic Today — Northern Fleet/Arctic signals
    'NorwayMFA',           # Norwegian MFA — Arctic/NATO flank
    # ── Cross-theater (ME-Russia links) ───────────────────────────
    'MiddleEastSpectator', # ME-Russia axis signals
    'HMIntelligence',      # HM Intelligence -- Russia/Ukraine OSINT
    # ── Israeli vantage on the ME-Russia axis (v2.0.0, NARROW scope) ──
    # Added ONLY for the Iran-Russia military track, Russia-Israel Syria
    # deconfliction, and aliyah-as-domestic-pressure. Hebrew is NOT a primary
    # language of Russia/Ukraine reporting and these are not general war
    # sources -- the paired Hebrew keywords in rhetoric_tracker_russia.py are
    # deliberately scoped to that axis so this does not bleed into the
    # Ukraine-war score (the Hungary/Belarus lesson).
    'abualiexpress',       # Hebrew aggregator -- already used in TURKEY/GREECE lists
    'kann_news',           # Kan -- Israeli public broadcaster, Hebrew
]

# ── Belarus-specific channel list (v1.0.0 — Apr 29 2026) ──
# Used by Belarus stability scoring in app.py.
# Focused curation to avoid Ukraine-war content bleeding into Belarus
# score (same lesson learned with Hungary).
#
# Key signals to capture:
#   - Lukashenko / Khrenin defense statements (BelTA, pul_1, Belarus MFA)
#   - Tikhanovskaya opposition in exile (NEXTA primary)
#   - Russian deployment / Wagner remnants in Belarus
#   - NATO border tensions (Suwałki Gap, Poland/Lithuania border)
#   - Iran-Belarus cooperation (Apr 27 2026 IR-RU-BY trilateral)
#   - Migrant weaponization at Polish/Lithuanian border
BELARUS_CHANNELS = [
    # ── Belarusian opposition (exile media) ───────────────────────
    'nexta_tv',                # ✅ NEXTA — primary Belarusian opposition (live since 2020)
    'belamova',                # Belarus opposition tracker
    'sviatlanaTSlive',         # Tikhanovskaya official — opposition leader in exile
    # ── Belarusian state / pro-regime (for what regime is saying) ──
    'pul_1',                   # "Пул Первого" — Lukashenko's office press pool
    'BELTA_news',              # BelTA — Belarus state news agency
    # ── Russian-language Eastern Europe coverage ──────────────────
    'meduzaio',                # Meduza — independent Russian journalism
    'currenttime',             # Current Time — RFE/RL Russian service
    'bbcrussian',              # BBC Russian — Eastern European transitions
    # ── EU institutional monitoring ───────────────────────────────
    'EUvsDisinfo',             # EU vs Disinfo — Russian/Belarusian interference
    # ── Cross-theater (Belarus-Iran-Russia axis) ──────────────────
    'MiddleEastSpectator',     # ME-Russia-Iran axis signals (post-Apr 27 trilateral)
    # ── NATO frontline coverage ───────────────────────────────────
    'NorwayMFA',               # Norwegian MFA — broader NATO flank perspective
    # ── OSINT (general — kept light to avoid Ukraine-war bleed) ───
    'OSINTdefender',           # OSINT Defender — broad coverage incl. Belarus deployments
]

def fetch_belarus_telegram_signals(hours_back=120):
    """
    Fetch Telegram signals for Belarus stability tracker.
    Uses 120h (5 day) window — Belarus signal moves on multi-day rhythm
    (Lukashenko statements, defense ministry comms, opposition reports).

    Key signals to watch:
      - Khrenin (Defense Minister) statements re: Iran/Russia cooperation
      - Lukashenko health / succession rumors
      - Russian troop movements / Wagner deployments in Belarus
      - Tikhanovskaya statements on political prisoners
      - Suwałki Gap / NATO border activity
      - Migrant weaponization at Polish/Lithuanian border
      - Iran-Belarus follow-up after April 27 SCO trilateral

    Context (April 27, 2026):
      Belarus Defense Minister Khrenin met with Iran Deputy DM Talaei-Nik;
      Belarus' Defence Ministry stated 'mutual interest of Minsk and Tehran
      for further deepening of joint interaction'.
    """
    if not _telegram_available():
        print("[Telegram Belarus] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(BELARUS_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(BELARUS_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Belarus] ❌ fetch error: {str(e)[:200]}")
        return []

# ────────────────────────────────────────────────────────────
# MOLDOVA TELEGRAM (v1.0.0 — Jul 16 2026)
# ────────────────────────────────────────────────────────────
# The Moldovan information space is Telegram-heavy and RU-first in exactly
# the places that matter (Transnistria, Gagauzia, the Shor networks operate
# ON Telegram). Curated list, VERIFY-IN-LOGS: any channel logging zero
# messages across two scans needs its handle corrected.
MOLDOVA_CHANNELS = [
    ('newsmakerlive',  1.0, 'NewsMaker — RU-language Chisinau outlet; fastest Moldova wire'),
    ('nokta_md',       0.9, 'Nokta — Gagauzia-focused independent outlet (Comrat)'),
    ('tv8md',          0.9, 'TV8 — independent Moldovan broadcaster'),
    ('zdgmd',          0.9, 'Ziarul de Garda — investigative (Shor networks, vote-buying)'),
]


def fetch_moldova_telegram_signals(hours_back=168):
    """
    Moldova-specific Telegram scan (dedicated list — the general Europe
    channels are war-heavy and would drown the interference signal, the same
    isolation rationale as Hungary).

    Watching for:
      - Election interference / vote-buying network chatter (Shor ecosystem)
      - Transnistria escalation language (OGRF, Cobasna, Security Zone)
      - Gagauzia separatist pressure (Comrat, Gutul)
      - Energy blackmail cycles (Moldovagaz, Cuciurgan/MGRES)
    """
    if not _telegram_available():
        print("[Telegram Moldova] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(MOLDOVA_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(MOLDOVA_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Moldova] ❌ fetch error: {str(e)[:200]}")
        return []

# ────────────────────────────────────────────────────────────
# UKRAINE TELEGRAM (v1.0.0 — May 2026)
# ────────────────────────────────────────────────────────────
UKRAINE_CHANNELS = [
    # ── Ukrainian government / official ─────────────────────────
    'V_Zelenskiy_official',    # Zelensky's official Telegram
    'Pravda_Gerashchenko',     # Anton Gerashchenko (former MoIA advisor)
    'mfaukraine',              # Ukraine MFA
    # ── Ukrainian press (English/Ukrainian) ─────────────────────
    'KyivIndependent_official',  # Kyiv Independent
    'ukrpravda_news',          # Ukrainska Pravda
    'ukrinform',               # Ukrinform state news
    # ── Defense / OSINT (Ukraine-focused) ───────────────────────
    'OSINTdefender',           # OSINT Defender — broad combat OSINT
    'wartranslated',           # WarTranslated — Russian-side primary source translations
    'ClashReport',             # ClashReport — broad OSINT
    # ── Russian-language coverage ───────────────────────────────
    'meduzaio',                # Meduza — independent Russian journalism
    'currenttime',             # Current Time — RFE/RL Russian
    # ── EU institutional monitoring ─────────────────────────────
    'EUvsDisinfo',             # Russian disinformation tracking
    # ── Cross-theater (Iran-Russia-Ukraine axis) ────────────────
    'MiddleEastSpectator',     # ME-Russia-Iran axis (Iranian drone supply context)
    'HMIntelligence',      # HM Intelligence -- heavy Ukraine war signaling
    'RageIntel',           # RageIntel -- Ukraine combat OSINT (added Jun 2026; verify exact handle)
    # ── Israeli vantage (v2.0.0, NARROW scope) ──
    # Iranian drone/missile supply to Russia is the specific signal; Israeli
    # channels frequently report it first. Scoped keywords only.
    'abualiexpress',       # Hebrew aggregator -- Iran-Russia materiel track
]


def fetch_ukraine_telegram_signals(hours_back=72):
    """
    Fetch Telegram signals for Ukraine rhetoric tracker.
    Uses 72h (3 day) window — Ukraine signal moves on faster rhythm than
    Belarus (active war, daily strikes/aid announcements/diplomatic shifts).

    Key signals to watch:
      - Zelensky statements re: ceasefire / aid / defense industrial
      - Ukrainian armed forces operational reports
      - US aid pipeline status (Trump statements, Witkoff envoy activity)
      - Drone advisor exports (GCC partnerships, training operations)
      - Frontline pressure (advances, retreats, salient defense)
      - Black Sea grain corridor disruption
      - Energy infrastructure strikes
      - Russian Shahed/Kalibr/Kinzhal salvos
    """
    if not _telegram_available():
        print("[Telegram Ukraine] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(UKRAINE_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(UKRAINE_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Ukraine] ❌ fetch error: {str(e)[:200]}")
        return []

TURKEY_CHANNELS = [
    'ClashReport',          # Turkish-origin OSINT -- the anchor source
    'MiddleEastSpectator',  # Cross-theater ME-Russia links
    'OSINTdefender',        # High-signal English OSINT
    'intelslava',           # Aggregator -- catches Turkey-Russia threads
    'disclosetv',           # Breaking conflict news
    # ── Turkish-language / state-adjacent (regime narrative voice) ──
    'trtworld',             # ⚠️ verify handle -- TRT World (state media)
    'dailysabah',           # ⚠️ verify handle -- Daily Sabah (pro-gov daily)
    # ── Hebrew-language / Israeli OSINT (Turkey-as-threat framing) ──
    'abualiexpress',        # ⚠️ verify handle -- Abu Ali Express (HE+EN, heavy regional)
]

def fetch_turkey_telegram_signals(hours_back=96):
    """
    Fetch Telegram signals for the Turkey swing-state tracker.
    96h window -- Turkey rhetoric moves slower than Ukraine (no active
    war) but faster than Belarus (live Levant friction).

    Key signals to watch:
      - Buffer-zone / safe-zone framing (signature pre-operation tell)
      - Turkey-Israel friction in Syria (deconfliction strain)
      - Lebanon-vector chatter (ports, trainers, Diyanet/TIKA)
      - Straits / Montreux leverage signaling
      - S-400 / SCO / BRICS autonomy-track moves
    """
    if not _telegram_available():
        print("[Telegram Turkey] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(TURKEY_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(TURKEY_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Turkey] ❌ fetch error: {str(e)[:200]}")
        return []

# ====================================================================
# EASTERN MED / CAUCASUS SPOKE -- Greece, Cyprus, Azerbaijan (Jun 2026)
# Turkey-spoke + Iran-spoke expansion. Each list leads with proven anchor
# OSINT (ClashReport/OSINTdefender/intelslava/disclosetv -- confirmed live,
# region-wide) so there is real signal immediately. Country-specific handles
# tagged "verify" are best-candidate guesses; _async_fetch_messages skips dead
# usernames gracefully, so unverified entries cost nothing until confirmed.
# ====================================================================

GREECE_CHANNELS = [
    'ClashReport',          # anchor OSINT -- Aegean / Greece-Turkey threads
    'OSINTdefender',        # anchor OSINT -- English, high signal
    'intelslava',           # aggregator -- catches Greece-Turkey items
    'disclosetv',           # breaking conflict news
    # -- Turkish-side framing (the bidirectional Aegean voice -- reused from TURKEY_CHANNELS) --
    'trtworld',             # verify -- TRT World (Turkish state media, EN)
    'dailysabah',           # verify -- Daily Sabah (pro-government daily)
    'abualiexpress',        # verify -- Abu Ali Express (HE+EN, heavy regional)
    # -- Greek-specific (verify handles are live) --
    'GreekCityTimes',       # ⚠️ verify -- Greek City Times (EN)
    'doureios',             # ⚠️ verify -- Doureios (Greek defense)
    'pentapostagma',        # ⚠️ verify -- Pentapostagma (Greek news/defense)
]

def fetch_greece_telegram_signals(hours_back=96):
    """Telegram signals for the Greece tracker -- Aegean / Greece-Turkey / Evros / Eastern-Med deployments.
    96h window matches the Turkey-spoke cadence."""
    if not _telegram_available():
        print("[Telegram Greece] Signals unavailable -- skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(GREECE_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(GREECE_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Greece] ❌ fetch error: {str(e)[:200]}")
        return []


CYPRUS_CHANNELS = [
    'ClashReport',          # anchor OSINT
    'OSINTdefender',        # anchor OSINT
    'intelslava',           # aggregator
    'disclosetv',           # breaking conflict news
    # -- Cyprus-specific (verify handles are live) --
    'CyprusMail',           # ⚠️ verify -- Cyprus Mail (EN daily)
    'incyprus',             # ⚠️ verify -- In-Cyprus
]

def fetch_cyprus_telegram_signals(hours_back=96):
    """Telegram signals for the Cyprus tracker -- SBA/Akrotiri, buffer zone, Eastern-Med hydrocarbons, Greece deployments.
    96h window matches the Turkey-spoke cadence."""
    if not _telegram_available():
        print("[Telegram Cyprus] Signals unavailable -- skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(CYPRUS_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(CYPRUS_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Cyprus] ❌ fetch error: {str(e)[:200]}")
        return []


AZERBAIJAN_CHANNELS = [
    'ClashReport',          # anchor OSINT
    'OSINTdefender',        # anchor OSINT
    'intelslava',           # aggregator
    'disclosetv',           # breaking conflict news
    'MiddleEastSpectator',  # Iran-Azerbaijan friction threads
    # -- Azerbaijan-specific (verify handles are live) --
    'caliberaz',            # ⚠️ verify -- Caliber.Az (state-adjacent defense)
    'apa_az',               # ⚠️ verify -- APA news agency
    'trendnewsagency',      # ⚠️ verify -- Trend News Agency
]

def fetch_azerbaijan_telegram_signals(hours_back=96):
    """Telegram signals for the Azerbaijan tracker -- Iran-border/Nakhchivan, Karabakh/Zangezur, Israel ties, BTC pipeline.
    96h window matches the Turkey-spoke cadence."""
    if not _telegram_available():
        print("[Telegram Azerbaijan] Signals unavailable -- skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(AZERBAIJAN_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(AZERBAIJAN_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Azerbaijan] ❌ fetch error: {str(e)[:200]}")
        return []

def fetch_hungary_telegram_signals(hours_back=120):
    """
    Fetch Telegram signals for Hungary stability tracker.
    Uses 120h (5 day) window — captures transition signals
    which move faster than Arctic/strategic but slower than
    active warzones. Key signals to watch:
      - Tisza transition announcements (EU re-engagement, Ukraine unblocking)
      - Fidesz/Orban opposition reaction
      - Russian reaction to losing primary EU ally
      - Brussels response (frozen funds, rule of law proceedings)
      - Slovak tensions / ethnic Hungarian minority issues
      - Media freedom restoration signals
      - Electoral violation dispute signals (both parties filed reports)

    Context (April 12, 2026):
      Magyar/Tisza: 138/199 seats (53.6%), constitutional supermajority
      Orban/Fidesz: 55 seats (37.8%), heading to opposition
      Turnout: 77% — record in post-communist Hungarian history
    """
    if not _telegram_available():
        print("[Telegram Hungary] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(HUNGARY_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(HUNGARY_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Hungary] ❌ fetch error: {str(e)[:200]}")
        return []
        
def fetch_greenland_telegram_signals(hours_back=48):
    """
    Fetch Telegram signals for Greenland sovereignty rhetoric tracker.
    Uses 48h window — Greenland moves slower than active warzones.
    """
    if not _telegram_available():
        print("[Telegram Greenland] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(GREENLAND_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(GREENLAND_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Greenland] ❌ fetch error: {str(e)[:200]}")
        return []


def fetch_russia_telegram_signals(hours_back=168):
    """
    Fetch Telegram signals for Russia rhetoric tracker.
    Uses 168h (7 day) window — matches Russia tracker scan interval
    and captures slower-moving strategic signals like nuclear/Arctic.
    """
    if not _telegram_available():
        print("[Telegram Russia] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(RUSSIA_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(RUSSIA_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Russia] ❌ fetch error: {str(e)[:200]}")
        return []


def _telegram_available():
    """Check if Telegram integration is fully configured."""
    if not TELETHON_AVAILABLE:
        return False
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
        print("[Telegram Europe] ⚠️ Missing environment variables")
        return False
    return True


def _ensure_session_file():
    """Decode session file from base64 env var if needed."""
    session_path = f'{SESSION_NAME}.session'
    if os.path.exists(session_path):
        return True

    session_b64 = os.environ.get('TELEGRAM_SESSION_BASE64')
    if session_b64:
        try:
            session_data = base64.b64decode(session_b64)
            with open(session_path, 'wb') as f:
                f.write(session_data)
            print(f"[Telegram Europe] ✅ Session file decoded ({len(session_data)} bytes)")
            return True
        except Exception as e:
            print(f"[Telegram Europe] ❌ Session decode error: {str(e)[:100]}")
            return False

    print("[Telegram Europe] ⚠️ No session file and no TELEGRAM_SESSION_BASE64 env var")
    return False


async def _async_fetch_messages(channels, hours_back=24):
    """
    Async function to fetch messages from Telegram channels.
    Returns list of messages compatible with Europe backend article format.
    """
    if not _ensure_session_file():
        return []

    messages = []
    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    try:
        client = TelegramClient(SESSION_NAME, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            print("[Telegram Europe] ❌ Session not authorized")
            await client.disconnect()
            return []

        # v2.0.0: deduplicate case-insensitively -- Telegram handles are not
        # case-sensitive, so 'RageIntel' and 'rageintel' are one channel.
        seen = set()
        unique_channels = []
        for _ch in channels:
            if _ch.lower() not in seen:
                seen.add(_ch.lower())
                unique_channels.append(_ch)
        channels = unique_channels

        limit = _msg_limit(hours_back)
        _tiers = {}
        for _ch in channels:
            _t = get_channel_meta(_ch)['tier']
            _tiers[_t] = _tiers.get(_t, 0) + 1
        print(f"[Telegram Europe] ✅ Connected, fetching from {len(channels)} channels "
              f"(limit {limit}/channel) -- tiers: {_tiers}")

        for channel in channels:
            _meta = get_channel_meta(channel)
            try:
                entity = await client.get_entity(channel)
                history = await client(GetHistoryRequest(
                    peer=entity,
                    limit=limit,
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                ))

                channel_count = 0
                for msg in history.messages:
                    if msg.date and msg.date.replace(tzinfo=timezone.utc) > since and msg.message:
                        messages.append({
                            'title': msg.message[:200],
                            'url': f'https://t.me/{channel}/{msg.id}',
                            'published': msg.date.replace(tzinfo=timezone.utc).isoformat(),
                            'query': f'telegram_{channel}',
                            'source': f'Telegram @{channel}',
                            'views': getattr(msg, 'views', 0) or 0,
                            'forwards': getattr(msg, 'forwards', 0) or 0,
                            # --- v2.0.0 provenance (additive; existing
                            # consumers reading title/url/source are unaffected)
                            'channel': channel,
                            'source_tier': _meta['tier'],
                            'source_lang': _meta['lang'],
                        })
                        channel_count += 1

                print(f"[Telegram Europe] @{channel}: {channel_count} messages "
                      f"[{_meta['tier']}/{'+'.join(_meta['lang'])}] (last {hours_back}h)")

            except FloodWaitError as e:
                wait = e.seconds
                print(f"[Telegram Europe] @{channel} flood wait {wait}s — skipping channel")
                if wait > 300:
                    # More than 5 min wait -- bail out of entire Telegram session
                    print(f"[Telegram Europe] ⚠️ Flood wait > 5min — stopping Telegram fetch early")
                    break
                await asyncio.sleep(min(wait, 30))
                continue
            except (UsernameInvalidError, UsernameNotOccupiedError):
                print(f"[Telegram Europe] @{channel} — invalid/dead username, skipping")
                continue
            except Exception as e:
                print(f"[Telegram Europe] @{channel} error: {str(e)[:100]}")
                continue

        await client.disconnect()
        print(f"[Telegram Europe] ✅ Total: {len(messages)} messages from {len(channels)} channels")

    except Exception as e:
        print(f"[Telegram Europe] ❌ Connection error: {str(e)[:200]}")
        try:
            await client.disconnect()
        except:
            pass

    return messages


def fetch_europe_telegram_signals(hours_back=24, include_extended=True):
    """
    Synchronous wrapper to fetch European Telegram messages.

    Args:
        hours_back: How many hours back to fetch (default 24)
        include_extended: Whether to include extended channel list (Caucasus, Baltic, etc.)

    Returns:
        List of dicts with keys: title, url, published, query, source, views, forwards
    """
    if not _telegram_available():
        print("[Telegram Europe] Signals unavailable — skipping")
        return []

    channels = EUROPE_CHANNELS.copy()
    if include_extended:
        channels.extend(EXTENDED_EUROPE_CHANNELS)

    # Bridge async to sync
    try:
        try:
            loop = asyncio.get_running_loop()
            print("[Telegram Europe] ⚠️ Event loop already running — using thread")
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(channels, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(channels, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Europe] ❌ fetch error: {str(e)[:200]}")
        return []


def fetch_poland_telegram_signals(hours_back=96):
    """
    Fetch Telegram signals for the Poland consensus tracker.

    96h window -- Poland's hybrid tape is steady rather than bursty. The
    campaign is designed to be sustainable, so it does not spike the way an
    active-war theatre does; a shorter window would miss the pattern and a
    longer one would blur it.

    Key signals to watch:
      - Sabotage / arson / rail incidents (kinetic domain)
      - Cyber incidents against energy, rail, government (cyber domain)
      - Doppelgänger / Matryoshka / bot-campaign detection (cognitive domain)
      - POLISH ATTRIBUTION -- ABW/Tusk/Siemoniak naming Russia. Note this is
        scored as RESILIENCE, not damage: a state that names its attacker in
        public is a state whose consensus is functioning.
      - Belarus border / instrumentalized migration
      - Volhynia / Poland-Ukraine wedge amplification
    """
    if not _telegram_available():
        print("[Telegram Poland] Signals unavailable — skipping")
        return []
    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _async_fetch_messages(POLAND_CHANNELS, hours_back))
                return future.result(timeout=120)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_async_fetch_messages(POLAND_CHANNELS, hours_back))
            finally:
                loop.close()
    except Exception as e:
        print(f"[Telegram Poland] ❌ fetch error: {str(e)[:200]}")
        return []


def get_europe_telegram_status():
    """Return status info for health check / debugging."""
    return {
        'telethon_installed': TELETHON_AVAILABLE,
        'api_configured': bool(TELEGRAM_API_ID and TELEGRAM_API_HASH),
        'phone_configured': bool(TELEGRAM_PHONE),
        'session_available': os.path.exists(f'{SESSION_NAME}.session') or bool(os.environ.get('TELEGRAM_SESSION_BASE64')),
        'core_channels': EUROPE_CHANNELS,
        'extended_channels': EXTENDED_EUROPE_CHANNELS,
        'ready': _telegram_available() and (os.path.exists(f'{SESSION_NAME}.session') or bool(os.environ.get('TELEGRAM_SESSION_BASE64')))
    }
