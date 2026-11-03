"""
Asifah Analytics -- Europe Signal Matcher v1.0.0
November 3, 2026   (Europe backend; used by the Poland interpreter and the Russia tracker)

WHY THIS EXISTS
  The same defect Africa (Nov 2) and Asia (Nov 2) had: levels come from EXACT
  PHRASES that real headlines almost never contain word for word. Live read,
  Nov 2 2026 evening -- Poland's own corpus carried:
      "Poland launches operation along Russian border in response to reports
       of planned sabotage"                                    (Notes from Poland)
      "Poland detains Ukrainian accused of arson attack in Romania on behalf
       of Russia"                                              (Notes from Poland)
      "Polish president in physical confrontation with judges amid power
       struggle at constitutional court"                       (Notes from Poland)
      "Polish ambassador to UN becomes third envoy to resign amid crisis over
       constitutional court"                                   (Notes from Poland)
  ...and printed: russian_pressure L0, hybrid tape "quiet" on all three
  domains, cohabitation "quiet, 0 signals". The trigger was 'sabotage poland';
  the headline said "Poland ... planned sabotage". A broken sensor reporting calm
  -- on exactly the vectors the Poland tracker exists to read (the hybrid
  campaign and the cohabitation gap). Russia's own tracker read nato_flank L0 and
  hybrid L0 on 1,369 articles the same week.

WHAT IT DOES
  Two-part (co-occurrence) matching: a rule fires when EVERY one of its term
  groups appears in the same headline + summary. English plus Polish, Russian,
  Ukrainian and Romanian terms where the trackers fetch them.
  * Text is normalised (lowercase, accents stripped, apostrophes unified).
    Latin terms match whole words; 'stem*' matches a word start. Cyrillic terms
    match as substrings (stems), which is how Russian inflection behaves.
  * CORROBORATION: L3+ needs 2+ different outlets at that level; one outlet
    alone tops out at L2. For count-style vectors (Poland's domain bands) the
    same rule: one outlet counts at most 2, so it can read "simmering" but never
    "elevated" on its own.
  * History is not a signal: anniversaries, documentaries, "years after" and
    retrospectives are excluded from every ladder.
  * It only ever RAISES a reading -- max(old, co-occurrence). Every raise is
    recorded with the rule, the outlets and the headlines.

  Entry points:
    count_cooccurrence(tracker, scan_data, key) -- Poland interpreter: domain
        counts (kinetic / cyber / cognitive / attribution / migration /
        cohabitation) that feed its existing bands.
    vector_cooccurrence(tracker, articles)      -- Russia tracker: nato_flank and
        hybrid raised; NEW vectors drone_incursion (into a NON-belligerent's
        airspace -- never battlefield strikes inside Ukraine) and black_sea.
    corroborated_vector(articles, trigger_dict) -- literal phrase ladders under
        the platform corroboration rule (L3+ needs two outlets) and with the
        phrase + outlets that set the level recorded.
"""

import re
import unicodedata
from urllib.parse import urlparse

MATCHER_VERSION = '1.0.0'


# ----------------------------------------------------------------------------
# NORMALISATION + MATCHING
# ----------------------------------------------------------------------------
def norm(text):
    t = str(text or '').replace('’', "'").replace('‘', "'").replace('ʼ', "'")
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace('ł', 'l')          # Polish l-stroke has no decomposition
    # Places, not actors: the Black Sea is not "Black", Russian Federation stays russia.
    return t


_NONLATIN = re.compile(r'[Ѐ-ӿ؀-ۿ぀-ヿ㐀-鿿가-힯]')
_RX = {}


def _term_rx(term):
    rx = _RX.get(term)
    if rx is None:
        t = norm(term)
        if _NONLATIN.search(t):
            rx = re.compile(re.escape(t.rstrip('*')))
        elif t.endswith('*'):
            rx = re.compile(r'(?<![a-z0-9])' + re.escape(t[:-1]))
        else:
            rx = re.compile(r'(?<![a-z0-9])' + re.escape(t) + r'(?![a-z0-9])')
        _RX[term] = rx
    return rx


