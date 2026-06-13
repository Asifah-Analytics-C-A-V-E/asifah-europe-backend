"""
=======================================================================
  ASIFAH ANALYTICS -- TURKEY SIGNAL INTERPRETER
  v1.0.0 (Jun 11 2026)
=======================================================================

Analytical layer for rhetoric_tracker_turkey.py. The platform's FIRST
SWING-STATE interpreter: Turkey is neither an outbound-coercion tracker
(China pattern) nor an inbound-rhetoric tracker (Cuba/Greenland pattern)
nor an absorber (India pattern). Ankara's doctrine is strategic
autonomy -- NATO membership, S-400s, Russia energy, and Gulf finance
held simultaneously. "Turkey is Turkey."

THE CORE ANALYTICAL PRODUCTS:

1. DUAL ALIGNMENT INDICES -- a NATO-anchor index and a strategic-
   autonomy index scored in parallel. Because the baseline is "high on
   both," the signal is DECOUPLING: autonomy rising while Alliance
   cooperation falls. Divergence, not membership, is the metric.

2. LEBANON-VECTOR PLAYBOOK LADDER -- Turkey's documented expansion
   pattern is invitation engineering, never invasion-by-surprise:
     L1 perimeter rhetoric -> L2 soft-power penetration (Diyanet/TIKA)
     -> L3 economic-strategic stakes (ports, TPAO, drones)
     -> L4 defense cooperation MOU (the Libya-model tripwire)
     -> L5 presence by invitation / "buffer zone" framing.
   Precedents: N. Cyprus 1974, Syria ops 2016-19, Libya 2020, Somalia,
   Iraq (Bashiqa), Balkans soft power.

3. SYRIA AS LEAD INDICATOR -- Turkey already has troops, proxies, and
   economic depth in northern Syria. Sharp rises in Syria rhetoric have
   historically preceded broader regional ambition; Syria escalation
   signals are weighted as the leading edge of the Levant vector.

4. MIRROR-IMAGING FRICTION INDEX -- Israel claims Turkey is taking over
   Lebanon; Ankara claims Israel's operations in Syria and Lebanon
   "threaten Turkey too" (Erdogan, Jun 10 2026). BOTH rhetorics
   escalating in sync is itself the signal. We read both, attribute
   both, and the reader completes the inference.

5. CONSTITUTIONAL-CLOCK MULTIPLIER -- Erdogan's term math (~2028)
   requires a new constitution or early elections to run again.
   Election proximity is a CALENDAR MULTIPLIER on active signal stacks,
   never a standalone signal (Black Swan discipline).

DOCTRINE: estimative voice only. "Consistent with," "historically
precedes," "likely indicates." No probabilities, no dates, no "will."
Convergence, not prediction. The reader completes the inference.

Consumed by: rhetoric_tracker_turkey.py via interpret_signals(scan_data).
Cross-theater fingerprints written for Lebanon / Israel / Syria trackers
(ME backend, shared Redis) and both ME + Europe regional BLUFs.
=======================================================================
"""

from datetime import datetime, timezone

INTERPRETER_VERSION = '1.0.0'

CONVERGENCE_DISCLAIMER = (
    'This composite is a CONVERGENCE indicator, NOT a probability of '
    'action. Active signals indicate the named conditions are present; '
    'they do not predict whether or when any action will occur.'
)


# ============================================================
# RUMINT -- concept-seeding / posture-probing detection
# ------------------------------------------------------------
# A lightweight read that rides ALONGSIDE the threat band and never
# inflates it. Detects trial-balloon behavior: expansionist framing
# floated to gauge regional reception, as a possible precursor to a
# posture shift. Bands on an escalating-OBSERVABLE ladder --
#   Watch -> Active -> Corroborated
# -- where each rung is gated by a NEW present-tense signal, not a
# forecast. 'off' = no pill (absence stays honest).
#
# PORTABILITY: only the COUNTRY-SPECIFIC constants below change per
# country (Greenland, Cuba, ...). _band_rumint() / _score_rumint() /
# _count_terms_in_reception() are generic and clone as-is.
# ============================================================

# --- COUNTRY-SPECIFIC (Turkey: Ottoman-restoration framing) ---
RUMINT_SUBJECT = 'Ottoman-restoration framing'
RUMINT_EXPANSION_KEYWORDS = [
    # EN
    'neo-ottoman', 'neo ottoman', 'neo-ottomanism', 'ottomanism',
    'ottoman revival', 'restore the ottoman', 'ottoman empire',
    'ottoman heritage', 'mavi vatan', 'blue homeland', 'misak-i milli',
    'national pact', 'caliphate', 'ummah leader',
    'leader of the muslim world', 'protector of jerusalem',
    'guardian of jerusalem', 'defender of al-quds',
    'turkish sphere of influence', 'turkish expansionism',
    'turkey expansionism', 'turkey regional power', 'turkey imperial',
    # TR
    'osmanli', 'osmanlı', 'yeni osmanli', 'yeni osmanlı',
    'osmanli mirasi', 'misak-ı millî', 'halifelik', 'hilafet',
    # HE / AR (native script -- functional match against native titles)
    'עות׳מאני',
    'התפשטות טורקית',
    'العثمانية الجديدة',
    'عثماني',
    'التوسع التركي',
    'النفوذ التركي',
]
RUMINT_TARGETS = [
    'lebanon', 'syria', 'aleppo', 'idlib', 'mosul', 'kirkuk', 'iraq',
    'jerusalem', 'al-aqsa', 'al aqsa', 'gaza',
    'lubnan', 'lübnan', 'suriye', 'gazze',
    'לבנון', 'סוריה',
    'لبنان', 'سوريا',
    'حلب', 'الموصل',
]
RUMINT_CORROBORATION_KEYWORDS = [
    'buffer zone', 'safe zone', 'guvenli bolge', 'güvenli bölge',
    'tampon bolge', 'turkish operation', 'turkish military operation',
    'turkish forces', 'turkish troops', 'cross-border operation',
    'tsk operation', 'deconfliction',
]
RUMINT_RECEPTION_VENUES = ['r/lebanon', 'r/syria', 'r/forbiddenbromance']
RUMINT_FRAMING_FLOOR = 3   # distinct expansion terms below which we stay silent


