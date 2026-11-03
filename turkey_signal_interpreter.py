"""
=======================================================================
  ASIFAH ANALYTICS -- TURKEY SIGNAL INTERPRETER
  v1.1.0 (Nov 3 2026)  -- EVIDENCE PASS + HUB READ
=======================================================================

v1.1.0 (Nov 3 2026)
  1. Red and green lines are scored PER ARTICLE and counted by PUBLISHER
     (europe_evidence): BREACHED needs two outlets. v1.0 pooled every
     headline into one string, so one blog post could breach a sev-5 line.
     Each line now carries its evidence (title, outlet, phrase) and a
     plain-language 'plain' title for the page.
  2. Topic gate: lines and indices read only Turkey items. The Israeli and
     analyst feeds are not Turkey-filtered; "buffer zone" in a JPost story
     about Israel's own zone used to light Turkey's buffer-zone line. Every
     buffer-zone phrase is now Turkey-anchored.
  3. Alignment indices, mirror friction, mediation and the election clock
     count OUTLETS, not phrases -- volume cannot climb above evidence.
  4. Lebanon ladder: rungs 3+ need 2 outlets, rung 5 (presence) needs 3;
     platform outputs cap the ladder at L4 (L5 assertion rule).
  5. Only kinetic lines (direct Turkey-Israel clash, new Syria operation)
     may print 'critical' in top_signals.
  6. top_indicator + thin_read + corpus_health; two dated background
     tracks (Kurdish file, Turkey-Israel deconfliction).
  7. build_hub_read(): Turkey as a WHEEL -- periphery spokes, projection
     footprints and this scan's own Israel/Lebanon reads, under the same
     convergence gate as the GPI's Turkey narrative.
  8. Domestic tripwires updated for 2026: the Imamoglu trial and the May
     2026 CHP court ruling are baseline now; Ozel's new party is the
     opposition to watch.

v1.0.0 (Jun 11 2026) -- original design notes follow.

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

from europe_evidence import (EVIDENCE_VERSION, build_corpus, corpus_health,
                              find, score_green, score_line)

INTERPRETER_VERSION = '1.1.0'

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
        'plain':    'Turkey talking about a new buffer zone in Lebanon, Syria or Iran',
        'kinetic':  False,
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
        # v1.1: every phrase is TURKEY-anchored. 'buffer zone lebanon' alone was
        # Israel's own south-Lebanon zone as often as Turkey's.
        'triggers_breached': [
            'turkish buffer zone in lebanon', 'turkey buffer zone lebanon',
            'turkey safe zone lebanon', 'turkish safe zone in lebanon',
            'turkish buffer zone in iran', 'turkey buffer zone iran',
            'turkey expands safe zone', 'turkey expands buffer zone',
            'new turkish buffer zone', 'lubnan guvenli bolge', 'iran tampon bolge',
        ],
        'triggers_approaching': [
            'turkish buffer zone', 'turkey buffer zone', 'turkey safe zone',
            'turkish safe zone', 'turkey security corridor', 'turkish security zone',
            'ankara buffer zone', 'protective zone turkey', 'tampon bolge',
        ],
    },
    {
        'id':       'defense_mou_lebanon',
        'plain':    'Turkey and Lebanon moving toward a defence agreement',
        'kinetic':  False,
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
        'plain':    'Turkish and Israeli forces in direct confrontation',
        'kinetic':  True,
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
            'turkish israeli forces clash',
            'israel strikes turkish', 'turkey strikes israeli',
            'turkish israeli incident syria', 'turkey israel military confrontation',
            'turkish jets israeli jets', 'turkey israel exchange fire',
        ],
        'triggers_approaching': [
            'turkey israel clash', 'turkey israel tensions syria',
            'israel warns turkey', 'turkey warns israel',
            'turkey israel collision course', 'erdogan netanyahu confrontation',
        ],
    },
    {
        'id':       'nato_rupture',
        'plain':    'Turkey taking concrete steps away from NATO',
        'kinetic':  False,
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
        'plain':    'Turkey threatening to restrict the Bosphorus and Dardanelles',
        'kinetic':  False,
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
        'plain':    'Turkey preparing a new military operation in Syria',
        'kinetic':  True,
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
        'plain':    'The PKK peace process going into reverse',
        'kinetic':  False,
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
        'plain':    "Turkey's domestic political crisis escalating",
        'kinetic':  False,
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
            # v1.1: the Imamoglu trial has run since March 2026 and the CHP court
            # ruling landed May 21 2026 -- reporting ON them is baseline now.
            # Breach = a new rupture: emergency rule, capital controls, the
            # arrest of Ozel (new opposition leader), mass unrest.
            'state of emergency turkey', 'mass protests turkey', 'lira collapse',
            'ozel arrested', 'ozel detained', 'martial law turkey',
            'capital controls turkey', 'opposition party closed turkey',
        ],
        'triggers_approaching': [
            'imamoglu conviction upheld', 'imamoglu political ban upheld',
            'lira plunge', 'lira record low', 'cbrt governor fired',
            'borsa istanbul circuit breaker', 'protests istanbul', 'opposition crackdown turkey',
            'early elections turkey', 'case against ozel', 'ozel immunity',
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
            'caatsa sanctions lifted', 'turkey f-35 return',
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
            'pkk weapons handover', 'peace process law', 'pkk members released',
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
# KEYWORD LISTS (unchanged from v1.0 -- the counting changed, not the words)
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

ELECTION_PROXIMITY_KEYWORDS = [
    'early elections turkey', 'turkey snap election', 'new constitution turkey',
    'erdogan constitution', 'constitutional amendment turkey', 'erdogan 2028',
    'erdogan re-election', 'turkey election date', 'erdogan term',
]

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


# ============================================================
# EVIDENCE CORPUS (v1.1.0)
# ============================================================
# v1.0 pooled every headline into one string and counted distinct phrases
# anywhere in it: one blog post carrying "buffer zone" was enough to light a
# severity-5 red line. v1.1 scores PER ARTICLE and counts PUBLISHERS through
# europe_evidence (the rule the rest of Europe already runs):
#   BREACHED     breach phrase carried by 2+ outlets
#   APPROACHING  breach phrase from 1 outlet, or approach phrases from 2+
#   WATCHING     approach phrase from 1 outlet, or social chatter only
#   INACTIVE     nothing
#
# TOPIC GATE. The Israeli and analyst RSS feeds (JPost, Times of Israel, MEE)
# are NOT Turkey-filtered, so a JPost story about Israel's own buffer zone in
# south Lebanon used to light Turkey's buffer-zone line. Lines and indices now
# read only items that mention Turkey -- or come from a Turkish outlet, where
# the subject is implicit ("Fidan meets...", "Ankara says...").

TURKEY_TERMS = [
    'turkey', 'turkish', 'turkiye', 'erdogan', 'ankara', 'istanbul', 'fidan',
    'bosphorus', 'dardanelles', 'incirlik', 'tsk', 'mit chief',
    'bayraktar', 'baykar', 'diyanet', 'akp', 'mhp', 'chp', 'dem party',
    'imamoglu', 'ozel', 'bahceli', 'ocalan', 'pkk', 'montreux',
    'turkiye', 'turkler', 'tbmm',
    'טורקיה', 'ארדואן', 'تركيا', 'اردوغان', 'أردوغان', 'التركي', 'التركية',
]
TURKISH_OUTLET_HINTS = [
    'daily sabah', 'dailysabah', 'hurriyet', 'trt', 'anadolu', 'aa.com.tr',
    'duvar', 'bianet', 'turkiye today', 'turkiyetoday', 'turkish minute',
    'turkishminute', 'sozcu', 'cumhuriyet', 'milliyet', 'sabah', 'yeni safak',
    'yenisafak', 'medyascope', 't24', 'bloomberg ht', 'ntv', 'haberturk',
]


def _is_turkey_item(item):
    outlet = item.get('outlet') or ''
    if any(h in outlet for h in TURKISH_OUTLET_HINTS):
        return True
    text = item.get('text') or ''
    return any(t in text for t in TURKEY_TERMS)


def _corpus_for(scan_data):
    """(full corpus, Turkey-gated corpus). Built once per interpret call."""
    full = scan_data.get('_corpus')
    if not isinstance(full, list):
        full = build_corpus(scan_data,
                            article_keys=('articles_en', 'articles_tr', 'articles_other'))
    gated = [c for c in full if _is_turkey_item(c)]
    return full, gated


# ============================================================
# DUAL ALIGNMENT INDICES -- the swing-state core (v1.1 evidence-weighted)
# ============================================================

def _breadth_index(found):
    """Phrases count only as far as the outlet breadth behind them: one outlet
    carrying six phrases reads 25, not 75. 8 classes = saturated (100)."""
    phrases = len(found['phrases'])
    outlets = len(found['outlets'])
    return min(100, int(12.5 * min(phrases, outlets + 1)))


def _score_alignment_indices(corpus, thin=False):
    """Parallel NATO-anchor and strategic-autonomy indices. Baseline is BOTH
    elevated ("Turkey is Turkey"); the signal is the divergence between them."""
    anchor = find(corpus, NATO_ANCHOR_KEYWORDS)
    autonomy = find(corpus, STRATEGIC_AUTONOMY_KEYWORDS)
    anchor_index = _breadth_index(anchor)
    autonomy_index = _breadth_index(autonomy)
    divergence = autonomy_index - anchor_index

    if thin:
        posture = ('UNDER-READ -- too few outlets this cycle to read alignment; the indices '
                   'below are a floor, not a finding')
        band = 'anchored' if abs(divergence) < 40 else ('decoupling' if divergence > 0 else 'anchoring')
    elif divergence >= 40:
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
        'nato_anchor_index':        anchor_index,
        'strategic_autonomy_index': autonomy_index,
        'anchor_hits':              len(anchor['phrases']),
        'autonomy_hits':            len(autonomy['phrases']),
        'anchor_outlets':           len(anchor['outlets']),
        'autonomy_outlets':         len(autonomy['outlets']),
        'divergence':               divergence,
        'band':                     band,
        'posture':                  posture,
        'evidence': {'anchor': anchor['evidence'][:3], 'autonomy': autonomy['evidence'][:3]},
        'method': ('Distinct signal classes per index, counted only as far as the number of '
                   'outlets carrying them (phrases <= outlets + 1), scaled to 0-100. The '
                   'signal is the divergence between the two, not either level alone.'),
    }


# ============================================================
# LEBANON-VECTOR PLAYBOOK LADDER (v1.1 corroboration-gated)
# ============================================================
# Rungs 1-2 (rhetoric, soft power) may light on one outlet. Rungs 3+ need two
# outlets -- the platform's L3+ rule -- and rung 5 (presence) needs three,
# because it is the only rung that describes Turkish forces on the ground.
# A single-outlet hit on an upper rung is RECORDED, not asserted.

_STAGE_MIN_OUTLETS = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}


def _score_lebanon_vector(corpus):
    stage_hits = []
    for st in LEBANON_VECTOR_STAGES:
        f = find(corpus, st['keywords'])
        n = len(f['outlets'])
        stage_hits.append({'stage': st['stage'], 'name': st['name'],
                           'hits': len(f['phrases']), 'outlets': n,
                           'reached': n >= _STAGE_MIN_OUTLETS[st['stage']],
                           'evidence': f['evidence'][:2]})

    reached = [sh for sh in stage_hits if sh['reached']]
    top = max(reached, key=lambda x: x['stage']) if reached else None
    single = [sh for sh in stage_hits if sh['outlets'] >= 1 and not sh['reached']]
    unconfirmed = max(single, key=lambda x: x['stage']) if single else None

    if not top:
        reading = ('No corroborated Lebanon-vector signal this cycle. The ladder is '
                   'instrumented; quiet here means nothing reached two outlets.')
        band = 'dormant'
    elif top['stage'] <= 1:
        reading = ('Perimeter rhetoric only -- Ankara talking about Lebanon as inside its '
                   'security perimeter. The lowest rung: narrative positioning, not preparation.')
        band = 'rhetoric'
    elif top['stage'] == 2:
        reading = ('Soft-power activity (Diyanet, TIKA, schools, aid). This is the Balkans '
                   'pattern; historically it precedes economic stakes, not military moves.')
        band = 'soft_power'
    elif top['stage'] == 3:
        reading = ('Economic-strategic stakes (ports, reconstruction, energy), carried by '
                   'two or more outlets. On the documented playbook this rung comes before '
                   'security-cooperation offers. Port-concession reporting is the item to watch.')
        band = 'economic'
    elif top['stage'] == 4:
        reading = ('SECURITY-FOOTPRINT language -- defence-cooperation talk with Beirut, '
                   'corroborated. This is the Libya-model tripwire: in 2019-20 an MOU of this '
                   'class came months before Turkish forces arrived by invitation.')
        band = 'security'
    else:
        reading = ('PRESENCE reporting -- Turkish forces in Lebanon, carried by three or more '
                   'outlets. Every Turkish cross-border deployment since 2016 has followed '
                   'this pattern. Ladder rung 5; platform outputs cap it at L4 (presence is '
                   'not hostilities -- the L5 assertion rule).')
        band = 'kinetic_risk'
    if unconfirmed and (not top or unconfirmed['stage'] > top['stage']):
        reading += (f" One outlet also carried rung-{unconfirmed['stage']} language "
                    f"({unconfirmed['name'].lower()}); single-source, so recorded rather than read.")

    stage = top['stage'] if top else 0
    return {
        'stage':          stage,
        'platform_level': min(stage, 4),
        'stage_name':     top['name'] if top else 'Dormant',
        'band':           band,
        'stages':         stage_hits,
        'unconfirmed_stage': unconfirmed['stage'] if unconfirmed else 0,
        'reading':        reading,
        'precedents':     'N. Cyprus 1974 · Syria 2016-19 · Libya 2020 · Somalia · Iraq (Bashiqa) · Balkans soft power',
    }


# ============================================================
# MIRROR-IMAGING FRICTION INDEX (v1.1 outlet-counted)
# ============================================================

def _score_mirror_friction(corpus):
    """Both capitals accusing the other of Levant expansion, in sync, is the
    signal. v1.1 counts OUTLETS per direction, not phrases."""
    il = find(corpus, ISRAEL_CLAIMS_TURKEY_KEYWORDS)
    tr = find(corpus, TURKEY_CLAIMS_ISRAEL_KEYWORDS)
    n_il, n_tr = len(il['outlets']), len(tr['outlets'])
    combined = n_il + n_tr
    synchronized = n_il >= 2 and n_tr >= 2

    if synchronized and combined >= 7:
        band, reading = 'high', (
            'Mirror-imaging spiral: Israeli claims of Turkish expansion and Turkish claims of '
            'Israeli expansion are BOTH running across several outlets this cycle. Mutual '
            'threat narratives rising together is the pattern that has preceded deconfliction '
            'failures between rivals sharing airspace.')
    elif synchronized:
        band, reading = 'elevated', (
            'Both directions of the Turkey-Israel threat story are live this cycle -- each '
            'capital casting the other as the expansionist. The question is whether the '
            'US-run deconfliction channel is keeping pace with the rhetoric.')
    elif combined >= 3:
        louder = 'Israeli claims about Turkey' if n_il > n_tr else 'Turkish claims about Israel'
        band, reading = 'simmering', (
            f'One-sided friction: {louder} are carrying the story. Not yet a synchronized '
            'spiral -- and which side is louder is itself informative.')
    else:
        band, reading = 'normal', 'No significant Turkey-Israel friction rhetoric this cycle.'

    return {
        'israel_claims_turkey': n_il,
        'turkey_claims_israel': n_tr,
        'synchronized':         synchronized,
        'band':                 band,
        'reading':              reading,
        'evidence':             (il['evidence'][:2] + tr['evidence'][:2]),
        'method':               'Outlets carrying each direction of the claim (not phrase counts).',
    }


# ============================================================
# CONSTITUTIONAL-CLOCK MULTIPLIER (calendar discipline)
# ============================================================

def _election_clock_multiplier(corpus, red_lines_triggered):
    """Election/constitution proximity amplifies an ACTIVE signal stack by 15%;
    it contributes ZERO on its own (multiplier, never signal)."""
    f = find(corpus, ELECTION_PROXIMITY_KEYWORDS)
    outlets = len(f['outlets'])
    active_stack = any(r['status'] in ('BREACHED', 'APPROACHING') for r in red_lines_triggered)
    active = outlets >= 2 and active_stack
    return {
        'active':     active,
        'hits':       len(f['phrases']),
        'outlets':    outlets,
        'multiplier': 0.15 if active else 0.0,
        'note': ('Constitution / early-election talk is running alongside an active signal '
                 'stack -- domestic timing amplifies the composite by 15%.') if active else
                ('Calendar condition contributes zero without an active signal stack '
                 '(multiplier discipline).'),
    }


# ============================================================
# CORPUS KEYWORD MATCHER -- LEGACY (RUMINT only)
# ============================================================

def _check_keywords(scan_data, keywords):
    """v1.0 pooled matcher, kept ONLY for the RUMINT pill (which rides alongside
    the score and never moves it). Red/green lines and indices no longer use it."""
    if not keywords:
        return 0
    corpus_parts = []
    for key in ('articles_en', 'articles_tr', 'articles_other'):
        for art in (scan_data.get(key) or []):
            corpus_parts.append((art.get('title') or '').lower())
            corpus_parts.append((art.get('description') or '').lower())
            _url = (art.get('url') or art.get('link') or '').lower()
            if _url:
                corpus_parts.append(_url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    for key in ('telegram_messages', 'bluesky_signals', 'reddit_signals'):
        for sig in (scan_data.get(key) or []):
            corpus_parts.append((sig.get('text') or sig.get('title') or '').lower())
    corpus = ' | '.join(corpus_parts)
    if not corpus:
        return 0
    return sum(1 for kw in keywords if kw.lower() in corpus)


# ============================================================
# RED / GREEN LINE SCORING (v1.1 evidence-based)
# ============================================================

def _score_red_lines(corpus):
    triggered = []
    for line in RED_LINES:
        s = score_line(corpus, line['triggers_breached'], line['triggers_approaching'])
        triggered.append({
            'id':               line['id'],
            'category':         line['category'],
            'title':            line['title'],
            'plain':            line.get('plain', ''),
            'severity':         line['severity'],
            'kinetic':          bool(line.get('kinetic')),
            'description':      line['description'],
            'status':           s['status'],
            'breached_hits':    s['breached_hits'],
            'approaching_hits': s['approaching_hits'],
            'breach_outlets':   s['breach_outlets'],
            'approach_outlets': s['approach_outlets'],
            'evidence':         s['evidence'],
            'trigger':          _trigger_words(s),
        })
    return triggered


def _trigger_words(s):
    """Plain-language 'why this status' line for the page."""
    st = s['status']
    if st == 'BREACHED':
        return f"Breach language carried by {s['breach_outlets']} outlets."
    if st == 'APPROACHING':
        if s['breach_outlets'] == 1:
            return 'Breach language from one outlet only -- needs a second to count as breached.'
        return f"Approach language carried by {s['approach_outlets']} outlets."
    if st == 'WATCHING':
        return 'One outlet, or social chatter only -- noted, not counted.'
    return ''


def _score_green_lines(corpus):
    triggered = []
    for line in GREEN_LINES:
        s = score_green(corpus, line['triggers_active'], line['triggers_signaled'])
        triggered.append({
            'id':              line['id'],
            'category':        line['category'],
            'title':           line['title'],
            'description':     line['description'],
            'status':          s['status'],
            'active_hits':     s['active_hits'],
            'signaled_hits':   s['signaled_hits'],
            'active_outlets':  s['active_outlets'],
            'signaled_outlets': s['signaled_outlets'],
            'evidence':        s['evidence'],
        })
    return triggered


# ============================================================
# DIPLOMATIC / MEDIATION TRACK (v1.1 outlet-counted)
# ============================================================

def _score_diplomatic_track(corpus, green_lines_triggered):
    """Mediation posture: Turkey's diplomatic identity. The score is now the
    number of OUTLETS carrying mediation language, net of outlets carrying its
    collapse -- one press release no longer reads as an active track."""
    pos = find(corpus, MEDIATION_TRIGGERS)
    neg = find(corpus, MEDIATION_NEGATORS)
    score = max(0, len(pos['outlets']) - len(neg['outlets']))
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
        'raw_hits': len(pos['phrases']),
        'negated':  len(neg['outlets']),
        'scenario': scenario,
        'modifier': modifier,
        'deconfliction_active': deconfliction_active,
        'evidence': pos['evidence'][:3],
        'unit':     'outlets',
    }


# ============================================================
# DATED BACKGROUND TRACKS (v1.1) -- what has already happened
# ============================================================
# The scan asks whether these are holding. Facts are dated and sourced; they
# are background, never this cycle's evidence. Refresh at each review.

KURDISH_BASELINE = {
    'as_of': '2026-11-03',
    'what': ('Feb 2025: Ocalan calls on the PKK to disarm. May 2025: the PKK announces it '
             'will end its armed struggle. Jul and Oct 2025: weapons-handover ceremonies in '
             'northern Iraq. Aug 2025: parliament sets up a commission to oversee the process.'),
    'status': ('Aug 10 2026: parliament passed the framework law for the PKK\'s dissolution '
               '(468 votes; AKP, MHP and DEM in favour) -- legal protection and sentence '
               'suspension for some former members, plus reintegration.'),
    'constraint': ('Still open: Ocalan\'s status, anti-terror law changes, wider Kurdish '
                   'political and cultural rights, and SDF integration in Syria.'),
    'sources': ['https://www.al-monitor.com/originals/2026/08/turkish-parliament-passes-landmark-law-advance-pkk-peace-process'],
}

DECONFLICTION_BASELINE = {
    'as_of': '2026-11-03',
    'what': ('Turkey and Israel both operate in Syrian airspace. The US runs an '
             'information-sharing channel between Ankara, Jerusalem and Damascus.'),
    'status': ('Aug 18 2026: Israel struck the runway at Abu al-Duhur airfield (Idlib) after '
               'reports that Turkey would use it; Ankara was not warned and denied any troop '
               'move. Aug 19: US envoy Tom Barrack said Washington is building a "more '
               'robust" Turkey-Israel-Syria deconfliction mechanism -- not yet in place.'),
    'constraint': 'Israel\'s October 2026 election and coalition formation shape Jerusalem\'s posture.',
    'sources': ['https://www.thenationalnews.com/news/mena/2026/08/19/us-working-on-deconfliction-mechanism-between-turkey-syria-and-israel-says-barrack/'],
}


def _status_of(lines, line_id):
    for ln in lines:
        if ln['id'] == line_id:
            return ln
    return {}


def _kurdish_track(red_lines, green_lines):
    rev = _status_of(red_lines, 'kurdish_file_reversal')
    grn = _status_of(green_lines, 'kurdish_peace_process')
    rs, gs = rev.get('status', 'INACTIVE'), grn.get('status', 'DORMANT')
    if rs in ('BREACHED', 'APPROACHING'):
        status = 'strain'
        read = ('The PKK process is under strain this cycle: reversal language '
                + ('is carried by two or more outlets.' if rs == 'BREACHED' else 'is reported.')
                + ' A reversal would reopen the Syria and Iraq files at once.')
    elif rs == 'WATCHING':
        status = 'contested'
        read = 'One outlet or social chatter questions the process; the August 2026 law still stands.'
    elif gs in ('ACTIVE', 'SIGNALED'):
        status = 'holding'
        read = ('The process is in the news and moving forward: '
                + ('implementation steps are reported.' if gs == 'ACTIVE' else 'talks and statements, not new steps.'))
    else:
        status = 'quiet'
        read = ('The process is not in this scan\'s reporting. Quiet means unread this cycle, '
                'not stalled -- the August 2026 law is the standing baseline.')
    return {'status': status, 'read': read,
            'evidence': (rev.get('evidence') or []) + (grn.get('evidence') or []),
            'baseline': KURDISH_BASELINE,
            'title': 'THE KURDISH FILE — PKK DISSOLUTION PROCESS'}


def _deconfliction_track(red_lines, green_lines, mirror):
    clash = _status_of(red_lines, 'turkey_israel_direct_clash')
    dec = _status_of(green_lines, 'israel_deconfliction_track')
    cs, ds = clash.get('status', 'INACTIVE'), dec.get('status', 'DORMANT')
    if cs == 'BREACHED':
        status = 'strain'
        read = ('Two or more outlets report Turkish and Israeli forces in direct confrontation -- '
                'the tail risk the deconfliction channel exists to stop.')
    elif cs == 'APPROACHING':
        status = 'contested'
        read = ('Tension language about Turkish and Israeli forces in Syria is in the reporting '
                f"({clash.get('trigger', '').rstrip('.').lower()}). No incident is reported.")
    elif mirror.get('band') in ('elevated', 'high'):
        status = 'contested'
        read = ('No incident, but both capitals are accusing each other in sync. Rhetoric is '
                'outrunning the deconfliction machinery.')
    elif ds in ('ACTIVE', 'SIGNALED'):
        status = 'holding'
        read = 'Deconfliction contacts are reported and no confrontation language is present.'
    else:
        status = 'quiet'
        read = ('Neither confrontation nor deconfliction is in this scan\'s reporting. Unread, '
                'not calm -- the Abu al-Duhur strike showed how fast this file moves.')
    return {'status': status, 'read': read,
            'evidence': (clash.get('evidence') or []) + (dec.get('evidence') or []),
            'baseline': DECONFLICTION_BASELINE,
            'title': 'TURKEY–ISRAEL IN SYRIA — THE DECONFLICTION CHANNEL'}


# ============================================================
# HUB READ (v1.1) -- Turkey as a WHEEL: what its spokes are reporting
# ============================================================
# Three inputs, one picture (the same unification the GPI's Turkey-convergence
# narrative uses, so the page and the GPI cannot disagree):
#   periphery   spoke:turkey:<c>  (Greece, Cyprus, Azerbaijan, Armenia, Kazakhstan
#               -- countries REACTING to Turkey), read through spoke_wheel_reader
#   projection  turkey:theater_footprints  (Libya, Syria, Iraq, West Bank --
#               theatres Turkey is pushing INTO), via the Projection Node
#   self        this scan's own Israel-friction and Lebanon-vector reads
# Gate (GPI-identical): converged when 3+ theatres are at L2+, or 2+ that span
# BOTH a projection theatre and a periphery spoke.

HUB_ACTIVE_LEVEL = 2
_FRICTION_LEVEL = {'normal': 0, 'simmering': 1, 'elevated': 2, 'high': 3}
_KIND_WORDS = {'periphery': 'reacting to Ankara', 'projection': 'Turkey pushing in'}


def build_hub_read(periphery_wheel, projection, mirror, lebanon_vector):
    """Pure function -- no Redis. Returns the hub block for the page and summary."""
    nodes = {}

    def put(n):
        cur = nodes.get(n['theatre'])
        if cur is None or n['level'] > cur['level'] or (cur['state'] != 'lit' and n['state'] == 'lit'):
            nodes[n['theatre']] = n

    wheel = periphery_wheel or {}
    proj_detail = (projection or {}).get('theater_detail') or {}
    for s in wheel.get('spokes') or []:
        c = s.get('country')
        if not c or c in proj_detail:
            continue          # projection footprint is the Turkey-specific read for that theatre
        put({'theatre': c, 'display': s.get('display') or c.title(), 'kind': 'periphery',
             'level': int(s.get('level') or 0), 'state': s.get('state') or 'not_reporting',
             'node_class': s.get('node_class') or '', 'relationship': s.get('relationship') or '',
             'top': s.get('top_signal') or '', 'age_hours': s.get('age_hours'),
             'source': s.get('source') or ''})
    for t, d in proj_detail.items():
        lvl = int(d.get('level') or 0)
        put({'theatre': t, 'display': t.replace('_', ' ').title(), 'kind': 'projection',
             'level': lvl, 'state': 'lit' if lvl >= HUB_ACTIVE_LEVEL else 'dark',
             'node_class': d.get('mode') or 'dormant', 'relationship': ', '.join(d.get('objective_tags') or []),
             'top': (d.get('top_phrases') or [''])[0], 'age_hours': None, 'source': 'footprint'})
    fl = _FRICTION_LEVEL.get((mirror or {}).get('band'), 0)
    put({'theatre': 'israel', 'display': 'Israel', 'kind': 'periphery', 'level': fl,
         'state': 'lit' if fl >= HUB_ACTIVE_LEVEL else 'dark', 'node_class': 'friction',
         'relationship': 'friction', 'top': 'Turkey-Israel friction: ' + (mirror or {}).get('band', 'normal'),
         'age_hours': 0, 'source': 'this_scan'})
    lv = int((lebanon_vector or {}).get('platform_level') or 0)
    put({'theatre': 'lebanon', 'display': 'Lebanon', 'kind': 'projection', 'level': lv,
         'state': 'lit' if lv >= HUB_ACTIVE_LEVEL else 'dark', 'node_class': 'playbook_ladder',
         'relationship': (lebanon_vector or {}).get('band', 'dormant'),
         'top': 'Lebanon vector: ' + (lebanon_vector or {}).get('stage_name', 'Dormant'),
         'age_hours': 0, 'source': 'this_scan'})

    allnodes = sorted(nodes.values(), key=lambda n: (-n['level'], n['theatre']))
    active = [n for n in allnodes if n['level'] >= HUB_ACTIVE_LEVEL and n['state'] != 'not_reporting']
    has_p = any(n['kind'] == 'projection' for n in active)
    has_r = any(n['kind'] == 'periphery' for n in active)
    converged = len(active) >= 3 or (len(active) >= 2 and has_p and has_r)
    silent = [n for n in allnodes if n['state'] == 'not_reporting']
    reporting = [n for n in allnodes if n['state'] != 'not_reporting']

    names = ', '.join(n['display'] for n in active)
    if converged:
        span = 'both pushing in and drawing reactions' if (has_p and has_r) else (
            'pushing into several theatres' if has_p else 'drawing reactions across the periphery')
        headline = (f'Turkey\'s wheel is turning: {len(active)} theatres are active at once '
                    f'({names}) -- Ankara {span}. That breadth is the read no single-country '
                    'page can give.')
    elif len(active) == 1:
        headline = (f'One theatre is active on Turkey\'s wheel ({names}); the rest are quiet. '
                    'A lone spoke is local -- convergence needs two or more.')
    elif reporting:
        headline = (f'Turkey\'s wheel is quiet: {len(reporting)} theatres reporting, none above L1. '
                    'No multi-theatre push this cycle.')
    else:
        headline = 'No Turkey spoke is reporting -- the wheel is unread, not quiet.'
    if silent and reporting:
        headline += (f' {len(silent)} expected spoke{"s" if len(silent) != 1 else ""} '
                     f'({", ".join(n["display"] for n in silent)}) did not report: unread, not calm.')

    return {
        'converged':   converged,
        'active':      [n['theatre'] for n in active],
        'active_count': len(active),
        'reporting':   len(reporting),
        'silent':      [n['theatre'] for n in silent],
        'nodes':       allnodes,
        'headline':    headline,
        'wheel_readable': bool(wheel.get('readable', bool(wheel))),
        'projection_bluf': (projection or {}).get('bluf', ''),
        'gate':        ('Converged when 3+ theatres are at L2+, or 2+ spanning a projection '
                        'theatre and a periphery spoke (same gate as the GPI).'),
        'kind_words':  _KIND_WORDS,
    }


def spoke_reads_from_hub(hub):
    """Compact {country: {present, fresh, level, node_class}} for the shared
    evidence-layer wheel card."""
    out = {}
    for n in (hub or {}).get('nodes') or []:
        out[n['theatre']] = {'present': n['state'] != 'not_reporting',
                             'fresh': n['state'] != 'not_reporting',
                             'level': n['level'], 'node_class': n['node_class'],
                             'kind': n['kind']}
    return out


# ============================================================
# SO-WHAT NARRATIVE (estimative voice, doctrine-compliant)
# ============================================================

def _build_so_what(red_lines_triggered, green_lines_triggered, diplomatic, alignment,
                   lebanon_vector, mirror_friction, election_clock, health):
    breached = [r for r in red_lines_triggered if r['status'] == 'BREACHED']
    approaching = [r for r in red_lines_triggered if r['status'] == 'APPROACHING']
    active_gl = [g for g in green_lines_triggered if g['status'] == 'ACTIVE']

    kinetic_class = [r for r in breached if r['id'] in
                     ('buffer_zone_levant', 'defense_mou_lebanon',
                      'turkey_israel_direct_clash', 'syria_new_operation')]
    if kinetic_class:
        scenario, priority = 'Kinetic-Precursor Signals Active', 'critical'
        assessment = (
            'Two or more outlets carry kinetic-precursor language this cycle: '
            + '; '.join(r['title'] for r in kinetic_class[:2]) + '. '
            'On Turkey\'s documented pattern, language of this class has come before '
            'cross-border action -- it does not predict action, and that distinction is the '
            'analysis. Watch border force posture and the deconfliction channel.')
    elif mirror_friction['band'] == 'high':
        scenario, priority = 'Mirror-Friction Spiral', 'high'
        assessment = mirror_friction['reading']
    elif mirror_friction['band'] == 'elevated' and mirror_friction['synchronized']:
        scenario, priority = 'Mirror Friction Building', 'elevated'
        assessment = (mirror_friction['reading'] + ' Lebanon vector reads at the '
                      + lebanon_vector['stage_name'].lower() + ' level.')
    elif alignment['band'] == 'decoupling' and not health.get('thin'):
        scenario, priority = 'Alignment Decoupling Signals', 'high'
        assessment = (
            'The strategic-autonomy index is running well ahead of the NATO-anchor index '
            f"(divergence {alignment['divergence']:+d}). Sustained divergence -- not any single "
            'S-400 or SCO headline -- is what genuine drift from the Alliance looks like. One '
            'cycle is weather; watch for persistence.')
    elif breached or len(approaching) >= 2:
        scenario, priority = 'Elevated Signal Stack', 'elevated'
        names = [r['title'] for r in (breached + approaching)[:3]]
        assessment = (
            'Several tripwires show corroborated activity: ' + '; '.join(names) + '. No '
            'kinetic-precursor line is breached, so the stack reads as friction, not '
            'operational preparation. ' + lebanon_vector['reading'])
    elif lebanon_vector['stage'] >= 3:
        scenario, priority = 'Levant Vector Advancing', 'elevated'
        assessment = lebanon_vector['reading']
    elif health.get('thin'):
        scenario, priority = 'Under-Read Cycle', 'normal'
        assessment = (
            f"This scan is thin ({health.get('reason')}). Quiet lines below are UNREAD, not "
            'calm -- read the baseline tracks and the hub wheel, and treat the score as a floor.')
    else:
        scenario, priority = 'Dual-Track Baseline', 'normal'
        assessment = (
            'Turkey holds its usual posture: NATO-anchor and strategic-autonomy tracks both '
            'active, no kinetic-precursor line corroborated, Lebanon vector at the '
            f"{lebanon_vector['stage_name'].lower()} level. \"Turkey is Turkey\" is the baseline; "
            'the tracker exists for the cycle when it stops being true.')

    if election_clock['active']:
        assessment += (' Constitutional-clock context: election and constitution talk is running '
                       'alongside this signal stack -- historically associated with sharper risk '
                       'calculus in both directions.')
    if active_gl:
        assessment += (' Stabilizing tracks active: '
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
# TOP INDICATOR (v1.1) -- the one plain-language line
# ============================================================

def _top_indicator(red_lines, alignment, lebanon_vector, mirror, kurdish, deconf, health):
    breached = sorted([r for r in red_lines if r['status'] == 'BREACHED'], key=lambda r: -r['severity'])
    approaching = sorted([r for r in red_lines if r['status'] == 'APPROACHING'], key=lambda r: -r['severity'])
    if breached:
        r = breached[0]
        line = (f"{r.get('plain') or r['title']} -- {r['breach_outlets']} outlets carry it this cycle. "
                'That is a corroborated tripwire, not a forecast.')
    elif lebanon_vector['stage'] >= 3:
        line = (f"Turkey's Lebanon playbook reads rung {lebanon_vector['stage']} "
                f"({lebanon_vector['stage_name'].lower()}) on two or more outlets -- the rung before "
                'security cooperation.')
    elif mirror['band'] in ('elevated', 'high'):
        line = ('Turkey and Israel are accusing each other of expansion in the same cycle -- the '
                'rhetoric is running ahead of the deconfliction channel.')
    elif approaching:
        r = approaching[0]
        line = (f"Closest tripwire: {r.get('plain') or r['title']} -- not breached; "
                f"{r['trigger'].rstrip('.').lower()}.")
    elif alignment['band'] in ('drifting', 'decoupling') and not health.get('thin'):
        line = (f"Alignment drift: autonomy signals are outrunning NATO-anchor signals "
                f"({alignment['divergence']:+d}). Watch for a second cycle.")
    else:
        line = ('Turkey is playing both tracks as usual -- NATO and strategic autonomy at once -- '
                'with no tripwire corroborated this cycle.')
    if kurdish['status'] == 'strain':
        line += ' The PKK process is also under strain.'
    elif deconf['status'] == 'strain' and 'Israel' not in line:
        line += ' Turkey-Israel confrontation language is also present.'
    if health.get('thin'):
        line = 'Thin read -- ' + line
    return line


# ============================================================
# TOP SIGNALS (canonical schema)
# ============================================================
# Levels stay strings (critical/high/elevated/normal) for the page and BLUF.
# L5 assertion rule: only a KINETIC line (direct Turkey-Israel clash, a new
# Syria operation) may print 'critical'; every other red line caps at 'high'.

def _build_top_signals(red_lines_triggered, green_lines_triggered, diplomatic, alignment,
                       lebanon_vector, mirror_friction, hub=None):
    signals = []

    def red_level(r, breached):
        if breached:
            if r.get('kinetic') and r['severity'] >= 4:
                return 'critical'
            return 'high' if r['severity'] >= 4 else 'elevated'
        return 'elevated'

    breached = sorted([r for r in red_lines_triggered if r['status'] == 'BREACHED'], key=lambda r: -r['severity'])
    for r in breached[:3]:
        signals.append({
            'category':    r['category'].lower().replace(' ', '_').replace('/', '_'),
            'level':       red_level(r, True),
            'short_text':  f"BREACHED: {r.get('plain') or r['title']} ({r['breach_outlets']} outlets)",
            'long_text':   r['description'],
            'icon':        '\U0001f6a8',
            'source_link': f"/rhetoric-turkey.html#{r['id']}",
        })
    approaching = sorted([r for r in red_lines_triggered if r['status'] == 'APPROACHING'], key=lambda r: -r['severity'])
    for r in approaching[:2]:
        signals.append({
            'category':    r['category'].lower().replace(' ', '_').replace('/', '_'),
            'level':       'elevated',
            'short_text':  f"Approaching: {r.get('plain') or r['title']}",
            'long_text':   r['trigger'] + ' ' + r['description'],
            'icon':        '⚠️',
            'source_link': f"/rhetoric-turkey.html#{r['id']}",
        })
    if alignment['band'] in ('drifting', 'decoupling', 'anchoring'):
        signals.append({
            'category':    'alignment_divergence',
            'level':       ('high' if alignment['band'] == 'decoupling' else
                            'elevated' if alignment['band'] == 'drifting' else 'normal'),
            'short_text':  f"Alignment divergence {alignment['divergence']:+d}: {alignment['band'].upper()}",
            'long_text':   alignment['posture'] + ' ' + alignment['method'],
            'icon':        '⚓',
            'source_link': '/rhetoric-turkey.html#alignment',
        })
    if lebanon_vector['stage'] >= 2:
        signals.append({
            'category':    'lebanon_vector',
            'level':       {2: 'normal', 3: 'elevated', 4: 'high', 5: 'high'}[lebanon_vector['stage']],
            'short_text':  f"Lebanon vector: rung {lebanon_vector['stage']} {lebanon_vector['stage_name']}",
            'long_text':   lebanon_vector['reading'],
            'icon':        '\U0001f1f1\U0001f1e7',
            'source_link': '/rhetoric-turkey.html#lebanon-vector',
        })
    if mirror_friction['band'] in ('elevated', 'high'):
        signals.append({
            'category':    'mirror_friction',
            'level':       'high' if mirror_friction['band'] == 'high' else 'elevated',
            'short_text':  (f"Turkey-Israel mirror friction: {mirror_friction['band'].upper()} "
                            f"(IL→TR {mirror_friction['israel_claims_turkey']} / "
                            f"TR→IL {mirror_friction['turkey_claims_israel']} outlets)"),
            'long_text':   mirror_friction['reading'],
            'icon':        '⚔️',
            'source_link': '/rhetoric-turkey.html#mirror-friction',
        })
    if hub and hub.get('converged'):
        signals.append({
            'category':    'hub_convergence',
            'level':       'elevated',
            'short_text':  f"Turkey wheel converged: {hub['active_count']} theatres active",
            'long_text':   hub['headline'],
            'icon':        '☸️',
            'source_link': '/rhetoric-turkey.html#evLayer',
        })
    for g in [g for g in green_lines_triggered if g['status'] == 'ACTIVE'][:2]:
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

def _build_fingerprints(red_lines_triggered, alignment, lebanon_vector, mirror_friction, diplomatic):
    """fingerprint:turkey:{key} for the ME trackers and both regional BLUFs. Now
    evidence-gated, so the GPI's Turkey-convergence read inherits the rule."""
    fingerprints = {
        'turkey_lebanon_vector':   lebanon_vector['band'],
        'turkey_israel_friction':  mirror_friction['band'],
        'turkey_nato_divergence':  alignment['band'],
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
    """Called from rhetoric_tracker_turkey.py. Returns the interpretation dict
    with canonical top_signals[]. scan_data may carry '_corpus' (pre-built) and
    'sensing'; the hub block is attached by the tracker after its Redis reads."""
    try:
        full, corpus = _corpus_for(scan_data)
        health = corpus_health(scan_data, full, min_articles=25, min_outlets=5)
        red_lines      = _score_red_lines(corpus)
        green_lines    = _score_green_lines(corpus)
        diplomatic     = _score_diplomatic_track(corpus, green_lines)
        alignment      = _score_alignment_indices(corpus, thin=health['thin'])
        lebanon_vector = _score_lebanon_vector(corpus)
        mirror         = _score_mirror_friction(corpus)
        election_clock = _election_clock_multiplier(corpus, red_lines)
        rumint         = _score_rumint(scan_data)
        kurdish        = _kurdish_track(red_lines, green_lines)
        deconf         = _deconfliction_track(red_lines, green_lines, mirror)
        so_what        = _build_so_what(red_lines, green_lines, diplomatic, alignment,
                                        lebanon_vector, mirror, election_clock, health)
        top_signals    = _build_top_signals(red_lines, green_lines, diplomatic, alignment,
                                            lebanon_vector, mirror)
        fingerprints   = _build_fingerprints(red_lines, alignment, lebanon_vector, mirror, diplomatic)
        top_indicator  = _top_indicator(red_lines, alignment, lebanon_vector, mirror,
                                        kurdish, deconf, health)

        breached    = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        watching    = [r for r in red_lines if r['status'] == 'WATCHING']
        active_gl   = [g for g in green_lines if g['status'] == 'ACTIVE']

        red_load = sum(r['severity'] for r in breached) * 2 + sum(r['severity'] for r in approaching)
        composite_modifier = int(round((diplomatic['modifier'] + red_load)
                                       * (1.0 + election_clock['multiplier'])))

        return {
            'so_what':             so_what,
            'top_indicator':       top_indicator,
            'thin_read':           health['thin'],
            'corpus_health':       health,
            'top_signals':         top_signals,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'watching_count':    len(watching),
                'highest_severity':  max((r['severity'] for r in red_lines
                                          if r['status'] in ('BREACHED', 'APPROACHING')), default=0),
                'rule':              'BREACHED = 2+ outlets; APPROACHING = 1 outlet of breach language or 2+ of approach language.',
            },
            'green_lines': {
                'triggered':         green_lines,
                'active_count':      len(active_gl),
                'signaled_count':    len([g for g in green_lines if g['status'] == 'SIGNALED']),
                'diplomatic_score':  diplomatic['score'],
            },
            'diplomatic_track':           diplomatic,
            'alignment':                  alignment,
            'lebanon_vector':             lebanon_vector,
            'mirror_friction':            mirror,
            'election_clock':             election_clock,
            'rumint':                     rumint,
            'kurdish_track':              kurdish,
            'deconfliction_track':        deconf,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier':         composite_modifier,
            'interpreter_version':        INTERPRETER_VERSION,
            'evidence_version':           EVIDENCE_VERSION,
            'interpreted_at':             datetime.now(timezone.utc).isoformat(),
            'disclaimer':                 CONVERGENCE_DISCLAIMER,
        }

    except Exception as e:
        print(f'[Turkey Interpreter] Error: {str(e)[:120]}')
        return {
            'so_what': {'scenario': 'Interpreter error', 'priority': 'normal',
                        'assessment': str(e)[:200], 'breached_count': 0,
                        'approaching_count': 0, 'active_green_count': 0},
            'top_indicator':              'The Turkey interpreter failed this cycle -- nothing on this page is a reading.',
            'thin_read':                  True,
            'corpus_health':              {'thin': True, 'reason': 'interpreter error'},
            'top_signals':                [],
            'red_lines':                  {'triggered': [], 'breached_count': 0,
                                           'approaching_count': 0, 'highest_severity': 0},
            'green_lines':                {'triggered': [], 'active_count': 0,
                                           'signaled_count': 0, 'diplomatic_score': 0},
            'diplomatic_track':           {'score': 0, 'scenario': 'Unknown', 'modifier': 0},
            'alignment':                  {'nato_anchor_index': 0, 'strategic_autonomy_index': 0,
                                           'divergence': 0, 'band': 'anchored', 'posture': 'Unknown'},
            'lebanon_vector':             {'stage': 0, 'platform_level': 0, 'stage_name': 'Dormant',
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
