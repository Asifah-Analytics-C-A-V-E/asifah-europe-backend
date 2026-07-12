"""
Kazakhstan Signal Interpreter v1.0.0 (Jul 12 2026)
===================================================
Analytical layer for rhetoric_tracker_kazakhstan.py.

THE FRAME: Kazakhstan is not a "drift" country. Multi-vector hedging IS the
state doctrine -- Astana sells stability to Moscow, Beijing, Washington and
the markets simultaneously, and the product is mostly real. So the sensor is
NOT "which way is it drifting" (that is the Armenia instrument). The sensor is
"IS THE HEDGE HOLDING" -- a three-pole balance index where DIVERGENCE FROM
EQUILIBRIUM is the signal, whichever pole is pulling.

THE STRUCTURAL READ the tracker exists to surface: Kazakhstan's two flagship
global exports -- crude (CPC to Novorossiysk) and ~40% of the world's uranium
-- BOTH physically transit Russia. Chromium rides Chinese rail east. Its
commodity POWER is real and its commodity ROUTES are owned by the two
neighbours it is hedging against. The Middle Corridor is the attempted escape
from exactly that. The commodity data explains the corridor's existence.

Vector set:
  1. Middle Corridor / TITR -- corridor-vector family member #2 (inherits the
     portable schema from TRIPP; BRI and IMEC to follow).
  2. Russia levers -- CPC chokehold, northern-irredentist rhetoric, sanctions-
     rerouting corridor, language-status friction. Reporting tempo, both
     directions honest.
  3. China dual-track -- ELITE PULL (BRI, trade, pipelines) vs STREET FRICTION
     (Sinophobia, land protests, Xinjiang ethnic-Kazakh grievance, Ili/Irtysh
     water). One vector, two polarities. This is what feeds the FIRST China
     spoke.
  4. Domestic tripwire -- the January 2022 pattern class: fuel/utility price
     announcement -> Mangystau/Zhanaozen labour unrest -> metastasis. Pattern
     memory, not prophecy.
  5. Hedging-integrity index -- three-pole balance. Divergence IS the signal.
  6. West/minerals anchor -- C5+1, critical-minerals courtship, TCO/Kashagan.
  7. Turkic integration (light) -- OTS, Ankara drone/defence ties.
  8. Succession -- the vice presidency created by the Jul 1 2026 constitution
     is presidentially appointed. Whoever gets it is the anointed successor.
     Highest-value discrete signal in the country.

Multipliers (NEVER standalone signals -- Black Swan discipline):
  - Kurultai election clock (Aug 23 2026; snap presidential chatter live)
  - Winter heating calendar (the Jan-2022 tripwire is seasonal)

Commodity vector is CONVERGENCE-GATED. Kazakhstan's commodity pressure is
STRUCTURAL (world's #1 uranium producer every single day), so feeding it into
the score would pin the country at 'surge' permanently and the alarm would
stop meaning anything. It fires a signal ONLY when commodity pressure
co-occurs with a live pressure vector -- because THAT is the story: a
chokepoint being squeezed, not a chokepoint merely existing.

Doctrine: convergence, not prediction. Estimative voice, precedent-anchored.
The reader completes the inference. Absence stays honest.
"""

from datetime import datetime, timezone

INTERPRETER_VERSION = '1.0.0'

CONVERGENCE_DISCLAIMER = (
    'This composite is a CONVERGENCE indicator, NOT a probability of action. '
    'Active signals indicate pressure conditions are present; they do not '
    'predict whether or when any specific outcome will occur.'
)


# ============================================================
# CORPUS KEYWORD MATCHER
# ============================================================