def has_any(ntext, terms):
    for t in terms:
        if _term_rx(t).search(ntext):
            return t
    return None


def outlet_of(a):
    """The PUBLISHER, never the feed. A Google News item's title ends ' - Outlet'."""
    title = str(a.get('title') or '')
    if ' - ' in title:
        tail = title.rsplit(' - ', 1)[1].strip()
        if 0 < len(tail) <= 60:
            return tail.lower()
    src = a.get('source')
    if isinstance(src, dict):
        src = src.get('name')
    src = str(src or '').strip()
    if src and not src.lower().startswith(('gnews', 'google news', 'googlenews', 'gdelt', 'http')):
        return src.lower()
    host = urlparse(str(a.get('url') or a.get('link') or '')).netloc.lower().replace('www.', '')
    return host or 'unknown'


def _text(a):
    return ' '.join(str(a.get(k) or '') for k in ('title', 'description', 'summary', 'content', 'text'))


def _R(name, level, groups, exclude=None):
    return {'name': name, 'level': level, 'groups': groups, 'exclude': exclude or []}


def fire_rules(ntext, rules):
    for r in sorted(rules, key=lambda x: -x['level']):
        if r.get('exclude') and has_any(ntext, r['exclude']):
            continue
        hits = []
        for g in r['groups']:
            h = has_any(ntext, g)
            if not h:
                break
            hits.append(h)
        else:
            return r['level'], r['name'], hits
    return 0, None, None


def corroborated_level(levels_by_outlet):
    for L in range(5, 0, -1):
        n = sum(1 for v in levels_by_outlet.values() if v >= L)
        if n >= (2 if L >= 3 else 1):
            return L
    return 0


# ----------------------------------------------------------------------------
# SHARED TERM SETS
# ----------------------------------------------------------------------------
HISTORY = ['anniversary', 'years after', 'years since', 'years ago', 'documentary', 'film', 'movie',
           'book review', 'museum', 'remembers', 'retrospective', 'in memoriam', 'rocznic*']

RU = ['russia', 'russian', "russia's", 'moscow', 'kremlin', 'putin', 'gru', 'fsb', 'svr', 'wagner',
      'rosja', 'rosyjsk*', 'moskw*', 'rusia', 'rusiei', 'rusesc*',
      'росси', 'российск', 'кремл',
      'росі', 'російськ']
BY = ['belarus', 'belarusian', 'lukashenko', 'minsk', 'bialorus*', 'беларус']
PL = ['poland', 'polish', "poland's", 'warsaw', 'polska', 'polski*', 'polsk*', 'polsce', 'polske', 'polski',
      'warszaw*', 'rzeszow',
      'gdansk', 'krakow', 'wroclaw', 'lublin', 'bialystok', 'tusk', 'nawrocki', 'sikorski', 'kosiniak*',
      'siemoniak', 'abw', 'skw', 'польш']
# Non-belligerents a Russian drone or saboteur can reach. Ukraine is deliberately
# absent: a drone over Ukraine is the war, not an incursion.
NONBELL = PL + ['romania', 'romanian', 'bucharest', 'moldova', 'moldovan', 'chisinau', 'lithuania',
                'lithuanian', 'vilnius', 'latvia', 'latvian', 'riga', 'estonia', 'estonian', 'tallinn',
                'baltic state*', 'baltics', 'finland', 'finnish', 'helsinki', 'denmark', 'danish',
                'copenhagen', 'norway', 'norwegian', 'sweden', 'swedish', 'germany', 'german', 'berlin',
                'netherlands', 'dutch', 'belgium', 'belgian', 'czech', 'slovakia', 'hungary', 'bulgaria',
                'nato airspace', 'nato territory', 'nato member*', "nato's eastern flank", 'eastern flank']