# --- GENERIC (portable: identical across all RUMINT-enabled countries) ---
def _band_rumint(framing, specificity, reception, corroboration, subject):
    """Band the RUMINT read on the escalating-observable ladder. Each rung
    is gated by a NEW present-tense signal, never a forecast. 'off' returns
    an inactive payload so the frontend shows no pill (absence stays honest)."""
    if framing < RUMINT_FRAMING_FLOOR:
        return {'active': False, 'band': 'off', 'label': '', 'driver': '',
                'framing': framing, 'specificity': specificity,
                'reception': reception, 'corroboration': corroboration}
    if specificity >= 1 and corroboration >= 1:
        band, label = 'corroborated', 'Corroborated'
        driver = (subject + ' is target-specific and now matched by independent '
                  'posture/operational signals -- the lonely rhetoric has company. '
                  'Consistent with concept-seeding that historically precedes a '
                  'posture shift; reader completes the inference.')
    elif specificity >= 1 or reception >= 1:
        band, label = 'active', 'Active'
        echo = ' and echoing in regional venues' if reception >= 1 else ''
        driver = (subject + ' is target-specific' + echo + ' -- concept-seeding '
                  'underway. Consistent with trial-balloon behavior; reader '
                  'completes the inference.')
    else:
        band, label = 'watch', 'Watch'
        driver = (subject + ' is present but not yet target-specific. Baseline '
                  'concept-seeding; watching for specificity drift.')
    return {'active': True, 'band': band, 'label': label, 'driver': driver,
            'framing': framing, 'specificity': specificity,
            'reception': reception, 'corroboration': corroboration}


def _count_terms_in_reception(scan_data, keywords, venues):
    """Distinct keyword count restricted to reddit signals whose source is a
    reception venue -- the 'is the target audience reacting?' read."""
    if not keywords:
        return 0
    parts = []
    for sig in (scan_data.get('reddit_signals') or []):
        if (sig.get('source') or '') in venues:
            parts.append((sig.get('text') or sig.get('title') or '').lower())
    corpus = ' | '.join(parts)
    if not corpus:
        return 0
    return sum(1 for kw in keywords if kw.lower() in corpus)


def _score_rumint(scan_data):
    """Compute the RUMINT read from the captured corpus. Framing / specificity /
    corroboration use the full corpus (_check_keywords); reception is venue-
    filtered. Counts are distinct-term counts -- a volume proxy, never a
    probability. Short-circuits when framing is below the floor."""
    framing = _check_keywords(scan_data, RUMINT_EXPANSION_KEYWORDS)
    if framing < RUMINT_FRAMING_FLOOR:
        return _band_rumint(framing, 0, 0, 0, RUMINT_SUBJECT)
    specificity   = _check_keywords(scan_data, RUMINT_TARGETS)
    corroboration = _check_keywords(scan_data, RUMINT_CORROBORATION_KEYWORDS)
    reception     = _count_terms_in_reception(
        scan_data, RUMINT_EXPANSION_KEYWORDS + RUMINT_TARGETS,
        RUMINT_RECEPTION_VENUES)
    return _band_rumint(framing, specificity, reception, corroboration,
                        RUMINT_SUBJECT)


# ============================================================
# RED LINES -- escalation / divergence tripwires
# ============================================================