def _check_keywords(scan_data, keywords):
    """Match keywords against the scan corpus. URL slugs are de-hyphenated so
    multi-word keywords match headline slugs."""
    if not keywords:
        return 0
    parts = []
    for key in ('articles_en', 'articles_kk', 'articles_ru'):
        for art in (scan_data.get(key) or []):
            parts.append((art.get('title') or '').lower())
            parts.append((art.get('description') or '').lower())
            parts.append((art.get('summary') or '').lower())
            parts.append((art.get('content') or '').lower())
            _url = (art.get('url') or art.get('link') or '').lower()
            if _url:
                parts.append(_url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    for key in ('reddit_signals', 'telegram_messages', 'bluesky_signals'):
        for sig in (scan_data.get(key) or []):
            parts.append((sig.get('text') or sig.get('title') or '').lower())
    corpus = ' | '.join(parts)
    if not corpus:
        return 0
    return sum(1 for kw in keywords if kw.lower() in corpus)


# ============================================================
# RED LINES
# ============================================================

RED_LINES = [
    {
        'id': 'fuel_price_unrest',
        'category': 'Fuel-Price Unrest (Jan-2022 Pattern)',
        'severity': 5,
        'breach_threshold': 2,
        'description': ('The precursor chain that produced Bloody January: fuel or utility '
                        'price change -> Mangystau/Zhanaozen labour action -> metastasis. '
                        'Pattern memory, not prophecy.'),
        'keywords': [
            'fuel price protest kazakhstan', 'lpg price kazakhstan', 'gas price protest',
            'utility tariff protest kazakhstan', 'petrol price kazakhstan protest',
            'zhanaozen protest', 'mangystau strike', 'mangistau protest',
            'oil workers strike kazakhstan', 'aktau protest', 'zhanaozen strike',
            'tariff increase protest', 'price hike protest kazakhstan',
            'протесты из-за цен на топливо', 'жанаозен забастовка',
            'забастовка нефтяников',
        ],
    },
    {
        'id': 'mass_unrest',
        'category': 'Mass Unrest / Security Response',
        'severity': 5,
        'breach_threshold': 2,
        'description': ('Nationwide mobilization, state-of-emergency declarations, or CSTO '
                        'assistance requests -- the January 2022 escalation ladder.'),
        'keywords': [
            'state of emergency kazakhstan', 'csto troops kazakhstan', 'csto request kazakhstan',
            'shoot to kill order', 'mass protests kazakhstan', 'riots kazakhstan',
            'internet shutdown kazakhstan', 'security forces open fire kazakhstan',
            'almaty unrest', 'nationwide protests kazakhstan', 'bloody january',
            'чрезвычайное положение казахстан', 'одкб казахстан', 'беспорядки казахстан',
        ],
    },
    {
        'id': 'cpc_disruption',
        'category': 'CPC Route Disruption',
        'severity': 4,
        'breach_threshold': 2,
        'description': ('Suspension, damage, or "maintenance" closure of the Caspian Pipeline '
                        'Consortium route -- historically invoked during periods of political '
                        'friction. The dependency IS the leverage.'),
        'keywords': [
            'cpc pipeline suspended', 'cpc terminal halt', 'caspian pipeline consortium suspend',
            'novorossiysk terminal closed', 'cpc maintenance halt', 'cpc export halt',
            'kazakh oil export disruption', 'cpc court ruling', 'cpc drone damage',
            'oil export blocked kazakhstan', 'transit halt kazakhstan',
            'ктк приостановлен', 'ктк остановка', 'новороссийск терминал',
        ],
    },
    {
        'id': 'russian_irredentist',
        'category': 'Russian Irredentist Rhetoric',
        'severity': 4,
        'breach_threshold': 2,
        'description': ('Russian nationalist or official language questioning Kazakh territorial '
                        'integrity or the status of northern Kazakhstan. Post-Ukraine, Astana '
                        'reads this as existential.'),
        'keywords': [
            'northern kazakhstan russian', 'kazakhstan territorial claim', 'gift from russia',
            'kazakhstan is russian land', 'kazakhstan next after ukraine',
            'russian nationalist kazakhstan', 'kazakhstan artificial state',
            'protect russian speakers kazakhstan', 'russian language kazakhstan status',
            'северный казахстан', 'территориальные претензии казахстан',
            'подарок россии', 'русскоязычные казахстан',
        ],
    },
    {
        'id': 'sanctions_secondary',
        'category': 'Secondary-Sanctions Exposure',
        'severity': 3,
        'breach_threshold': 2,
        'description': ('OFAC/EU action or warnings against Kazakh entities over sanctions '
                        're-export. The rerouting corridor is simultaneously a revenue lifeline '
                        'and a liability -- both directions reported honestly.'),
        'keywords': [
            'ofac kazakhstan', 'secondary sanctions kazakhstan', 'sanctions evasion kazakhstan',
            'parallel imports kazakhstan', 're-export russia kazakhstan',
            'eu sanctions kazakhstan', 'dual-use goods kazakhstan',
            'sanctions circumvention kazakhstan', 'kazakh bank sanctioned',
            'санкции казахстан', 'параллельный импорт', 'реэкспорт в россию',
        ],
    },
    {
        'id': 'sinophobia_flashpoint',
        'category': 'China Street Friction',
        'severity': 3,
        'breach_threshold': 2,
        'description': ('Anti-China protest, land-lease backlash, Xinjiang ethnic-Kazakh '
                        'grievance surfacing, or water-dispute escalation. The street half of '
                        'the China dual-track -- elites pull one way, the street pulls back.'),
        'keywords': [
            'anti-china protest kazakhstan', 'sinophobia kazakhstan', 'land lease china protest',
            'xinjiang kazakhs', 'ethnic kazakhs detained china', 'atajurt',
            'chinese factory protest kazakhstan', 'anti-chinese rally',
            'water dispute china kazakhstan', 'ili river china', 'irtysh water china',
            'debt trap china kazakhstan',
            'антикитайские протесты', 'синьцзян казахи',
        ],
    },
    {
        'id': 'succession_rupture',
        'category': 'Succession Rupture',
        'severity': 3,
        'breach_threshold': 2,
        'description': ('Elite fracture around the succession machinery: the vice presidency '
                        'created by the July 2026 constitution is presidentially appointed, '
                        'making the appointment the highest-value discrete signal in the '
                        'country. Purges, arrests, and clan-conflict reporting cluster here.'),
        'keywords': [
            'vice president kazakhstan appointed', 'vice presidency kazakhstan',
            'successor tokayev', 'tokayev health', 'elite purge kazakhstan',
            'nazarbayev family arrest', 'clan conflict kazakhstan',
            'security service purge kazakhstan', 'knb arrest', 'coup plot kazakhstan',
            'snap presidential election kazakhstan', 'tokayev to run again',
            'вице-президент казахстан', 'преемник токаева', 'досрочные выборы казахстан',
        ],
    },
]


# ============================================================
# GREEN LINES
# ============================================================

GREEN_LINES = [
    {
        'id': 'middle_corridor_milestone',
        'category': 'Middle Corridor Milestone',
        'severity': 4,
        'active_threshold': 2,
        'description': 'Trans-Caspian route capacity, volume, or investment milestone -- the hedge maturing',
        'keywords': [
            'middle corridor volume', 'trans-caspian route record', 'titr freight',
            'aktau port expansion', 'kuryk port', 'middle corridor investment',
            'global gateway kazakhstan', 'trans-caspian agreement',
            'middle corridor record', 'caspian shipping capacity',
            'средний коридор', 'транскаспийский маршрут',
        ],
    },
    {
        'id': 'export_diversification',
        'category': 'Export Route Diversification',
        'severity': 4,
        'active_threshold': 2,
        'description': 'Non-Russian export routes advancing -- BTC pipeline, Caspian tanker volumes, Druzhba alternatives',
        'keywords': [
            'baku tbilisi ceyhan kazakhstan', 'btc pipeline kazakh oil',
            'kazakh oil via azerbaijan', 'tanker route caspian oil',
            'export diversification kazakhstan', 'bypass russia oil kazakhstan',
            'alternative export route kazakhstan', 'kazmunaygas azerbaijan',
            'диверсификация экспорта казахстан',
        ],
    },
    {
        'id': 'west_minerals_anchor',
        'category': 'West / Critical-Minerals Track',
        'severity': 3,
        'active_threshold': 2,
        'description': 'C5+1, EU/US critical-minerals agreements, major Western energy investment',
        'keywords': [
            'c5+1', 'critical minerals kazakhstan', 'us kazakhstan minerals',
            'eu kazakhstan raw materials', 'tengizchevroil expansion', 'chevron kazakhstan',
            'kashagan investment', 'western investment kazakhstan',
            'rare earths kazakhstan', 'abraham accords kazakhstan',
        ],
    },
    {
        'id': 'turkic_integration',
        'category': 'Turkic Integration (OTS)',
        'severity': 2,
        'active_threshold': 2,
        'description': 'Organization of Turkic States cooperation, Ankara defence/drone ties -- a fourth, lighter pole',
        'keywords': [
            'organization of turkic states', 'turkic states summit', 'ots summit',
            'turkey kazakhstan drone', 'anka drone kazakhstan', 'baykar kazakhstan',
            'turkey kazakhstan defence', 'turkic council', 'turkic investment fund',
            'организация тюркских государств',
        ],
    },
    {
        'id': 'de_escalation_diplomacy',
        'category': 'Multi-Vector Diplomacy',
        'severity': 2,
        'active_threshold': 2,
        'description': 'Balanced diplomatic engagement across poles -- the hedge working as designed',
        'keywords': [
            'tokayev visit beijing', 'tokayev visit moscow', 'tokayev visit washington',
            'multi-vector foreign policy', 'balanced foreign policy kazakhstan',
            'kazakhstan mediation', 'astana talks', 'kazakhstan neutrality',
            'многовекторная политика',
        ],
    },
]


def _score_red_lines(scan_data):
    out = []
    for line in RED_LINES:
        hits = _check_keywords(scan_data, line['keywords'])
        status = ('BREACHED' if hits >= line['breach_threshold']
                  else 'APPROACHING' if hits >= 1 else 'QUIET')
        out.append({'id': line['id'], 'category': line['category'],
                    'severity': line['severity'], 'status': status,
                    'hits': hits, 'description': line['description']})
    return out


def _score_green_lines(scan_data):
    out = []
    for line in GREEN_LINES:
        hits = _check_keywords(scan_data, line['keywords'])
        status = ('ACTIVE' if hits >= line['active_threshold']
                  else 'SIGNALED' if hits >= 1 else 'QUIET')
        out.append({'id': line['id'], 'category': line['category'],
                    'severity': line['severity'], 'status': status,
                    'hits': hits, 'description': line['description']})
    return out


# ============================================================
# VECTOR 1 — MIDDLE CORRIDOR (corridor-vector family member #2)
# Inherits the portable schema minted for TRIPP. BRI and IMEC follow.
# ============================================================

CORRIDOR_PROGRESS_KEYWORDS = [
    'middle corridor', 'trans-caspian', 'titr', 'trans caspian international transport route',
    'aktau port', 'kuryk port', 'caspian freight', 'corridor volume record',
    'global gateway kazakhstan', 'container train china europe', 'khorgos',
    'rail freight kazakhstan europe', 'corridor investment', 'port capacity expansion',
    'средний коридор', 'транскаспийский', 'актау порт',
]

CORRIDOR_THREAT_KEYWORDS = [
    'corridor bottleneck', 'caspian shipping delay', 'port congestion aktau',
    'corridor capacity limit', 'russia pressure transit', 'transit tariff increase',
    'caspian water level', 'shipping constraint caspian', 'corridor unviable',
    'rail bottleneck kazakhstan', 'china rail restriction',
    'узкое место коридора',
]

_CORRIDOR_BLOCKERS = {
    'russia':    ['russia', 'moscow', 'kremlin', 'россия', 'москва'],
    'china':     ['china', 'beijing', 'китай', 'пекин'],
    'capacity':  ['bottleneck', 'congestion', 'capacity limit', 'water level', 'delay'],
}


def _score_middle_corridor(scan_data):
    progress = _check_keywords(scan_data, CORRIDOR_PROGRESS_KEYWORDS)
    threat = _check_keywords(scan_data, CORRIDOR_THREAT_KEYWORDS)

    blockers = []
    if threat:
        for actor, net in _CORRIDOR_BLOCKERS.items():
            if _check_keywords(scan_data, net):
                blockers.append(actor)

    if progress >= 6:
        stage, stage_name = 4, 'Scaling'
    elif progress >= 4:
        stage, stage_name = 3, 'Operational Growth'
    elif progress >= 2:
        stage, stage_name = 2, 'Active Build-Out'
    elif progress >= 1:
        stage, stage_name = 1, 'Rhetorical'
    else:
        stage, stage_name = 0, 'Dormant This Cycle'

    threat_band = ('high' if threat >= 4 else 'elevated' if threat >= 2
                   else 'simmering' if threat >= 1 else 'quiet')

    if stage >= 2 and threat_band in ('elevated', 'high'):
        status_read = (
            'Corridor build-out and constraint reporting are rising together -- consistent '
            'with the pattern seen when a bypass route matures fast enough to matter to the '
            'states it bypasses.')
    elif stage >= 2:
        status_read = (
            'Trans-Caspian build-out signals active with constraint rhetoric quiet -- '
            'consistent with an uncontested expansion window for the primary hedge against '
            'route dependency.')
    elif threat_band in ('elevated', 'high'):
        status_read = (
            'Constraint reporting active while build-out signals are quiet -- consistent with '
            'friction surfacing faster than progress.')
    else:
        status_read = 'Corridor axis quiet this cycle.'

    return {
        # -- portable corridor schema (shared with TRIPP; BRI/IMEC inherit) --
        'corridor_name':    'Middle Corridor / TITR',
        'class':            'trans_caspian',
        'progress_signals': progress,
        'threat_signals':   threat,
        'blocker_actors':   blockers,
        'status_read':      status_read,
        'ts':               datetime.now(timezone.utc).isoformat(),
        # -- vector extras --
        'stage':            stage,
        'stage_name':       stage_name,
        'threat_band':      threat_band,
    }


# ============================================================
# VECTOR 2 — RUSSIA LEVERS (tempo sensor, both directions honest)
# ============================================================

RU_LEVER_KEYWORDS = [
    'cpc pipeline', 'caspian pipeline consortium', 'novorossiysk', 'transit through russia',
    'russian railways kazakhstan', 'rail transit russia kazakhstan', 'eaeu kazakhstan',
    'eurasian economic union kazakhstan', 'gazprom kazakhstan', 'rosatom kazakhstan',
    'baikonur lease', 'russian language kazakhstan', 'csto kazakhstan',
    'ктк', 'евразийский союз казахстан', 'байконур',
]

RU_FRICTION_KEYWORDS = [
    'kazakhstan refuses recognize', 'tokayev refuses', 'kazakhstan distances from russia',
    'kazakhstan complies with sanctions', 'kazakhstan denies helping russia',
    'summons russian ambassador', 'kazakhstan protests russian statement',
    'kazakhstan will not recognize', 'moscow criticizes kazakhstan',
    'russian mp kazakhstan', 'kazakhstan russia tension',
    'казахстан не признает', 'казахстан россия напряженность',
]

RU_ALIGNMENT_KEYWORDS = [
    'kazakhstan russia cooperation', 'tokayev putin meeting', 'kazakhstan russia trade record',
    'joint venture russia kazakhstan', 'russia kazakhstan gas deal',
    'rosatom nuclear plant kazakhstan', 'kazakhstan russia union',
    'казахстан россия сотрудничество',
]


def _score_russia_levers(scan_data):
    lever_tempo = _check_keywords(scan_data, RU_LEVER_KEYWORDS)
    friction = _check_keywords(scan_data, RU_FRICTION_KEYWORDS)
    alignment = _check_keywords(scan_data, RU_ALIGNMENT_KEYWORDS)

    combined = lever_tempo + friction
    band = ('high' if combined >= 7 else 'elevated' if combined >= 4
            else 'simmering' if combined >= 1 else 'quiet')

    # Net polarity: friction vs alignment. Both are honest reads; the pole is
    # whichever the tape is actually carrying this cycle.
    net = friction - alignment
    if net >= 2:
        polarity = 'friction'
    elif net <= -2:
        polarity = 'alignment'
    else:
        polarity = 'balanced'

    parts = []
    if lever_tempo:
        parts.append(f'Lever-infrastructure coverage at {lever_tempo} signals '
                     '(CPC, rail, EAEU, Baikonur, Rosatom class).')
    if friction:
        parts.append(f'Friction reporting at {friction} signals.')
    if alignment:
        parts.append(f'Counter-direction honesty: cooperation reporting also active '
                     f'({alignment} signals). The sensor measures tempo both ways.')
    reading = ' '.join(parts) if parts else 'Russia-lever reporting quiet this cycle.'

    return {
        'band': band, 'lever_tempo': lever_tempo, 'friction_signals': friction,
        'alignment_signals': alignment, 'polarity': polarity, 'reading': reading,
    }


# ============================================================
# VECTOR 3 — CHINA DUAL-TRACK (feeds the FIRST China spoke)
# Elite pull and street friction are DIFFERENT signals with DIFFERENT
# polarities. A country where the government leans in while the street pushes
# back is a legible, emittable state -- and it is the normal state here.
# ============================================================

CN_ELITE_KEYWORDS = [
    'china kazakhstan trade', 'belt and road kazakhstan', 'bri kazakhstan',
    'xi jinping kazakhstan', 'tokayev beijing', 'china kazakhstan investment',
    'khorgos dry port', 'china kazakhstan pipeline', 'china kazakhstan rail',
    'sco summit', 'china central asia summit', 'chinese loan kazakhstan',
    'kazakhstan uranium china', 'china kazakhstan agreement',
    'китай казахстан сотрудничество', 'один пояс один путь',
]

CN_STREET_KEYWORDS = [
    'anti-china protest kazakhstan', 'sinophobia', 'land lease protest',
    'chinese factory protest', 'anti-chinese sentiment kazakhstan',
    'xinjiang kazakhs', 'ethnic kazakhs china camps', 'atajurt',
    'water dispute china', 'ili river', 'irtysh river china', 'lake balkhash',
    'debt trap kazakhstan', 'chinese workers protest kazakhstan',
    'антикитайские настроения', 'синьцзян казахи',
]


def _score_china_dual_track(scan_data):
    elite = _check_keywords(scan_data, CN_ELITE_KEYWORDS)
    street = _check_keywords(scan_data, CN_STREET_KEYWORDS)

    # spoke:china:kazakhstan relationship (Turkey-wheel vocabulary, per doctrine)
    if elite >= 3 and elite > street:
        relationship, level = 'alignment', 2
    elif elite >= 1 and elite > street:
        relationship, level = 'alignment', 1
    elif street > elite and street >= 2:
        relationship, level = 'friction', 2
    elif street >= 1:
        relationship, level = 'friction', 1
    else:
        relationship, level = 'alignment', 0

    if elite >= 2 and street >= 2:
        track = 'diverging'
        reading = (
            'Elite alignment and street friction are BOTH active -- the signature Kazakh '
            'condition: the government leans into Beijing while the street pushes back. '
            'Historically this gap widens before land, labour, or water disputes surface '
            'as protest.')
        top_signal = 'China dual-track diverging: elite alignment vs street friction both live'
    elif elite >= 2:
        track = 'elite_pull'
        reading = ('Elite-level China alignment leading the tape; street-friction signals quiet '
                   'this cycle.')
        top_signal = 'China elite alignment active (BRI / trade / energy class)'
    elif street >= 2:
        track = 'street_friction'
        reading = ('Street-level China friction leading the tape while elite alignment is quiet '
                   '-- consistent with a societal-grievance cycle rather than a state-level shift.')
        top_signal = 'China street friction active (land / labour / Xinjiang / water class)'
    else:
        track = 'quiet'
        reading = 'China axis quiet this cycle.'
        top_signal = 'Kazakhstan-China axis quiet this cycle'

    return {
        'track': track, 'elite_signals': elite, 'street_signals': street,
        'divergence': abs(elite - street),
        'relationship': relationship,   # feeds spoke:china:kazakhstan
        'level': level,
        'top_signal': top_signal,
        'reading': reading,
    }


# ============================================================
# VECTOR 4 — DOMESTIC TRIPWIRE (the January 2022 pattern class)
# ============================================================

DOMESTIC_KEYWORDS = [
    'protest kazakhstan', 'strike kazakhstan', 'rally kazakhstan', 'demonstration astana',
    'labour dispute kazakhstan', 'oil workers kazakhstan', 'zhanaozen', 'mangystau',
    'fuel price kazakhstan', 'utility tariff kazakhstan', 'lpg price',
    'arrest activist kazakhstan', 'crackdown kazakhstan', 'opposition kazakhstan',
    'протесты казахстан', 'забастовка казахстан', 'жанаозен',
]

PATTERN_CHAIN = [
    ('price_trigger', ['fuel price', 'lpg price', 'utility tariff', 'petrol price',
                       'tariff increase', 'цены на топливо']),
    ('labour_action', ['strike', 'oil workers', 'zhanaozen', 'mangystau', 'mangistau',
                       'забастовка']),
    ('metastasis',    ['nationwide', 'almaty', 'spread to', 'mass protests',
                       'state of emergency', 'по всей стране']),
]


def _score_domestic_tripwire(scan_data):
    tempo = _check_keywords(scan_data, DOMESTIC_KEYWORDS)

    # Pattern-chain progression: how far along the Jan-2022 precursor sequence
    # is the tape? This is PATTERN MEMORY -- it reports where the chain stands,
    # it does not forecast that the chain will complete.
    chain_stage = 0
    chain_links = []
    for name, kws in PATTERN_CHAIN:
        if _check_keywords(scan_data, kws):
            chain_stage += 1
            chain_links.append(name)

    band = ('high' if tempo >= 7 else 'elevated' if tempo >= 4
            else 'simmering' if tempo >= 1 else 'quiet')

    if chain_stage >= 3:
        reading = ('All three links of the January-2022 precursor chain are present in the same '
                   'cycle: price trigger, labour action, and geographic spread. In 2022 that '
                   'sequence ran from a fuel-price announcement to nationwide unrest in roughly '
                   'seventy-two hours. Pattern memory, not prediction.')
    elif chain_stage == 2:
        reading = ('Two links of the January-2022 precursor chain are present '
                   f"({', '.join(chain_links)}). The sequence has historically preceded "
                   'escalation; it has also frequently stopped here.')
    elif chain_stage == 1:
        reading = (f"One link of the January-2022 precursor chain is present ({chain_links[0]}). "
                   'Isolated; below the historical escalation pattern.')
    else:
        reading = 'Domestic tape quiet this cycle.'

    return {
        'band': band, 'tempo': tempo, 'chain_stage': chain_stage,
        'chain_links': chain_links, 'reading': reading,
    }


# ============================================================
# VECTOR 5 — HEDGING INTEGRITY (three-pole balance)
# The Kazakhstan instrument. NOT a drift axis: multi-vector balance IS the
# doctrine, so DIVERGENCE FROM EQUILIBRIUM is the signal -- whichever pole
# is pulling. A country leaning hard toward ANY single pole is the story.
# ============================================================

POLE_RUSSIA = [
    'russia kazakhstan', 'moscow astana', 'eaeu', 'csto', 'putin tokayev',
    'russian investment kazakhstan', 'rosatom', 'gazprom kazakhstan',
    'россия казахстан', 'одкб',
]
POLE_CHINA = [
    'china kazakhstan', 'beijing astana', 'belt and road', 'bri', 'sco',
    'xi jinping kazakhstan', 'chinese investment kazakhstan', 'khorgos',
    'китай казахстан',
]
POLE_WEST = [
    'us kazakhstan', 'eu kazakhstan', 'c5+1', 'chevron', 'tengizchevroil',
    'critical minerals', 'western investment kazakhstan', 'brussels astana',
    'washington astana', 'сша казахстан', 'ес казахстан',
]


def _score_hedging_integrity(scan_data):
    ru = _check_keywords(scan_data, POLE_RUSSIA)
    cn = _check_keywords(scan_data, POLE_CHINA)
    we = _check_keywords(scan_data, POLE_WEST)
    total = ru + cn + we

    poles = {'russia': ru, 'china': cn, 'west': we}

    if total == 0:
        return {
            'integrity': 'unread', 'poles': poles, 'total_signals': 0,
            'dominant_pole': None, 'dominance_pct': 0, 'divergence': 0,
            'reading': 'Insufficient pole signal this cycle to read the hedge. Absence stays honest.',
        }

    dominant = max(poles, key=lambda k: poles[k])
    dominance_pct = round((poles[dominant] / total) * 100)
    # Divergence from perfect three-way equilibrium (33/33/33).
    divergence = round(sum(abs((v / total) * 100 - 33.3) for v in poles.values()) / 2)

    if divergence >= 40:
        integrity = 'strained'
        reading = (f'Hedge reading STRAINED: the {dominant.upper()} pole carries {dominance_pct}% of '
                   'pole-signal this cycle, well outside the balance Astana sells to all three '
                   'capitals at once. Sustained single-pole dominance is the condition that has '
                   'historically preceded either a public rebalancing gesture or a concession.')
    elif divergence >= 22:
        integrity = 'tilting'
        reading = (f'Hedge reading TILTING toward the {dominant} pole ({dominance_pct}% of pole-signal). '
                   'Within historical range, but the tape is no longer balanced.')
    else:
        integrity = 'holding'
        reading = (f'Hedge reading HOLDING: pole-signal distributed across Russia/China/West with no '
                   f'single pole dominant ({dominant} leads at {dominance_pct}%). The multi-vector '
                   'doctrine is functioning as designed this cycle.')

    return {
        'integrity': integrity, 'poles': poles, 'total_signals': total,
        'dominant_pole': dominant, 'dominance_pct': dominance_pct,
        'divergence': divergence, 'reading': reading,
    }


# ============================================================
# VECTOR 6 — SUCCESSION (the VP is the tell)
# ============================================================

SUCCESSION_KEYWORDS = [
    'vice president kazakhstan', 'vice presidency', 'successor tokayev', 'succession kazakhstan',
    'tokayev term', 'snap election kazakhstan', 'presidential election kazakhstan',
    'kurultai election', 'tokayev run again', 'constitutional court kazakhstan term',
    'ashimbayev', 'tasmagambetov', 'karin kazakhstan',
    'вице-президент', 'преемник', 'досрочные выборы',
]


def _score_succession(scan_data):
    hits = _check_keywords(scan_data, SUCCESSION_KEYWORDS)
    if hits >= 4:
        band = 'active'
        reading = ('Succession machinery is live on the tape. The July 2026 constitution created a '
                   'PRESIDENTIALLY APPOINTED vice presidency, and the Constitutional Court has ruled '
                   "Tokayev's current term does not count against the single-term limit. The VP "
                   'appointment is the single highest-value discrete signal in the country -- whoever '
                   'receives it is the anointed successor.')
    elif hits >= 1:
        band = 'simmering'
        reading = ('Succession chatter present below cluster threshold. Watch the vice-presidential '
                   'appointment: it is the appointment that names the heir.')
    else:
        band = 'quiet'
        reading = 'Succession tape quiet this cycle.'
    return {'band': band, 'hits': hits, 'reading': reading}


# ============================================================
# VECTOR 7 — TURKIC INTEGRATION (light, fourth pole)
# ============================================================

TURKIC_KEYWORDS = [
    'organization of turkic states', 'turkic states summit', 'turkic council',
    'turkey kazakhstan', 'ankara astana', 'turkish drone kazakhstan', 'anka kazakhstan',
    'baykar kazakhstan', 'turkic investment fund', 'turkey kazakhstan defence',
    'организация тюркских государств', 'турция казахстан',
]


def _score_turkic(scan_data):
    hits = _check_keywords(scan_data, TURKIC_KEYWORDS)
    band = 'active' if hits >= 3 else 'simmering' if hits >= 1 else 'quiet'
    reading = ({
        'active': ('Turkic-integration signals active (OTS / Ankara defence-industrial class) -- a '
                   'fourth, lighter pole that Astana uses to dilute the big-three hedge.'),
        'simmering': 'Scattered Turkic-integration signals; below cluster threshold.',
        'quiet': 'Turkic axis quiet this cycle.',
    })[band]
    return {'band': band, 'hits': hits, 'reading': reading}


# ============================================================
# COMMODITY CONVERGENCE (the compound read — CONVERGENCE-GATED)
#
# Kazakhstan's commodity pressure is STRUCTURAL, not episodic: it is the
# world's #1 uranium producer and a top-tier oil exporter every single day.
# Feeding that into the theatre score would pin the country at 'surge'
# permanently and the alarm would stop meaning anything. A sensor that always
# says SURGE says nothing.
#
# So the commodity vector fires ONLY on convergence: commodity pressure
# co-occurring with a LIVE pressure vector. Commodity surge alone is the
# commodity card's job. Commodity surge + Russia lever tempo is a story about
# a chokepoint being SQUEEZED -- and that is what belongs in the BLUF and GPI.
#
# The structural fact underneath: Kazakh crude exits via CPC through Russia,
# and Kazakh uranium transits Russia too. The commodity power is real; the
# commodity ROUTES belong to the neighbours being hedged against.
# ============================================================

def _score_commodity_convergence(commodity_data, russia, corridor, domestic, china):
    if not commodity_data or not commodity_data.get('success', True):
        return {'active': False, 'gate': 'no_data', 'pressure': 0, 'alert': 'unknown',
                'commodities': [], 'convergence_with': [],
                'reading': 'Commodity proxy returned no data this cycle. Absence stays honest.'}

    pressure = commodity_data.get('commodity_pressure', 0) or 0
    alert = (commodity_data.get('alert_level') or 'normal').lower()
    summaries = commodity_data.get('commodity_summaries') or []
    names = [c.get('commodity') or c.get('name') for c in summaries][:6]
    names = [n for n in names if n]

    # The GATE: which pressure vectors are live RIGHT NOW?
    convergence_with = []
    if russia.get('band') in ('elevated', 'high'):
        convergence_with.append('russia_levers')
    if corridor.get('threat_band') in ('elevated', 'high'):
        convergence_with.append('corridor_threat')
    if domestic.get('band') in ('elevated', 'high') or domestic.get('chain_stage', 0) >= 2:
        convergence_with.append('domestic_tripwire')
    if china.get('track') == 'diverging':
        convergence_with.append('china_divergence')

    commodity_live = (alert in ('elevated', 'high', 'surge', 'critical')) or pressure >= 60

    if not commodity_live:
        return {'active': False, 'gate': 'commodity_quiet', 'pressure': pressure,
                'alert': alert, 'commodities': names, 'convergence_with': [],
                'reading': 'Commodity pressure below threshold this cycle.'}

    if not convergence_with:
        # Commodity hot, everything else quiet -> STRUCTURAL, not a signal.
        return {
            'active': False, 'gate': 'structural_only', 'pressure': pressure,
            'alert': alert, 'commodities': names, 'convergence_with': [],
            'reading': (
                f'Commodity pressure reads {alert.upper()} ({pressure:.0f}) but no pressure vector '
                'is live to converge with. This is Kazakhstan\'s STRUCTURAL exposure -- it is the '
                "world's largest uranium producer and a top-tier oil exporter every day of the "
                'year. Reported, not escalated: a commodity reading that is always high is not an '
                'alarm. See the commodity card for the standing exposure.'),
        }

    # CONVERGENCE. This is the read the platform exists to produce.
    vec_labels = {
        'russia_levers':     'Russia lever tempo',
        'corridor_threat':   'corridor constraint rhetoric',
        'domestic_tripwire': 'domestic tripwire chain',
        'china_divergence':  'China elite/street divergence',
    }
    live = ', '.join(vec_labels[v] for v in convergence_with)
    reading = (
        f'Commodity pressure ({alert.upper()}, {pressure:.0f}) is co-occurring with {live}. '
        'This is the convergence that matters: Kazakh crude exits through Russian territory via '
        'CPC, and Kazakh uranium transits Russia as well -- the commodity power is real, the '
        'commodity ROUTES belong to the neighbours being hedged against. Commodity pressure '
        'rising while route-holders are simultaneously active is the pattern consistent with a '
        'chokepoint being tested rather than merely existing.')

    return {
        'active': True, 'gate': 'converged', 'pressure': pressure, 'alert': alert,
        'commodities': names, 'convergence_with': convergence_with, 'reading': reading,
    }


# ============================================================
# MULTIPLIERS — never standalone signals (Black Swan discipline)
# ============================================================

ELECTION_CLOCK_KEYWORDS = [
    'kurultai election', 'parliamentary election kazakhstan', 'snap election kazakhstan',
    'presidential election kazakhstan', 'election campaign kazakhstan', 'maslikhat election',
    'august 23', 'выборы казахстан', 'курултай выборы',
]


def _election_clock_multiplier(scan_data, red_lines):
    """Kurultai elections Aug 23 2026; snap-presidential chatter live after the
    Jul 7 2026 Constitutional Court ruling. AMPLIFIER ONLY -- an election during
    a quiet period contributes nothing."""
    hits = _check_keywords(scan_data, ELECTION_CLOCK_KEYWORDS)
    stack_active = any(r['status'] != 'QUIET' for r in red_lines)
    if hits >= 2 and stack_active:
        return {'active': True, 'multiplier': 0.20, 'hits': hits,
                'reading': 'Election-window conditions amplifying an active signal stack.'}
    if hits >= 1 and stack_active:
        return {'active': True, 'multiplier': 0.10, 'hits': hits,
                'reading': 'Early election-clock chatter amplifying an active stack.'}
    return {'active': False, 'multiplier': 0.0, 'hits': hits, 'reading': ''}


def _winter_calendar_multiplier(red_lines, domestic):
    """THE Kazakhstan calendar multiplier. Bloody January began with a fuel-price
    change on January 1st, in the coldest weeks of a very cold country. Heating
    season is when a tariff decision stops being an economic story and becomes a
    survival story. AMPLIFIER ONLY -- winter with a quiet tape contributes zero."""
    month = datetime.now(timezone.utc).month
    in_heating_season = month in (11, 12, 1, 2, 3)
    deep_winter = month in (12, 1, 2)

    tripwire_live = (domestic.get('chain_stage', 0) >= 1
                     or domestic.get('band') in ('elevated', 'high')
                     or any(r['id'] in ('fuel_price_unrest', 'mass_unrest')
                            and r['status'] != 'QUIET' for r in red_lines))

    if not in_heating_season or not tripwire_live:
        return {'active': False, 'multiplier': 0.0, 'in_heating_season': in_heating_season,
                'reading': ''}
    mult = 0.25 if deep_winter else 0.15
    return {
        'active': True, 'multiplier': mult, 'in_heating_season': True,
        'reading': ('Heating-season conditions amplifying a live domestic tripwire. The January '
                    '2022 sequence began with a fuel-price change on January 1st -- in this '
                    'country, winter is when a tariff decision becomes a survival question.'),
    }


# ============================================================
# SO WHAT — the analyst voice
# ============================================================

def _build_so_what(red_lines, green_lines, corridor, russia, china, domestic,
                   hedge, succession, turkic, commodity, elec_clock, winter):
    breached = [r for r in red_lines if r['status'] == 'BREACHED']
    approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
    active_green = [g for g in green_lines if g['status'] == 'ACTIVE']

    if breached and any(r['severity'] >= 5 for r in breached):
        priority = 'critical'
    elif breached:
        priority = 'high'
    elif (approaching or hedge['integrity'] == 'strained'
          or domestic.get('chain_stage', 0) >= 2 or commodity.get('active')):
        priority = 'elevated'
    else:
        priority = 'normal'

    if breached:
        cats = ', '.join(sorted({r['category'] for r in breached}))
        scenario = f'Red-line breach: {cats}'
    elif domestic.get('chain_stage', 0) >= 2:
        scenario = 'Domestic precursor chain active (Jan-2022 pattern class)'
    elif hedge['integrity'] == 'strained':
        scenario = f"Hedge strained -- {hedge['dominant_pole']} pole dominant"
    elif approaching:
        cats = ', '.join(sorted({r['category'] for r in approaching}))
        scenario = f'Pressure approaching: {cats}'
    else:
        scenario = 'Baseline -- multi-vector hedge holding'

    parts = [
        'The Kazakhstan read is a hedging-integrity question, not a drift question: multi-vector '
        'balance IS the state doctrine, so the sensor asks whether the hedge is holding, not which '
        'way the country is turning.'
    ]
    parts.append(hedge['reading'])
    if corridor['stage'] >= 1 or corridor['threat_band'] != 'quiet':
        parts.append(f"Middle Corridor: {corridor['stage_name']} with constraint rhetoric "
                     f"{corridor['threat_band']}"
                     + (f" ({', '.join(corridor['blocker_actors'])})" if corridor['blocker_actors'] else '')
                     + '.')
    if russia['band'] != 'quiet':
        parts.append(f"Russia levers: {russia['band']} / {russia['polarity']}. {russia['reading']}")
    if china['track'] != 'quiet':
        parts.append(f"China: {china['reading']}")
    if domestic['chain_stage'] >= 1 or domestic['band'] != 'quiet':
        parts.append(domestic['reading'])
    if succession['band'] != 'quiet':
        parts.append(succession['reading'])
    if turkic['band'] == 'active':
        parts.append(turkic['reading'])
    if commodity.get('active'):
        parts.append(commodity['reading'])
    if winter.get('active'):
        parts.append(winter['reading'])
    if elec_clock.get('active'):
        parts.append(elec_clock['reading'])
    if active_green:
        parts.append('De-escalation markers active: '
                     + ', '.join(g['category'] for g in active_green) + '.')
    if (not breached and not approaching and not active_green
            and russia['band'] == 'quiet' and china['track'] == 'quiet'
            and corridor['stage'] == 0):
        parts.append('All vectors quiet this cycle. Silence is a valid analytical output; '
                     'manufactured signal is not.')

    return {
        'scenario': scenario, 'priority': priority, 'assessment': ' '.join(parts),
        'situation': scenario, 'breached_count': len(breached),
        'approaching_count': len(approaching), 'active_green_count': len(active_green),
        'disclaimer': CONVERGENCE_DISCLAIMER,
    }


# ============================================================
# TOP SIGNALS
# ============================================================

def _build_top_signals(red_lines, green_lines, corridor, russia, china, domestic,
                       hedge, succession, turkic, commodity):
    signals = []

    for r in red_lines:
        if r['status'] == 'BREACHED':
            signals.append({
                'priority': 1, 'category': r['id'],
                'short_text': f"RED LINE BREACHED: {r['category']} ({r['hits']} signals)",
                'long_text': f"{r['description']} {r['hits']} matched signals this cycle -- "
                             'a level consistent with the tripwire condition being live.',
                'pressure_type': 'kinetic' if r['id'] in ('mass_unrest', 'fuel_price_unrest')
                                 else 'economic' if r['id'] in ('cpc_disruption', 'sanctions_secondary')
                                 else 'diplomatic',
            })
    for r in red_lines:
        if r['status'] == 'APPROACHING':
            signals.append({
                'priority': 2, 'category': r['id'],
                'short_text': f"Approaching: {r['category']}",
                'long_text': f"{r['description']} Early signals present ({r['hits']}), below "
                             'breach threshold.',
                'pressure_type': 'economic' if r['id'] in ('cpc_disruption', 'sanctions_secondary')
                                 else 'diplomatic',
            })

    # COMMODITY CONVERGENCE — fires only when gated open. The compound read.
    if commodity.get('active'):
        signals.append({
            'priority': 1,
            'category': 'commodity_convergence',
            'short_text': (f"CONVERGENCE: commodity {commodity['alert'].upper()} "
                           f"({commodity['pressure']:.0f}) + "
                           f"{len(commodity['convergence_with'])} live pressure vector(s)"),
            'long_text': commodity['reading'],
            'pressure_type': 'economic',
        })

    if domestic.get('chain_stage', 0) >= 2:
        signals.append({
            'priority': 1 if domestic['chain_stage'] >= 3 else 2,
            'category': 'domestic_tripwire',
            'short_text': f"Jan-2022 precursor chain at stage {domestic['chain_stage']}/3 "
                          f"({', '.join(domestic['chain_links'])})",
            'long_text': domestic['reading'],
            'pressure_type': 'kinetic',
        })

    if hedge['integrity'] in ('strained', 'tilting'):
        signals.append({
            'priority': 2 if hedge['integrity'] == 'strained' else 3,
            'category': 'hedging_integrity',
            'short_text': (f"Hedge {hedge['integrity'].upper()}: {hedge['dominant_pole']} pole "
                           f"{hedge['dominance_pct']}% of pole-signal"),
            'long_text': hedge['reading'],
            'pressure_type': 'diplomatic',
        })

    if russia['band'] in ('elevated', 'high'):
        signals.append({
            'priority': 2, 'category': 'russia_levers',
            'short_text': f"Russia levers {russia['band']} / {russia['polarity']} "
                          f"({russia['lever_tempo']} lever signals)",
            'long_text': russia['reading'],
            'pressure_type': 'economic',
        })

    if china['track'] == 'diverging':
        signals.append({
            'priority': 2, 'category': 'china_dual_track',
            'short_text': china['top_signal'],
            'long_text': china['reading'],
            'pressure_type': 'diplomatic',
        })
    elif china['track'] in ('elite_pull', 'street_friction'):
        signals.append({
            'priority': 3, 'category': 'china_dual_track',
            'short_text': china['top_signal'],
            'long_text': china['reading'],
            'pressure_type': 'diplomatic',
        })

    if corridor['stage'] >= 2 or corridor['threat_band'] in ('elevated', 'high'):
        signals.append({
            'priority': 2 if corridor['threat_band'] in ('elevated', 'high') else 3,
            'category': 'middle_corridor',
            'short_text': f"Middle Corridor: {corridor['stage_name']} / constraints "
                          f"{corridor['threat_band']}",
            'long_text': corridor['status_read'],
            'pressure_type': 'economic',
        })

    if succession['band'] == 'active':
        signals.append({
            'priority': 2, 'category': 'succession',
            'short_text': f"Succession machinery active ({succession['hits']} signals)",
            'long_text': succession['reading'],
            'pressure_type': 'diplomatic',
        })

    for g in green_lines:
        if g['status'] == 'ACTIVE':
            signals.append({
                'priority': 3, 'category': g['id'],
                'short_text': f"GREEN LINE: {g['category']} active ({g['hits']} signals)",
                'long_text': f"{g['description']}. De-escalatory marker active this cycle.",
                'pressure_type': 'diplomatic',
            })

    if turkic['band'] == 'active':
        signals.append({
            'priority': 3, 'category': 'turkic_integration',
            'short_text': f"Turkic integration active ({turkic['hits']} signals)",
            'long_text': turkic['reading'],
            'pressure_type': 'diplomatic',
        })

    signals.sort(key=lambda s: s['priority'])
    return signals[:8]


# ============================================================
# FINGERPRINT SLICES
# ============================================================

def _build_fingerprints(corridor, russia, china, domestic, hedge, succession,
                        turkic, commodity):
    return {
        'hedging_integrity': {
            'integrity':     hedge['integrity'],
            'dominant_pole': hedge['dominant_pole'],
            'divergence':    hedge['divergence'],
            'poles':         hedge['poles'],
        },
        'middle_corridor': {
            'corridor_name':  corridor['corridor_name'],
            'class':          corridor['class'],
            'stage':          corridor['stage'],
            'threat_band':    corridor['threat_band'],
            'blocker_actors': corridor['blocker_actors'],
        },
        'russia_levers': {
            'band':        russia['band'],
            'polarity':    russia['polarity'],
            'lever_tempo': russia['lever_tempo'],
        },
        'china_spoke': {
            'level':         china['level'],
            'relationship':  china['relationship'],
            'track':         china['track'],
            'top_signal':    china['top_signal'],
            'elite_signals': china['elite_signals'],
            'street_signals': china['street_signals'],
        },
        'domestic_tripwire': {
            'band':        domestic['band'],
            'chain_stage': domestic['chain_stage'],
            'chain_links': domestic['chain_links'],
        },
        'succession': {
            'band': succession['band'],
            'hits': succession['hits'],
        },
        'turkic_integration': {
            'band': turkic['band'],
        },
        'commodity_convergence': {
            'active':           commodity.get('active', False),
            'gate':             commodity.get('gate'),
            'alert':            commodity.get('alert'),
            'pressure':         commodity.get('pressure', 0),
            'convergence_with': commodity.get('convergence_with', []),
        },
    }


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def interpret_signals(scan_data):
    """Main entry point. Called from rhetoric_tracker_kazakhstan.py.
    scan_data may carry 'commodity_data' (from commodity_proxy_europe
    get_commodity_data) -- read server-side so the commodity read reaches the
    BLUF and GPI, not just the page."""
    try:
        red_lines = _score_red_lines(scan_data)
        green_lines = _score_green_lines(scan_data)

        corridor   = _score_middle_corridor(scan_data)
        russia     = _score_russia_levers(scan_data)
        china      = _score_china_dual_track(scan_data)
        domestic   = _score_domestic_tripwire(scan_data)
        hedge      = _score_hedging_integrity(scan_data)
        succession = _score_succession(scan_data)
        turkic     = _score_turkic(scan_data)

        commodity = _score_commodity_convergence(
            scan_data.get('commodity_data'), russia, corridor, domestic, china)

        elec_clock = _election_clock_multiplier(scan_data, red_lines)
        winter     = _winter_calendar_multiplier(red_lines, domestic)

        so_what = _build_so_what(red_lines, green_lines, corridor, russia, china,
                                 domestic, hedge, succession, turkic, commodity,
                                 elec_clock, winter)
        top_signals = _build_top_signals(red_lines, green_lines, corridor, russia,
                                         china, domestic, hedge, succession, turkic,
                                         commodity)
        fingerprints = _build_fingerprints(corridor, russia, china, domestic, hedge,
                                           succession, turkic, commodity)

        breached = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']

        # Composite modifier. Green lines subtract (capped -25, canon).
        # Commodity NEVER contributes on its own -- only via the convergence gate.
        green_score = sum(g['severity'] for g in active_gl)
        red_load = (sum(r['severity'] for r in breached) * 2
                    + sum(r['severity'] for r in approaching))
        if commodity.get('active'):
            red_load += 4   # convergence bonus ONLY when the gate opened
        composite = red_load - min(25, green_score * 2)
        composite = int(round(composite
                              * (1.0 + elec_clock['multiplier'] + winter['multiplier'])))

        return {
            'so_what':     so_what,
            'top_signals': top_signals,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in red_lines
                                          if r['status'] != 'QUIET'), default=0),
            },
            'green_lines': {
                'triggered':      green_lines,
                'active_count':   len(active_gl),
                'signaled_count': len([g for g in green_lines if g['status'] == 'SIGNALED']),
                'diplomatic_score': green_score,
            },
            'middle_corridor':       corridor,
            'russia_levers':         russia,
            'china_dual_track':      china,
            'domestic_tripwire':     domestic,
            'hedging_integrity':     hedge,
            'succession':            succession,
            'turkic_integration':    turkic,
            'commodity_convergence': commodity,
            'election_clock':        elec_clock,
            'winter_calendar':       winter,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier':    composite,
            'interpreter_version':   INTERPRETER_VERSION,
            'interpreted_at':        datetime.now(timezone.utc).isoformat(),
            'disclaimer':            CONVERGENCE_DISCLAIMER,
        }

    except Exception as e:
        print(f'[Kazakhstan Interpreter] Error: {str(e)[:140]}')
        return {
            'so_what': {
                'scenario': 'Interpreter error', 'priority': 'normal',
                'assessment': str(e)[:200], 'situation': 'Interpreter error',
                'breached_count': 0, 'approaching_count': 0, 'active_green_count': 0,
                'disclaimer': CONVERGENCE_DISCLAIMER,
            },
            'top_signals': [],
            'red_lines':   {'triggered': [], 'breached_count': 0, 'approaching_count': 0,
                            'highest_severity': 0},
            'green_lines': {'triggered': [], 'active_count': 0, 'signaled_count': 0,
                            'diplomatic_score': 0},
            'middle_corridor':   {'corridor_name': 'Middle Corridor / TITR',
                                  'class': 'trans_caspian', 'stage': 0,
                                  'stage_name': 'Unknown', 'threat_band': 'quiet',
                                  'blocker_actors': [], 'progress_signals': 0,
                                  'threat_signals': 0, 'status_read': ''},
            'russia_levers':     {'band': 'quiet', 'polarity': 'balanced', 'lever_tempo': 0,
                                  'friction_signals': 0, 'alignment_signals': 0, 'reading': ''},
            'china_dual_track':  {'track': 'quiet', 'relationship': 'alignment', 'level': 0,
                                  'elite_signals': 0, 'street_signals': 0, 'divergence': 0,
                                  'top_signal': '', 'reading': ''},
            'domestic_tripwire': {'band': 'quiet', 'tempo': 0, 'chain_stage': 0,
                                  'chain_links': [], 'reading': ''},
            'hedging_integrity': {'integrity': 'unread', 'poles': {}, 'total_signals': 0,
                                  'dominant_pole': None, 'dominance_pct': 0,
                                  'divergence': 0, 'reading': ''},
            'succession':        {'band': 'quiet', 'hits': 0, 'reading': ''},
            'turkic_integration': {'band': 'quiet', 'hits': 0, 'reading': ''},
            'commodity_convergence': {'active': False, 'gate': 'error', 'pressure': 0,
                                      'alert': 'unknown', 'commodities': [],
                                      'convergence_with': [], 'reading': ''},
            'election_clock':    {'active': False, 'multiplier': 0.0, 'hits': 0, 'reading': ''},
            'winter_calendar':   {'active': False, 'multiplier': 0.0,
                                  'in_heating_season': False, 'reading': ''},
            'cross_theater_fingerprints': {},
            'composite_modifier': 0,
            'interpreter_version': INTERPRETER_VERSION,
            'error': str(e)[:200],
        }