DRONE = ['drone*', 'uav*', 'unmanned aerial', 'shahed*', 'geran*', 'gerbera', 'dron*', 'bezzalogow*',
         'беспилот', 'дрон']
INCURSION = ['incursion*', 'violat*', 'airspace', 'intrusion*', 'entered', 'crossed into', 'strayed into',
             'crashed in', 'crashed into', 'fell in', 'landed in', 'found in', 'debris', 'wreckage',
             'shot down', 'scrambl*', 'naruszen*', 'przestrzen* powietrzn*', 'spadl*']
INCURSION_SEVERE = ['shot down', 'downed', 'article 4', 'nato consult*', 'closed airspace',
                    'airport closed', 'airports closed', 'scrambl*']
# Drone POLICY is not a drone EVENT: "EU plans drone wall to protect airspace".
DRONE_POLICY = ['drone wall', 'counter-drone', 'anti-drone', 'procure*', 'contract*', 'purchas*', 'order*',
                'manufactur*', 'startup*', 'production', 'industry', 'exhibition', 'trade fair', 'training',
                'exercise*', 'drill*', 'plans to', 'plan to', 'proposal', 'budget']
HARM = ['killed', 'dead', 'deaths', 'casualt*', 'injur*', 'wounded', 'zabit*', 'ranny*', 'ofiar*']

SABOTAGE = ['sabotage*', 'saboteur*', 'sabotaz*', 'dywersj*', 'dywersant*', 'arson*', 'podpal*',
            'incendiary', 'parcel bomb*', 'bomb plot*', 'planned attack*', 'explosive device*',
            'derail*', 'rail line damaged', 'railway damaged', 'tracks damaged', 'cable* cut', 'cut cable*',
            'cable damage*', 'undersea cable*', 'pipeline damage*', 'infrastructure attack*',
            'diversion attack*', 'диверс', 'поджог']
LAW = ['arrest*', 'detain*', 'charged', 'charges', 'indict*', 'convicted', 'sentenced', 'suspect*',
       'operation', 'raid*', 'counter-terror*', 'counterterror*', 'police', 'prosecutor*', 'zatrzym*']
CYBER = ['cyberattack*', 'cyber attack*', 'cyber-attack*', 'hack*', 'ddos', 'ransomware', 'wiper*',
         'malware', 'cyberatak*', 'atak hakerski', 'кибератак']
COGNITIVE = ['disinformation', 'propaganda', 'troll*', 'bot network*', 'bot farm*', 'influence operation*',
             'influence campaign*', 'deepfake*', 'fake news', 'doppelganger', 'matryoshka', 'information war*',
             'dezinformacj*', 'дезинформ']
ATTRIB = ['blame*', 'accus*', 'attribut*', 'on behalf of', 'commissioned by', 'working for', 'linked to',
          'tied to', 'ties to', 'at the behest of', 'orchestrat*', 'behind the', 'expel*', 'deport*',
          'persona non grata', 'closes consulate', 'closed consulate', 'spy', 'spies', 'espionage',
          'intelligence ties', 'agent*']
MIGRATION = ['migrant*', 'migrat*', 'irregular migration', 'attempts to cross', 'border crossing*', 'crossing attempt*', 'illegal crossing*', 'pushback*',
             'border fence', 'border barrier', 'border wall', 'tunnel*', 'instrumentali*', 'weaponi*',
             'hybrid migration', 'migracj*', 'migranc*']
BORDER = ['border', 'frontier', 'granic*']

# Cohabitation: president vs government -- the gap the Poland tracker calls THE OPENING.
PL_PRES = ['nawrocki', 'president', 'presidential', 'prezydent*', 'palac prezydencki']
PL_INSTITUTIONS = ['tusk', 'government', 'prime minister', 'cabinet', 'constitutional court',
                   'constitutional tribunal', 'tribunal', 'trybunal*', 'judges', 'chief justice',
                   'supreme court', 'parliament', 'sejm', 'veto*', 'rzad*', 'premier']