RED_LINES = [
    {
        'id':       'buffer_zone_levant',
        'category': 'Kinetic Precursor',
        'title':    'Buffer-Zone Framing Toward Lebanon / Syria / Iran',
        'severity': 5,
        'description':
            'Turkish official or military-adjacent language framing a '
            '"buffer zone," "safe zone," or "security corridor" in '
            'Lebanon, expanded Syria sectors, or Iran. This phrasing is '
            'Turkey\'s signature pre-intervention tell -- it preceded '
            'every Syria operation (Euphrates Shield, Olive Branch, '
            'Peace Spring). March 2026: TSK reportedly discussed an '
            'Iran buffer zone in a collapse scenario (denied by MSB). '
            'Language of this class is consistent with operational '
            'planning conditions, not proof of intent.',
        'triggers_breached': [
            'buffer zone lebanon', 'safe zone lebanon', 'security corridor lebanon',
            'buffer zone iran', 'safe zone iran', 'turkish buffer zone',
            'turkey safe zone syria expansion', 'new buffer zone syria',
            'guvenli bolge lubnan', 'tampon bolge',
        ],
        'triggers_approaching': [
            'buffer zone', 'safe zone proposal', 'security corridor',
            'turkey security zone', 'protective zone turkey',
            'guvenli bolge',
        ],
    },
    {
        'id':       'defense_mou_lebanon',
        'category': 'Levant Vector',
        'title':    'Turkey-Lebanon Defense Cooperation Agreement',
        'severity': 5,
        'description':
            'Defense cooperation MOU, military training agreement, or '
            'security memorandum between Ankara and Beirut -- the '
            'Libya-model tripwire (the 2019 Tripoli MOU preceded '
            'Turkish deployment by invitation within months). The single '
            'clearest L4 rung on the Lebanon-vector ladder. Historically '
            'this instrument precedes presence, basing, and trainers.',
        'triggers_breached': [
            'turkey lebanon defense agreement', 'turkey lebanon military agreement',
            'turkey lebanon defense cooperation', 'turkey lebanon mou',
            'ankara beirut defense', 'turkish military trainers lebanon',
            'turkish troops lebanon', 'turkey lebanon security memorandum',
        ],
        'triggers_approaching': [
            'turkey lebanon military talks', 'turkey lebanese army',
            'turkish drones lebanon', 'bayraktar lebanon', 'turkey laf',
            'turkey lebanon security cooperation', 'turkish defense delegation beirut',
        ],
    },
    {
        'id':       'turkey_israel_direct_clash',
        'category': 'Mirror Friction',
        'title':    'Turkey-Israel Direct Confrontation Indicator',
        'severity': 5,
        'description':
            'Direct military incident, deconfliction failure, or '
            'force-on-force language between Turkish and Israeli assets '
            '-- most plausibly in Syrian airspace where both operate. '
            'Two NATO-adjacent militaries in the same contested space '
            'with collapsing deconfliction is the tail risk this '
            'tracker exists to surface early.',
        'triggers_breached': [
            'turkey israel clash', 'turkish israeli forces clash',
            'israel strikes turkish', 'turkey strikes israeli',
            'turkish israeli incident syria', 'turkey israel military confrontation',
            'turkish jets israeli jets', 'turkey israel exchange fire',
        ],
        'triggers_approaching': [
            'turkey israel deconfliction', 'turkey israel tensions syria',
            'israel warns turkey', 'turkey warns israel',
            'turkey israel collision course', 'erdogan netanyahu confrontation',
        ],
    },
    {
        'id':       'nato_rupture',
        'category': 'Alignment',
        'title':    'NATO-Anchor Rupture Signals',
        'severity': 4,
        'description':
            'Concrete moves consistent with Alliance decoupling rather '
            'than routine friction: new S-400 batteries or activation, '
            'Incirlik access restrictions on US/NATO operations, '
            'Article 5 commitment doubts from Ankara, SCO/BRICS '
            'membership steps beyond dialogue-partner status, or NATO '
            'exercise withdrawals. Routine Erdogan NATO-bashing is '
            'baseline; structural moves are the signal.',
        'triggers_breached': [
            'turkey leaves nato', 'turkey suspends nato', 'incirlik closed',
            'incirlik access restricted', 's-400 activated', 'new s-400 delivery',
            'turkey joins sco', 'turkey brics membership', 'turkey blocks nato operation',
        ],
        'triggers_approaching': [
            'turkey nato crisis', 'turkey threatens nato', 'incirlik leverage',
            'turkey questions article 5', 'turkey sco membership talks',
            'turkey brics application', 'turkey nato exercise withdrawal',
            's-400 second battery', 'turkey russia defense deal',
        ],
    },
    {
        'id':       'straits_restriction',
        'category': 'Straits Leverage',
        'title':    'Montreux / Straits Restriction Signaling',
        'severity': 4,
        'description':
            'Turkish signaling about restricting Bosphorus/Dardanelles '
            'transit beyond standing Montreux wartime measures -- '
            'tanker-class restrictions, insurance documentation '
            'tightening used as leverage, or threats to close straits '
            'to specific flags. The straits are Ankara\'s single most '
            'escalatory non-military lever; ~3M bpd of crude transits.',
        'triggers_breached': [
            'turkey closes straits', 'bosphorus closed', 'straits closure',
            'turkey blocks tankers', 'montreux suspension', 'dardanelles closed',
        ],
        'triggers_approaching': [
            'straits restriction', 'bosphorus restriction', 'tanker insurance bosphorus',
            'montreux review', 'turkey straits leverage', 'bosphorus transit delay',
        ],
    },
    {
        'id':       'syria_new_operation',
        'category': 'Syria Lead Indicator',
        'title':    'New Turkish Operation Language in Syria',
        'severity': 4,
        'description':
            'Language consistent with a NEW Turkish military operation '
            'or major expansion in Syria: operation naming patterns, '
            'troop massing on the border, ultimatums to the SDF or '
            'Damascus, or "terror corridor" framing revival. Syria is '
            'the lead-indicator vector -- sharp rises here have '
            'historically preceded broader regional ambition.',
        'triggers_breached': [
            'turkey launches operation syria', 'new turkish operation',
            'turkish offensive syria', 'turkey ground operation syria',
            'turkish troops enter', 'operation against sdf',
        ],
        'triggers_approaching': [
            'turkey masses troops', 'turkish reinforcements border',
            'turkey ultimatum sdf', 'turkey warns damascus', 'terror corridor',
            'turkey military buildup syria', 'imminent turkish operation',
        ],
    },
    {
        'id':       'kurdish_file_reversal',
        'category': 'Kurdish File',
        'title':    'Kurdish Peace-Process Reversal',
        'severity': 3,
        'description':
            'Collapse signals in the PKK dissolution / peace process: '
            'renewed PKK attacks, mass detention waves of Kurdish '
            'politicians, DEM party closure proceedings, or resumed '
            'cross-border strikes framed as process termination. '
            'Kurdish-file reversals are escalation tells with direct '
            'read-across to Syria and Iraq postures.',
        'triggers_breached': [
            'pkk attack resumed', 'peace process collapsed turkey',
            'dem party closed', 'kurdish peace process dead',
            'pkk ends ceasefire', 'turkey resumes strikes pkk',
        ],
        'triggers_approaching': [
            'peace process strain', 'kurdish process stalled',
            'dem party closure case', 'kurdish mayors detained',
            'pkk dissolution stalled', 'ocalan process doubt',
        ],
    },
    {
        'id':       'domestic_crisis_escalation',
        'category': 'Domestic',
        'title':    'Domestic Crisis Escalation',
        'severity': 3,
        'description':
            'Domestic instability beyond routine polarization: mass '
            'protest waves (Imamoglu-case escalation), lira crisis '
            'spiral, CBRT leadership purge, emergency-rule language, or '
            'opposition leadership arrests. Domestic pressure transmits '
            'to foreign-policy risk appetite in both directions -- '
            'caution before elections, diversion plays under stress.',
        'triggers_breached': [
            'state of emergency turkey', 'mass protests turkey', 'lira collapse',
            'imamoglu sentenced', 'chp leader arrested', 'martial law turkey',
            'capital controls turkey',
        ],
        'triggers_approaching': [
            'imamoglu trial', 'imamoglu verdict', 'lira plunge', 'lira record low',
            'cbrt governor fired', 'protests istanbul', 'chp crackdown',
            'opposition crackdown turkey', 'early elections turkey',
        ],
    },
]


# ============================================================
# GREEN LINES -- stabilization / anchor tracks
# ============================================================