PL_CONFLICT = ['crisis', 'clash*', 'confrontation', 'stand-off', 'standoff', 'power struggle', 'veto*',
               'vetoes', 'vetoed', 'resign*', 'deadlock*', 'chaos', 'oust*', 'impasse', 'blocks', 'blocked',
               'feud*', 'conflict', 'riot police', 'kryzys*', 'spor*', 'weto']

BLACK_SEA = ['black sea', 'odesa', 'odessa', 'sea of azov', 'azov', 'bosphorus', 'bosporus',
             'turkish straits', 'dardanelles', 'danube', 'izmail', 'reni', 'chornomorsk', 'pivdennyi',
             'novorossiysk', 'sevastopol', 'kerch', 'constanta', 'snake island', 'grain corridor',
             'черное мор', 'черном мор',
             'чорне мор', 'одес']
SHIP = ['tanker*', 'vessel*', 'ship', 'ships', 'shipping', 'cargo', 'bulk carrier*', 'freighter*',
        'container ship*', 'port', 'ports', 'harbou*', 'terminal*', 'grain ship*', 'merchant']
STRIKE = ['struck', 'hit by', 'hits', 'attack*', 'drone strike*', 'missile*', 'explosion*', 'exploded',
          'damag*', 'on fire', 'ablaze', 'sank', 'sunk', 'sinking', 'targeted', 'shelled']
MINE = ['sea mine*', 'naval mine*', 'drifting mine*', 'mine', 'mines', 'minefield*', 'minesweep*',
        'mine clearance', 'mine-clearing', 'mine countermeasure*']
SEA_DRONE = ['naval drone*', 'sea drone*', 'maritime drone*', 'unmanned surface', 'usv*', 'magura*',
             'sea baby']
PASSAGE = ['blockade*', 'closed to shipping', 'suspend* shipping', 'halt* shipping', 'shipping halted',
           'war risk', 'insurance premium*', 'transit suspended', 'passage', 'blocked']
NAVAL = ['black sea fleet', 'fleet', 'navy', 'naval', 'warship*', 'frigate*', 'submarine*', 'patrol*']


# ----------------------------------------------------------------------------
# POLAND -- count-style domains for poland_signal_interpreter.py
# Each rule's level only orders the rules; Poland's bands come from COUNTS.
# ----------------------------------------------------------------------------
POLAND_COUNTS = {
    # Kinetic hybrid: sabotage / arson / rail / drone incursion touching Poland.
    'kinetic': [
        _R('sabotage_poland', 3, [SABOTAGE, PL], exclude=HISTORY),
        _R('drone_incursion_poland', 3, [DRONE, INCURSION, PL], exclude=HISTORY + DRONE_POLICY),
        _R('gps_jamming', 2, [['gps jamming', 'gps interference', 'gnss jamming', 'zaklocen* gps'],
                              PL + ['baltic']], exclude=HISTORY),
    ],
    'cyber': [
        _R('cyber_poland', 3, [CYBER, PL], exclude=HISTORY),
    ],
    'cognitive': [
        _R('influence_op_poland', 3, [COGNITIVE, PL, RU], exclude=HISTORY),
    ],
    # Poland (or a NATO neighbour) publicly naming Russia -- resilience, not damage.
    'attribution': [
        _R('names_russia', 3, [PL + ['estonia', 'latvia', 'lithuania', 'romania'], ATTRIB, RU],
           exclude=HISTORY),
        # A sabotage case counts as ATTRIBUTION only when someone links it to Russia --
        # "planned sabotage along the Russian border" is a sabotage signal, not attribution.
        _R('sabotage_case_russia', 3, [SABOTAGE, RU, ATTRIB], exclude=HISTORY),
    ],
    'migration': [
        _R('belarus_border_pressure', 3, [MIGRATION, BY + BORDER, PL + ['latvia', 'lithuania']],
           exclude=HISTORY),
    ],
    'cohabitation': [
        _R('president_vs_government', 3, [PL_PRES, PL_INSTITUTIONS, PL_CONFLICT, PL], exclude=HISTORY),
        # The constitutional-court fight IS the cohabitation fight even when a headline
        # names only the court ("Police deployed during stand-off over control of top Poland court").
        _R('court_power_struggle', 3, [['constitutional court', 'constitutional tribunal', 'trybunal*',
                                        'top court', 'chief justice', 'supreme court', 'judges',
                                        'justices', 'court'],
                                       PL_CONFLICT + ['police deployed', 'suspended'], PL], exclude=HISTORY),
    ],
}