GREEN_LINES = [
    {
        'id':       'nato_anchor_active',
        'category': 'Alignment',
        'title':    'NATO-Anchor Cooperation Active',
        'description':
            'Concrete Alliance-anchoring moves: F-35 program re-entry '
            'steps, F-16 deliveries, EU SAFE defense-program '
            'participation, joint exercises, Montreux enforcement '
            'cooperation, or Article 5 reaffirmation at leader level. '
            'These hold the NATO-anchor index up against autonomy drift.',
        'triggers_active': [
            'turkey f-35 deal', 'turkey rejoins f-35', 'f-16 delivered turkey',
            'turkey safe program', 'turkey eu defense program',
            'turkey nato exercise', 'turkey hosts nato', 'erdogan article 5',
            'turkey nato summit agreement', 'turkey patriot deal',
        ],
        'triggers_signaled': [
            'turkey f-35 talks', 'turkey nato cooperation', 'turkey eu defense talks',
            'turkey us defense talks', 'caatsa relief turkey', 'turkey f-16 upgrade',
        ],
    },
    {
        'id':       'israel_deconfliction_track',
        'category': 'Mirror Friction',
        'title':    'Turkey-Israel Deconfliction Track Active',
        'description':
            'Active deconfliction or normalization machinery between '
            'Ankara and Jerusalem: technical talks (the Azerbaijan-'
            'mediated Syria channel), restored ambassador-level contact, '
            'or trade-relationship repair. This is the principal brake '
            'on the mirror-friction spiral.',
        'triggers_active': [
            'turkey israel deconfliction talks', 'turkey israel agreement',
            'turkey israel normalization', 'azerbaijan mediates turkey israel',
            'turkey israel technical talks', 'turkey israel channel',
        ],
        'triggers_signaled': [
            'turkey israel dialogue', 'turkey israel contacts',
            'turkey israel de-escalation', 'baku turkey israel',
        ],
    },
    {
        'id':       'kurdish_peace_process',
        'category': 'Kurdish File',
        'title':    'Kurdish Peace Process Advancing',
        'description':
            'Forward motion in the PKK dissolution / political '
            'settlement: disarmament milestones, DEM-AKP framework '
            'steps, reintegration legislation, or SDF integration '
            'progress in Syria. Process momentum lowers the Syria and '
            'domestic vectors simultaneously.',
        'triggers_active': [
            'pkk disarmament', 'pkk dissolves', 'kurdish peace agreement',
            'dem akp framework', 'reintegration law turkey', 'sdf integration agreed',
        ],
        'triggers_signaled': [
            'kurdish peace talks', 'ocalan statement peace', 'pkk congress',
            'kurdish opening', 'dem party talks',
        ],
    },
    {
        'id':       'mediation_track',
        'category': 'Diplomatic',
        'title':    'Turkey Mediation Role Active',
        'description':
            'Ankara operating in its mediator identity -- Ukraine grain '
            '/ prisoner channels, Istanbul-format hosting, Hamas-file '
            'intermediation, or Horn of Africa shuttle work. An active '
            'mediation posture is historically associated with '
            'restraint on Ankara\'s own escalation vectors (reputational '
            'capital is in play).',
        'triggers_active': [
            'turkey mediates', 'istanbul talks hosted', 'turkey brokers',
            'erdogan mediation', 'turkey hosts negotiations', 'ankara mediates',
            'turkey grain deal', 'istanbul format',
        ],
        'triggers_signaled': [
            'turkey offers mediate', 'turkey mediation offer', 'ankara offers host',
            'turkey diplomatic initiative',
        ],
    },
]


# ============================================================
# DUAL ALIGNMENT INDICES -- the swing-state core
# ============================================================

NATO_ANCHOR_KEYWORDS = [
    # Alliance machinery
    'turkey nato exercise', 'nato exercise turkey', 'turkey nato summit',
    'turkey nato commitment', 'turkey article 5', 'nato second largest army',
    'turkey nato cooperation', 'turkey hosts nato',
    # US/Western defense track
    'turkey f-35', 'turkey f-16', 'f-16 turkey', 'turkey patriot',
    'turkey us defense', 'caatsa relief', 'turkey pentagon',
    # EU defense / SAFE
    'turkey safe program', 'turkey eu defense', 'turkey european defense',
    # Montreux enforcement (Alliance-aligned application)
    'montreux enforcement', 'turkey enforces montreux', 'turkey blocks warships',
    # Ukraine-aligned track
    'turkey arms ukraine', 'bayraktar ukraine', 'turkey supports ukraine',
]

STRATEGIC_AUTONOMY_KEYWORDS = [
    # Russia entanglement
    'turkey russia energy', 'turkstream', 'akkuyu', 'turkey russia trade',
    'erdogan putin', 'turkey russia agreement', 'turkey rosatom',
    's-400', 'turkey russia defense',
    # Iran coordination
    'turkey iran cooperation', 'erdogan iran', 'turkey iran trade',
    'turkey iran agreement', 'ankara tehran',
    # East-bloc institutions
    'turkey sco', 'turkey brics', 'shanghai cooperation turkey',
    # Anti-Western / sovereignty framing
    'erdogan criticizes nato', 'erdogan slams west', 'turkey condemns us',
    'erdogan anti-west', 'turkey independent foreign policy',
    'strategic autonomy turkey', 'turkey defies sanctions',
    # Hamas / Islamist solidarity track
    'erdogan hamas', 'turkey hosts hamas', 'erdogan jerusalem',
    'erdogan muslim world', 'erdogan ummah',
]


def _score_alignment_indices(scan_data):
    """The swing-state product: parallel NATO-anchor and strategic-
    autonomy indices. Baseline expectation is BOTH elevated ("Turkey is
    Turkey"); the analytical signal is divergence between them."""
    anchor_hits = _check_keywords(scan_data, NATO_ANCHOR_KEYWORDS)
    autonomy_hits = _check_keywords(scan_data, STRATEGIC_AUTONOMY_KEYWORDS)
    # Scale hit counts to 0-100 index (8+ distinct keyword classes = saturated)
    anchor_index = min(100, int(anchor_hits * 12.5))
    autonomy_index = min(100, int(autonomy_hits * 12.5))
    divergence = autonomy_index - anchor_index

    if divergence >= 40:
        posture = 'DECOUPLING SIGNALS -- autonomy track running well ahead of Alliance track'
        band = 'decoupling'
    elif divergence >= 20:
        posture = 'DRIFT -- autonomy signals outpacing NATO-anchor signals this cycle'
        band = 'drifting'
    elif divergence <= -20:
        posture = 'ANCHORING -- Alliance-track signals outpacing autonomy this cycle'
        band = 'anchoring'
    else:
        posture = 'DUAL-TRACK BASELINE -- both tracks active, no decoupling pattern'
        band = 'anchored'

    return {
        'nato_anchor_index':       anchor_index,
        'strategic_autonomy_index': autonomy_index,
        'anchor_hits':             anchor_hits,
        'autonomy_hits':           autonomy_hits,
        'divergence':              divergence,
        'band':                    band,
        'posture':                 posture,
        'method': ('Keyword-class hit counts scaled to 0-100 per index. '
                   'Signal = divergence between indices, not either level alone.'),
    }


# ============================================================
# LEBANON-VECTOR PLAYBOOK LADDER
# ============================================================