# ----------------------------------------------------------------------------
# RUSSIA -- vector ladders for rhetoric_tracker_russia.py
# ----------------------------------------------------------------------------
RUSSIA_VECTORS = {
    # Russia pressing NATO's flank. L5 is never asserted here: an attack on NATO
    # territory must come from the literal L5 ladder AND two outlets.
    'nato_flank': [
        _R('drone_incursion_harm', 4, [DRONE, INCURSION, NONBELL, HARM], exclude=HISTORY + DRONE_POLICY),
        _R('drone_incursion_severe', 4, [DRONE, NONBELL, INCURSION_SEVERE], exclude=HISTORY + DRONE_POLICY),
        _R('drone_incursion', 3, [DRONE, INCURSION, NONBELL], exclude=HISTORY + DRONE_POLICY),
        _R('airspace_violation', 3, [RU, ['jet*', 'aircraft', 'fighter*', 'bomber*', 'mig-*', 'su-*'],
                                     ['violat*', 'intercept*', 'scrambl*', 'airspace'], NONBELL],
           exclude=HISTORY),
        _R('flank_buildup', 3, [RU, ['kaliningrad', 'suwalki', 'border', 'iskander*'],
                                ['deploy*', 'buildup', 'build-up', 'drill*', 'exercise*', 'troops',
                                 'missile*', 'threat*']], exclude=HISTORY),
        _R('flank_tension', 2, [RU, NONBELL, ['threat*', 'warn*', 'tension*', 'provocation*', 'hostile']],
           exclude=HISTORY),
    ],
    # The deniable campaign: sabotage, cyber, influence, weaponised migration.
    'hybrid': [
        _R('sabotage_harm', 4, [SABOTAGE, NONBELL, HARM], exclude=HISTORY),
        _R('sabotage_attributed', 3, [SABOTAGE, NONBELL, RU], exclude=HISTORY),
        _R('sabotage_case', 3, [SABOTAGE, LAW, NONBELL], exclude=HISTORY),
        _R('spy_expelled', 3, [RU, ['spy', 'spies', 'espionage', 'intelligence ties', 'agent*', 'diplomat*'],
                               ['expel*', 'deport*', 'arrest*', 'detain*', 'charged', 'persona non grata'],
                               NONBELL], exclude=HISTORY),
        _R('cyber_attributed', 3, [CYBER, RU, NONBELL], exclude=HISTORY),
        _R('migration_weaponised', 3, [MIGRATION, BY + RU, NONBELL], exclude=HISTORY),
        _R('influence_op', 2, [COGNITIVE, RU, NONBELL], exclude=HISTORY),
    ],
    # NEW (Nov 3 2026, Rachel's matrix priority): drones INTO a non-belligerent.
    # Battlefield strikes inside Ukraine never count -- Ukraine is not in NONBELL,
    # and a story must also carry incursion vocabulary.
    'drone_incursion': [
        _R('incursion_harm', 4, [DRONE, INCURSION, NONBELL, HARM], exclude=HISTORY + DRONE_POLICY),
        _R('incursion_severe', 4, [DRONE, NONBELL, INCURSION_SEVERE], exclude=HISTORY + DRONE_POLICY),
        _R('incursion', 3, [DRONE, INCURSION, NONBELL], exclude=HISTORY + DRONE_POLICY),
        _R('incursion_report', 2, [DRONE, ['airspace', 'incursion*', 'violat*'], NONBELL], exclude=HISTORY + DRONE_POLICY),
    ],
    # NEW (Nov 3 2026, Rachel's matrix priority): the Black Sea -- passage, mines,
    # shipping attacks. Corroborated like everything else.
    'black_sea': [
        _R('shipping_struck', 4, [BLACK_SEA, SHIP, STRIKE], exclude=HISTORY),
        _R('mine_strike', 4, [BLACK_SEA, MINE, ['hit*', 'struck', 'explod*', 'damag*', 'sank', 'sunk', 'blast']],
           exclude=HISTORY),
        _R('passage_restricted', 3, [BLACK_SEA, PASSAGE, SHIP + ['grain', 'traffic']], exclude=HISTORY),
        _R('sea_drone_attack', 3, [BLACK_SEA, SEA_DRONE], exclude=HISTORY),
        _R('mine_threat', 3, [BLACK_SEA, MINE], exclude=HISTORY),
        _R('naval_activity', 2, [BLACK_SEA, NAVAL + SHIP], exclude=HISTORY),
    ],
}

PROFILES = {'poland': POLAND_COUNTS, 'russia': RUSSIA_VECTORS}


# ----------------------------------------------------------------------------
# SCANNING
# ----------------------------------------------------------------------------
def _scan(articles, ladders):
    per = {k: {} for k in ladders}
    rule_at = {k: {} for k in ladders}
    examples = {k: [] for k in ladders}
    seen_titles = {k: set() for k in ladders}
    counts = {k: 0 for k in ladders}
    for a in articles or []:
        if not isinstance(a, dict):
            continue
        nt = norm(_text(a))
        if not nt.strip():
            continue
        outlet = outlet_of(a)
        tkey = norm(a.get('title') or a.get('text') or '')[:90]
        for k, rules in ladders.items():
            lvl, rname, ev = fire_rules(nt, rules)
            if not lvl:
                continue
            if tkey and tkey in seen_titles[k]:
                continue            # same story syndicated twice is one story
            seen_titles[k].add(tkey)
            counts[k] += 1
            if lvl > per[k].get(outlet, 0):
                per[k][outlet] = lvl
            rule_at[k].setdefault(lvl, rname)
            if len(examples[k]) < 5:
                src = a.get('source')
                examples[k].append({'level': lvl, 'rule': rname, 'evidence': ev,
                                    'title': str(a.get('title') or a.get('text') or '')[:150],
                                    'outlet': outlet, 'url': a.get('url') or a.get('link') or '',
                                    'source': src.get('name', '') if isinstance(src, dict) else str(src or ''),
                                    'publishedAt': a.get('publishedAt') or a.get('published') or ''})
    out = {}
    for k in ladders:
        L = corroborated_level(per[k])
        peak = max(per[k].values()) if per[k] else 0
        out[k] = {'level': L, 'raw_peak': peak, 'articles': counts[k], 'outlets': len(per[k]),
                  'rule': rule_at[k].get(L) or rule_at[k].get(peak) or '',
                  'held_back_for_corroboration': peak > L, 'examples': examples[k]}
    return out


def _pool(scan_data):
    """Every text item a tracker holds, whatever it calls its lists."""
    if isinstance(scan_data, list):
        return scan_data
    pool = []
    for key in ('articles', 'articles_en', 'articles_pl', 'articles_ru', 'articles_uk', 'articles_ro',
                'telegram_messages', 'bluesky_signals', 'reddit_signals'):
        pool.extend(x for x in (scan_data.get(key) or []) if isinstance(x, dict))
    return pool