LEBANON_VECTOR_STAGES = [
    {
        'stage': 1, 'name': 'Perimeter Rhetoric',
        'keywords': [
            'threaten turkey too', 'threatens turkey too', 'turkey security perimeter',
            'erdogan lebanon', 'turkey protects lebanon', 'turkey lebanese sunnis',
            'turkey lebanon sovereignty', 'erdogan defends lebanon',
            'ottoman lebanon', 'turkey historic responsibility',
        ],
    },
    {
        'stage': 2, 'name': 'Soft-Power Penetration',
        'keywords': [
            'diyanet lebanon', 'tika lebanon', 'turkish aid lebanon',
            'turkish schools lebanon', 'turkey tripoli', 'turkey akkar',
            'turkish citizenship lebanon', 'turkmen lebanon', 'turkish scholarships lebanon',
            'turkish mosques lebanon', 'turkish cultural center lebanon',
        ],
    },
    {
        'stage': 3, 'name': 'Economic-Strategic Stakes',
        'keywords': [
            'turkey beirut port', 'turkey tripoli port', 'turkish reconstruction lebanon',
            'tpao lebanon', 'turkey lebanon energy', 'turkish contractors lebanon',
            'turkey lebanon investment', 'turkish companies beirut',
            'turkey lebanon gas', 'turkey lebanon offshore',
        ],
    },
    {
        'stage': 4, 'name': 'Security Footprint (Libya-Model Tripwire)',
        'keywords': [
            'turkey lebanon defense', 'turkey lebanon military', 'turkish trainers lebanon',
            'turkey laf', 'bayraktar lebanon', 'turkey lebanon mou',
            'turkey lebanon security agreement', 'turkish naval visit beirut',
        ],
    },
    {
        'stage': 5, 'name': 'Presence / Buffer Framing',
        'keywords': [
            'turkish troops lebanon', 'turkey deploys lebanon', 'buffer zone lebanon',
            'safe zone lebanon', 'turkish forces beirut', 'turkey intervention lebanon',
        ],
    },
]


def _score_lebanon_vector(scan_data):
    """Score the Lebanon vector against the playbook ladder. The HIGHEST
    stage with keyword hits sets the reading; lower-stage activity is
    reported as breadth. Stage language is estimative throughout."""
    stage_hits = []
    for st in LEBANON_VECTOR_STAGES:
        hits = _check_keywords(scan_data, st['keywords'])
        stage_hits.append({'stage': st['stage'], 'name': st['name'], 'hits': hits})

    active = [sh for sh in stage_hits if sh['hits'] > 0]
    top = max(active, key=lambda x: x['stage']) if active else None

    if not top:
        reading = ('No Lebanon-vector signals detected this cycle. The ladder '
                   'is instrumented; silence is the honest reading.')
        band = 'dormant'
    elif top['stage'] <= 1:
        reading = ('Perimeter-rhetoric signals present -- language extending '
                   'Turkey\'s declared security perimeter over Lebanon. This is '
                   'the ladder\'s lowest rung and is consistent with narrative '
                   'positioning, not operational preparation.')
        band = 'rhetoric'
    elif top['stage'] == 2:
        reading = ('Soft-power-penetration signals present (Diyanet/TIKA/'
                   'community instruments). This layer resembles Turkey\'s '
                   'Balkans pattern and historically precedes economic stakes, '
                   'not kinetic moves.')
        band = 'soft_power'
    elif top['stage'] == 3:
        reading = ('Economic-strategic stake signals present (ports, '
                   'reconstruction, energy). On the documented playbook this '
                   'rung historically precedes security-cooperation overtures. '
                   'Port-concession reporting is the highest-value watch item.')
        band = 'economic'
    elif top['stage'] == 4:
        reading = ('SECURITY-FOOTPRINT signals present -- defense-cooperation '
                   'class language. This is the Libya-model tripwire rung: in '
                   'the 2019-2020 precedent, an MOU of this class preceded '
                   'deployment by invitation within months.')
        band = 'security'
    else:
        reading = ('PRESENCE/BUFFER-class signals present -- deployment or '
                   'buffer-zone framing applied to Lebanon. This is the '
                   'pattern that has immediately preceded every Turkish '
                   'cross-border operation since 2016.')
        band = 'kinetic_risk'

    return {
        'stage':       top['stage'] if top else 0,
        'stage_name':  top['name'] if top else 'Dormant',
        'band':        band,
        'stages':      stage_hits,
        'reading':     reading,
        'precedents':  'N. Cyprus 1974 · Syria 2016-19 · Libya 2020 · Somalia · Iraq (Bashiqa) · Balkans soft power',
    }


# ============================================================
# MIRROR-IMAGING FRICTION INDEX
# ============================================================

ISRAEL_CLAIMS_TURKEY_KEYWORDS = [
    'israel warns turkey', 'israeli officials turkey', 'turkish takeover lebanon',
    'turkey threat israel', 'israel turkey malign', 'netanyahu turkey',
    'israel accuses turkey', 'turkish expansion israel warns',
    'israel turkey ottoman', 'idf turkey threat', 'israel concerned turkey',
    'saudi sponsored turkish', 'turkey neo-ottoman threat',
]

TURKEY_CLAIMS_ISRAEL_KEYWORDS = [
    'threaten turkey too', 'threatens turkey too', 'erdogan israel attacks',
    'turkey condemns israel', 'erdogan condemns israel', 'turkey israel expansion',
    'ankara israel syria', 'turkey accuses israel', 'erdogan netanyahu',
    'turkey israel aggression', 'israeli expansionism turkey',
]


def _score_mirror_friction(scan_data):
    """Both capitals accusing the other of Levant expansion, escalating
    in sync, is itself the signal -- an action-reaction spiral read."""
    israel_claims = _check_keywords(scan_data, ISRAEL_CLAIMS_TURKEY_KEYWORDS)
    turkey_claims = _check_keywords(scan_data, TURKEY_CLAIMS_ISRAEL_KEYWORDS)
    combined = israel_claims + turkey_claims
    synchronized = israel_claims >= 2 and turkey_claims >= 2

    if synchronized and combined >= 8:
        band, reading = 'high', (
            'Mirror-imaging spiral active: Israeli claims about Turkish '
            'expansion and Turkish claims about Israeli expansion are BOTH '
            'elevated this cycle. Synchronized escalation of mutual threat '
            'narratives is the pattern that has historically preceded '
            'deconfliction failures between regional rivals operating in '
            'shared space.')
    elif synchronized:
        band, reading = 'elevated', (
            'Both directions of the Turkey-Israel threat narrative are '
            'active this cycle -- each capital is framing the other as the '
            'expansionist. Watch the Azerbaijan-mediated deconfliction '
            'channel for whether machinery is keeping pace with rhetoric.')
    elif combined >= 3:
        band, reading = 'simmering', (
            'One-directional friction rhetoric detected. Not yet a '
            'synchronized spiral; the asymmetry itself is informative.')
    else:
        band, reading = 'normal', 'No significant mirror-friction signals this cycle.'

    return {
        'israel_claims_turkey': israel_claims,
        'turkey_claims_israel': turkey_claims,
        'synchronized':         synchronized,
        'band':                 band,
        'reading':              reading,
    }


# ============================================================
# CONSTITUTIONAL-CLOCK MULTIPLIER (calendar discipline)
# ============================================================

ELECTION_PROXIMITY_KEYWORDS = [
    'early elections turkey', 'turkey snap election', 'new constitution turkey',
    'erdogan constitution', 'constitutional amendment turkey', 'erdogan 2028',
    'erdogan re-election', 'turkey election date', 'erdogan term',
]


def _election_clock_multiplier(scan_data, red_lines_triggered):
    """Election/constitution proximity amplifies an ACTIVE signal stack
    by 15%; it contributes ZERO on its own (multiplier, never signal --
    the Black Swan calendar discipline). FDD assessment: election math
    is currently suppressing Ankara's appetite for war entanglement, so
    the multiplier reads as context on risk appetite in either direction."""
    hits = _check_keywords(scan_data, ELECTION_PROXIMITY_KEYWORDS)
    active_stack = any(r['status'] in ('BREACHED', 'APPROACHING')
                       for r in red_lines_triggered)
    active = hits >= 2 and active_stack
    return {
        'active':     active,
        'hits':       hits,
        'multiplier': 0.15 if active else 0.0,
        'note': ('Constitutional-clock window detected alongside an active '
                 'signal stack -- domestic timing pressure amplifies the '
                 'composite by 15%.') if active else
                ('Calendar condition contributes zero without an active '
                 'signal stack (multiplier discipline).'),
    }


# ============================================================
# CORPUS KEYWORD MATCHER
# ============================================================