_POOL_CACHE = {}


def count_cooccurrence(tracker, scan_data, key):
    """Poland-style count for one domain -> {'count', 'outlets', 'articles', 'examples', ...}.
    'count' obeys corroboration: one outlet counts at most 2 (never 'elevated' alone)."""
    ladders = PROFILES.get(tracker, {})
    if key not in ladders:
        return {'count': 0, 'outlets': 0, 'articles': 0, 'examples': [], 'rule': ''}
    sid = id(scan_data)
    cached = _POOL_CACHE.get((tracker, sid))
    if cached is None or cached[0] is not scan_data:
        reads = _scan(_pool(scan_data), ladders)
        _POOL_CACHE.clear()
        _POOL_CACHE[(tracker, sid)] = (scan_data, reads)
    else:
        reads = cached[1]
    r = dict(reads[key])
    r['count'] = r['articles'] if r['outlets'] >= 2 else min(r['articles'], 2)
    return r


def cooccurrence_report(tracker, scan_data):
    """The full per-domain read, for the payload (`cooccurrence`)."""
    ladders = PROFILES.get(tracker, {})
    reads = _scan(_pool(scan_data), ladders)
    for r in reads.values():
        r['count'] = r['articles'] if r['outlets'] >= 2 else min(r['articles'], 2)
    return {'version': MATCHER_VERSION, 'tracker': tracker, 'domains': reads}


def vector_cooccurrence(tracker, articles):
    """-> (vector_levels {name: level}, report)."""
    ladders = PROFILES.get(tracker, {})
    reads = _scan(_pool(articles), ladders)
    levels = {k: r['level'] for k, r in reads.items()}
    return levels, {'version': MATCHER_VERSION, 'tracker': tracker, 'vectors': reads}


def corroborated_vector(articles, trigger_dict, context=None):
    """Literal phrase ladder under the platform corroboration rule.
    -> (level, phrase, outlets_at_level). L3+ needs 2 outlets carrying a phrase
    at that level; one outlet tops out at L2. `context` (optional {level: terms})
    requires a context term in the same article for that level -- e.g. Russia's
    L5 nuclear phrases must also mention Russia or Ukraine, so "A US nuclear
    strike on Iran?" cannot put Russia at Strategic Escalation."""
    per, phrase_at, outlets_at = {}, {}, {}
    for a in articles or []:
        if not isinstance(a, dict):
            continue
        text = f"{a.get('title') or ''} {a.get('description') or ''}".lower()
        ntext = None
        for level in sorted(trigger_dict, reverse=True):
            hit = next((p for p in trigger_dict[level] if p.lower() in text), None)
            if not hit:
                continue
            if context and level in context:
                ntext = ntext or norm(text)
                if not has_any(ntext, context[level]):
                    continue
            o = outlet_of(a)
            if level > per.get(o, 0):
                per[o] = level
            phrase_at.setdefault(level, hit)
            outlets_at.setdefault(level, set()).add(o)
            break
    L = corroborated_level(per)
    phrase = phrase_at.get(L)
    if L and phrase is None:
        phrase = next((phrase_at[x] for x in sorted(phrase_at, reverse=True) if x >= L), None)
    n = len({o for lv, os in outlets_at.items() if lv >= L for o in os}) if L else 0
    return L, phrase, n


def matching_items(tracker, scan_data, key):
    """[(outlet, normalised_text)] for every item that fires `key`'s ladder.
    Lets an interpreter measure severity INSIDE the stories that carried the
    signal, never across the whole corpus (Nov 3 2026: a South Korean soldier's
    death must not become a casualty from Polish sabotage)."""
    rules = PROFILES.get(tracker, {}).get(key) or []
    out = []
    for a in _pool(scan_data):
        nt = norm(_text(a))
        if nt.strip() and fire_rules(nt, rules)[0]:
            out.append((outlet_of(a), nt))
    return out