def _check_keywords(scan_data, keywords):
    """Match keywords against scan_data article corpus + social signals.
    URL slugs are de-hyphenated so multi-word keywords match headline
    slugs (the Ukraine v1.2 lesson)."""
    if not keywords:
        return 0
    corpus_parts = []
    for key in ('articles_en', 'articles_tr', 'articles_other'):
        for art in (scan_data.get(key) or []):
            corpus_parts.append((art.get('title') or '').lower())
            corpus_parts.append((art.get('description') or '').lower())
            corpus_parts.append((art.get('summary') or '').lower())
            corpus_parts.append((art.get('content') or '').lower())
            _url = (art.get('url') or art.get('link') or '').lower()
            if _url:
                corpus_parts.append(_url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    for key in ('telegram_messages', 'bluesky_signals', 'reddit_signals'):
        for sig in (scan_data.get(key) or []):
            corpus_parts.append((sig.get('text') or sig.get('title') or '').lower())
    corpus = ' | '.join(corpus_parts)
    if not corpus:
        return 0
    matches = 0
    for kw in keywords:
        if kw.lower() in corpus:
            matches += 1
    return matches


# ============================================================
# RED / GREEN LINE SCORING
# ============================================================

def _score_red_lines(scan_data):
    triggered = []
    for line in RED_LINES:
        breached_hits = _check_keywords(scan_data, line['triggers_breached'])
        approaching_hits = _check_keywords(scan_data, line['triggers_approaching'])
        if breached_hits > 0:
            status = 'BREACHED'
        elif approaching_hits > 0:
            status = 'APPROACHING'
        else:
            status = 'QUIET'
        triggered.append({
            'id':               line['id'],
            'category':         line['category'],
            'title':            line['title'],
            'severity':         line['severity'],
            'description':      line['description'],
            'status':           status,
            'breached_hits':    breached_hits,
            'approaching_hits': approaching_hits,
        })
    return triggered


def _score_green_lines(scan_data):
    triggered = []
    for line in GREEN_LINES:
        active_hits = _check_keywords(scan_data, line['triggers_active'])
        signaled_hits = _check_keywords(scan_data, line['triggers_signaled'])
        if active_hits > 0:
            status = 'ACTIVE'
        elif signaled_hits > 0:
            status = 'SIGNALED'
        else:
            status = 'QUIET'
        triggered.append({
            'id':            line['id'],
            'category':      line['category'],
            'title':         line['title'],
            'description':   line['description'],
            'status':        status,
            'active_hits':   active_hits,
            'signaled_hits': signaled_hits,
        })
    return triggered


# ============================================================
# DIPLOMATIC / MEDIATION TRACK
# ============================================================

MEDIATION_TRIGGERS = [
    'turkey mediates', 'ankara mediates', 'turkey brokers', 'erdogan mediation',
    'istanbul talks', 'istanbul format', 'turkey hosts negotiations',
    'turkey hosts talks', 'turkey grain deal', 'fidan shuttle',
    'turkey prisoner exchange', 'turkey diplomatic initiative',
    'turkey offers mediate', 'erdogan calls leaders', 'turkey deconfliction',
    'azerbaijan mediates turkey israel',
]

MEDIATION_NEGATORS = [
    'turkey refuses mediate', 'mediation collapsed', 'talks collapsed turkey',
    'turkey suspends talks', 'erdogan rules out', 'turkey withdraws mediation',
]


def _score_diplomatic_track(scan_data, green_lines_triggered):
    """Mediation posture: Turkey's diplomatic identity. Active mediation
    yields a small negative (de-escalatory) composite modifier --
    reputational capital in play is historically associated with
    restraint on Ankara's own vectors."""
    raw = _check_keywords(scan_data, MEDIATION_TRIGGERS)
    negated = _check_keywords(scan_data, MEDIATION_NEGATORS)
    score = max(0, raw - negated)

    deconfliction_active = any(
        g['id'] == 'israel_deconfliction_track' and g['status'] == 'ACTIVE'
        for g in green_lines_triggered)

    if score >= 4 or (score >= 2 and deconfliction_active):
        scenario, modifier = 'Active Mediation Posture', -6
    elif score >= 2:
        scenario, modifier = 'Mediation Signals Present', -3
    elif score >= 1:
        scenario, modifier = 'Mediation Mentions Only', -1
    else:
        scenario, modifier = 'No Active Mediation Track', 0

    return {
        'score':    score,
        'raw_hits': raw,
        'negated':  negated,
        'scenario': scenario,
        'modifier': modifier,
        'deconfliction_active': deconfliction_active,
    }


# ============================================================
# SO-WHAT NARRATIVE (estimative voice, doctrine-compliant)
# ============================================================

def _build_so_what(scan_data, red_lines_triggered, green_lines_triggered,
                   diplomatic, alignment, lebanon_vector, mirror_friction,
                   election_clock):
    breached = [r for r in red_lines_triggered if r['status'] == 'BREACHED']
    approaching = [r for r in red_lines_triggered if r['status'] == 'APPROACHING']
    active_gl = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']

    # Scenario selection: worst active pattern wins the headline
    kinetic_class = [r for r in breached if r['id'] in
                     ('buffer_zone_levant', 'defense_mou_lebanon',
                      'turkey_israel_direct_clash', 'syria_new_operation')]
    if kinetic_class:
        scenario = 'Kinetic-Precursor Signals Active'
        priority = 'critical'
        assessment = (
            'Signals in the kinetic-precursor class are present this cycle: '
            + '; '.join(r['title'] for r in kinetic_class[:2]) + '. '
            'On Turkey\'s documented operational pattern, language of this '
            'class has historically preceded cross-border action -- it does '
            'not predict action, and the distinction is the analysis. '
            'Watch deconfliction channels and border force posture for '
            'corroboration across independent layers.')
    elif mirror_friction['band'] == 'high':
        scenario = 'Mirror-Friction Spiral'
        priority = 'high'
        assessment = mirror_friction['reading']
    elif mirror_friction['band'] == 'elevated' and mirror_friction['synchronized']:
        scenario = 'Mirror Friction Building'
        priority = 'elevated'
        assessment = mirror_friction['reading'] + (
            ' Lebanon vector currently reads at the '
            + lebanon_vector['stage_name'].lower() + ' level.')
    elif alignment['band'] == 'decoupling':
        scenario = 'Alignment Decoupling Signals'
        priority = 'high'
        assessment = (
            'The strategic-autonomy index is running well ahead of the '
            'NATO-anchor index this cycle (divergence '
            f"{alignment['divergence']:+d}). Sustained divergence of this "
            'class -- rather than any single S-400 or SCO headline -- is '
            'the pattern consistent with genuine drift from the Alliance '
            'anchor. One cycle is weather; watch for persistence.')
    elif breached or len(approaching) >= 2:
        scenario = 'Elevated Signal Stack'
        priority = 'elevated'
        names = [r['title'] for r in (breached + approaching)[:3]]
        assessment = (
            'Multiple tripwires show activity this cycle: ' + '; '.join(names)
            + '. No kinetic-precursor class signals are present; the stack '
            'is consistent with elevated friction rather than operational '
            'preparation. ' + lebanon_vector['reading'])
    elif lebanon_vector['stage'] >= 3:
        scenario = 'Levant Vector Advancing'
        priority = 'elevated'
        assessment = lebanon_vector['reading']
    else:
        scenario = 'Dual-Track Baseline'
        priority = 'normal'
        assessment = (
            'Turkey holds its characteristic posture this cycle: both the '
            'NATO-anchor and strategic-autonomy tracks active, no '
            'kinetic-precursor signals, Lebanon vector at the '
            f"{lebanon_vector['stage_name'].lower()} level. "
            '"Turkey is Turkey" is the baseline reading; the tracker '
            'exists for the cycles when it stops being true.')

    if election_clock['active']:
        assessment += (' Constitutional-clock context: domestic election '
                       'timing is active alongside this signal stack, '
                       'historically associated with amplified risk '
                       'calculus in both directions.')
    if active_gl:
        assessment += (' Stabilization tracks active: '
                       + ', '.join(g['title'] for g in active_gl[:2]) + '.')

    return {
        'scenario':           scenario,
        'priority':           priority,
        'assessment':         assessment,
        'breached_count':     len(breached),
        'approaching_count':  len(approaching),
        'active_green_count': len(active_gl),
        'alignment_posture':  alignment['posture'],
        'lebanon_vector_stage': lebanon_vector['stage'],
        'mirror_friction_band': mirror_friction['band'],
        'disclaimer':         CONVERGENCE_DISCLAIMER,
    }


# ============================================================
# TOP SIGNALS (canonical schema)
# ============================================================

def _build_top_signals(red_lines_triggered, green_lines_triggered,
                       diplomatic, alignment, lebanon_vector,
                       mirror_friction, scan_data):
    signals = []
    SEVERITY_TO_LEVEL = {5: 'critical', 4: 'high', 3: 'elevated',
                         2: 'normal', 1: 'normal'}

    breached = [r for r in red_lines_triggered if r['status'] == 'BREACHED']
    breached.sort(key=lambda r: -r['severity'])
    for r in breached[:3]:
        signals.append({
            'category':    r['category'].lower().replace(' ', '_').replace('/', '_'),
            'level':       SEVERITY_TO_LEVEL.get(r['severity'], 'normal'),
            'short_text':  f"BREACHED: {r['title']}",
            'long_text':   r['description'],
            'icon':        '\U0001f6a8',
            'source_link': f"/rhetoric-turkey.html#{r['id']}",
        })

    approaching = [r for r in red_lines_triggered if r['status'] == 'APPROACHING']
    approaching.sort(key=lambda r: -r['severity'])
    for r in approaching[:2]:
        signals.append({
            'category':    r['category'].lower().replace(' ', '_').replace('/', '_'),
            'level':       'elevated',
            'short_text':  f"Approaching: {r['title']}",
            'long_text':   r['description'],
            'icon':        '\u26a0\ufe0f',
            'source_link': f"/rhetoric-turkey.html#{r['id']}",
        })

    # Swing-state signal: alignment divergence (when it says something)
    if alignment['band'] in ('drifting', 'decoupling', 'anchoring'):
        level = 'high' if alignment['band'] == 'decoupling' else 'elevated'
        signals.append({
            'category':    'alignment_divergence',
            'level':       level if alignment['band'] != 'anchoring' else 'normal',
            'short_text':  (f"Alignment divergence {alignment['divergence']:+d}: "
                            f"{alignment['band'].upper()}"),
            'long_text':   alignment['posture'] + ' ' + alignment['method'],
            'icon':        '\u2693',
            'source_link': '/rhetoric-turkey.html#alignment',
        })

    # Lebanon vector signal (stage 2+ is reportable)
    if lebanon_vector['stage'] >= 2:
        lv_level = {2: 'normal', 3: 'elevated', 4: 'high', 5: 'critical'}[lebanon_vector['stage']]
        signals.append({
            'category':    'lebanon_vector',
            'level':       lv_level,
            'short_text':  (f"Lebanon vector: L{lebanon_vector['stage']} "
                            f"{lebanon_vector['stage_name']}"),
            'long_text':   lebanon_vector['reading'],
            'icon':        '\U0001f1f1\U0001f1e7',
            'source_link': '/rhetoric-turkey.html#lebanon-vector',
        })

    # Mirror friction signal
    if mirror_friction['band'] in ('elevated', 'high'):
        signals.append({
            'category':    'mirror_friction',
            'level':       'high' if mirror_friction['band'] == 'high' else 'elevated',
            'short_text':  (f"Turkey-Israel mirror friction: {mirror_friction['band'].upper()} "
                            f"(IL\u2192TR {mirror_friction['israel_claims_turkey']} / "
                            f"TR\u2192IL {mirror_friction['turkey_claims_israel']})"),
            'long_text':   mirror_friction['reading'],
            'icon':        '\u2694\ufe0f',
            'source_link': '/rhetoric-turkey.html#mirror-friction',
        })

    active_gl = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']
    for g in active_gl[:2]:
        signals.append({
            'category':    'diplomatic',
            'level':       'normal',
            'short_text':  f"De-escalation: {g['title']}",
            'long_text':   g['description'],
            'icon':        '\U0001f7e2',
            'source_link': f"/rhetoric-turkey.html#{g['id']}",
        })

    return signals[:8]


# ============================================================
# CROSS-THEATER FINGERPRINTS
# ============================================================

def _build_fingerprints(red_lines_triggered, green_lines_triggered,
                        alignment, lebanon_vector, mirror_friction,
                        diplomatic, scan_data):
    """Written to shared Redis as fingerprint:turkey:{key} for
    consumption by Lebanon / Israel / Syria trackers (ME backend) and
    both ME + Europe regional BLUFs (Hungary dual-theater precedent)."""
    fingerprints = {
        'turkey_lebanon_vector':   lebanon_vector['band'],   # dormant/rhetoric/soft_power/economic/security/kinetic_risk
        'turkey_israel_friction':  mirror_friction['band'],  # normal/simmering/elevated/high
        'turkey_nato_divergence':  alignment['band'],        # anchored/anchoring/drifting/decoupling
        'turkey_east_alignment':   ('high' if alignment['strategic_autonomy_index'] >= 60
                                    else 'elevated' if alignment['strategic_autonomy_index'] >= 30
                                    else 'baseline'),
        'turkey_straits_leverage': False,
        'turkey_syria_escalation': 'normal',
        'turkey_mediation_active': diplomatic['scenario'] == 'Active Mediation Posture',
    }
    for r in red_lines_triggered:
        if r['status'] in ('BREACHED', 'APPROACHING'):
            if r['id'] == 'straits_restriction':
                fingerprints['turkey_straits_leverage'] = True
            elif r['id'] == 'syria_new_operation':
                fingerprints['turkey_syria_escalation'] = (
                    'critical' if r['status'] == 'BREACHED' else 'elevated')
    return fingerprints


# ============================================================
# MAIN ENTRY
# ============================================================

def interpret_signals(scan_data):
    """Main entry point. Called from rhetoric_tracker_turkey.py.
    Returns interpretation dict with canonical top_signals[]."""
    try:
        red_lines      = _score_red_lines(scan_data)
        green_lines    = _score_green_lines(scan_data)
        diplomatic     = _score_diplomatic_track(scan_data, green_lines)
        alignment      = _score_alignment_indices(scan_data)
        lebanon_vector = _score_lebanon_vector(scan_data)
        mirror         = _score_mirror_friction(scan_data)
        election_clock = _election_clock_multiplier(scan_data, red_lines)
        rumint         = _score_rumint(scan_data)
        so_what        = _build_so_what(scan_data, red_lines, green_lines,
                                        diplomatic, alignment, lebanon_vector,
                                        mirror, election_clock)
        top_signals    = _build_top_signals(red_lines, green_lines, diplomatic,
                                            alignment, lebanon_vector, mirror,
                                            scan_data)
        fingerprints   = _build_fingerprints(red_lines, green_lines, alignment,
                                             lebanon_vector, mirror, diplomatic,
                                             scan_data)

        breached    = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl   = [g for g in green_lines if g['status'] == 'ACTIVE']

        # Composite modifier: diplomatic (de-escalatory) + red-line load,
        # amplified by the constitutional-clock multiplier when active.
        red_load = sum(r['severity'] for r in breached) * 2 \
                 + sum(r['severity'] for r in approaching)
        composite_modifier = diplomatic['modifier'] + red_load
        composite_modifier = int(round(
            composite_modifier * (1.0 + election_clock['multiplier'])))

        return {
            'so_what':             so_what,
            'top_signals':         top_signals,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in red_lines
                                          if r['status'] != 'QUIET'), default=0),
            },
            'green_lines': {
                'triggered':         green_lines,
                'active_count':      len(active_gl),
                'signaled_count':    len([g for g in green_lines
                                          if g['status'] == 'SIGNALED']),
                'diplomatic_score':  diplomatic['score'],
            },
            'diplomatic_track':           diplomatic,
            'alignment':                  alignment,
            'lebanon_vector':             lebanon_vector,
            'mirror_friction':            mirror,
            'election_clock':             election_clock,
            'rumint':                     rumint,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier':         composite_modifier,
            'interpreter_version':        INTERPRETER_VERSION,
            'interpreted_at':             datetime.now(timezone.utc).isoformat(),
            'disclaimer':                 CONVERGENCE_DISCLAIMER,
        }

    except Exception as e:
        print(f'[Turkey Interpreter] Error: {str(e)[:120]}')
        return {
            'so_what': {
                'scenario':           'Interpreter error',
                'priority':           'normal',
                'assessment':         str(e)[:200],
                'breached_count':     0,
                'approaching_count':  0,
                'active_green_count': 0,
            },
            'top_signals':                [],
            'red_lines':                  {'triggered': [], 'breached_count': 0,
                                           'approaching_count': 0, 'highest_severity': 0},
            'green_lines':                {'triggered': [], 'active_count': 0,
                                           'signaled_count': 0, 'diplomatic_score': 0},
            'diplomatic_track':           {'score': 0, 'scenario': 'Unknown', 'modifier': 0},
            'alignment':                  {'nato_anchor_index': 0, 'strategic_autonomy_index': 0,
                                           'divergence': 0, 'band': 'anchored', 'posture': 'Unknown'},
            'lebanon_vector':             {'stage': 0, 'stage_name': 'Dormant',
                                           'band': 'dormant', 'stages': [], 'reading': ''},
            'mirror_friction':            {'band': 'normal', 'reading': '',
                                           'israel_claims_turkey': 0, 'turkey_claims_israel': 0,
                                           'synchronized': False},
            'election_clock':             {'active': False, 'multiplier': 0.0},
            'rumint':                     {'active': False, 'band': 'off', 'label': '',
                                           'driver': '', 'framing': 0, 'specificity': 0,
                                           'reception': 0, 'corroboration': 0},
            'cross_theater_fingerprints': {},
            'composite_modifier':         0,
            'interpreter_version':        INTERPRETER_VERSION,
            'error':                      str(e)[:200],
        }
