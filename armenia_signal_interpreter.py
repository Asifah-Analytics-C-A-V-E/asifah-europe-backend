"""
Armenia Signal Interpreter v1.1.0 (Nov 3 2026)
================================================

v1.1.0 (Nov 3 2026) -- EVIDENCE PASS + FOUR WHEELS
  1. Red/green lines and every vector count PUBLISHERS, not pooled phrases
     (europe_evidence). BREACHED needs 2+ outlets. Each line carries its
     evidence (headline, outlet, phrase), a plain-language title and a
     'why this status' sentence.
  2. build_spokes(): Armenia is a spoke on FOUR wheels -- Russia (lever
     pressure), Iran (the conditional buffer), Turkey (normalization) and the
     US (TRIPP anchor). The tracker writes one spoke:{hub}:armenia key each.
  3. Dated background tracks: the treaty/referendum gate (as of Oct 30 2026)
     and the Russian gas lever (price deal expires end-2026).
  4. top_indicator / thin_read / corpus_health.
  5. Reality refresh: the June 2026 election is over (Civil Contract 64/105,
     six short of the 70 needed to call a referendum); snap-election talk is
     now a referendum-clock term.

v1.0.0 (Jul 12 2026) -- original design notes follow.
Analytical layer for rhetoric_tracker_armenia.py. Follows the Turkey
interpreter contract (interpret_signals entry point, canonical top_signals,
cross_theater_fingerprints) with Armenia's own vector set.

THE FRAME (Jul 2026): the Armenia-Azerbaijan war ended on paper (initialed
Aug 2025, White House) and the fight moved inside Armenia. This interpreter
reads a peace-implementation contest under three-directional foreign
pressure -- not a ceasefire line.

Vector set:
  1. TRIPP corridor vector -- first member of the portable corridor-vector
     family (BRI and IMEC vectors will inherit this schema).
  2. Treaty / referendum diplomatic track (Ukraine gate discipline:
     framework triggers + stance negators).
  3. Russia interference and leverage vector -- reporting-tempo sensor,
     both directions honest. Sensor, not referee.
  4. Westward drift axis (Russia to West alignment drift).
  5. Iran conditional-buffer vector -- TRIPP rhetoric intensity is the
     flip-meter from buffer toward friction.
  6. Turkiye normalization vector -- feeds the spoke:turkey:armenia
     relationship polarity (dynamic: friction baseline, alignment when
     normalization warms).
  7. Referendum clock -- MULTIPLIER only, never a standalone signal
     (Black Swan discipline; port of Turkey's election clock).

Doctrine: convergence, not prediction. Estimative voice, precedent
anchored. The reader completes the inference. Absence stays honest.
"""

from datetime import datetime, timezone

from europe_evidence import build_corpus, corpus_health, find

INTERPRETER_VERSION = '1.1.0'

CONVERGENCE_DISCLAIMER = (
    'This composite is a CONVERGENCE indicator, NOT a probability of action. '
    'Active signals indicate pressure conditions are present; they do not '
    'predict whether or when any specific outcome will occur.'
)



# ============================================================
# EVIDENCE CORPUS (v1.1.0, Nov 3 2026)
# ============================================================
# v1.0 pooled every headline into ONE string and counted distinct phrases
# anywhere in it, so one blog post carrying three phrases could breach a
# severity-5 line. The corpus is now scored PER ARTICLE and counted by
# PUBLISHER (europe_evidence -- the rule the rest of Europe runs):
#   * red lines  BREACHED = breach language from 2+ outlets (3 where the line
#                demanded three phrases); APPROACHING = 1 outlet;
#                WATCHING = social chatter only
#   * vectors    a phrase count can never exceed the outlet breadth behind it
#                (phrases <= outlets + 1) -- volume cannot climb above evidence
# Social posts (Reddit / Bluesky) never corroborate. They are recorded, not counted.

_ARTICLE_KEYS = ('articles_en', 'articles_hy', 'articles_ru')


def _corpus(scan_data):
    c = scan_data.get('_ev_corpus')
    if c is None:
        c = build_corpus(scan_data, article_keys=_ARTICLE_KEYS)
        scan_data['_ev_corpus'] = c
    return c


def _check_keywords(scan_data, keywords):
    """Distinct phrases present, capped by the number of outlets carrying them
    (phrases <= outlets + 1). Social-only matches count zero."""
    if not keywords:
        return 0
    f = find(_corpus(scan_data), keywords)
    n = len(f['outlets'])
    return min(len(f['phrases']), n + 1) if n else 0


def _line_trigger(status, n, need):
    if status == 'BREACHED':
        return f'Carried by {n} outlets.'
    if status == 'APPROACHING':
        return (f'{n} outlet' + ('s' if n != 1 else '') +
                f' so far -- needs {need} to count as breached.')
    if status == 'WATCHING':
        return 'Social chatter only -- noted, not counted.'
    return ''


def _score_red_lines(scan_data):
    out = []
    corpus = _corpus(scan_data)
    for line in RED_LINES:
        f = find(corpus, line['keywords'])
        n = len(f['outlets'])
        need = max(2, line.get('breach_threshold', 2))
        status = ('BREACHED' if n >= need else 'APPROACHING' if n >= 1
                  else 'WATCHING' if f['social'] else 'QUIET')
        out.append({'id': line['id'], 'category': line['category'],
                    'title': line['category'], 'plain': line.get('plain', ''),
                    'severity': line['severity'], 'status': status,
                    'hits': len(f['phrases']), 'outlets': n,
                    'description': line['description'],
                    'evidence': f['evidence'][:3],
                    'trigger': _line_trigger(status, n, need)})
    return out


def _score_green_lines(scan_data):
    """De-escalation lines: ACTIVE at the line's threshold in OUTLETS (a
    signature or a border opening is a big claim -- one press release does not
    make it), SIGNALED on one outlet or chatter."""
    out = []
    corpus = _corpus(scan_data)
    for line in GREEN_LINES:
        f = find(corpus, line['keywords'])
        n = len(f['outlets'])
        need = max(1, line.get('active_threshold', 2))
        status = ('ACTIVE' if n >= need else 'SIGNALED' if (n >= 1 or f['social'])
                  else 'QUIET')
        out.append({'id': line['id'], 'category': line['category'],
                    'title': line['category'], 'severity': line['severity'],
                    'status': status, 'hits': len(f['phrases']), 'outlets': n,
                    'description': line['description'],
                    'evidence': f['evidence'][:3]})
    return out


# ============================================================
# RED LINES -- escalation tripwires
# status ladder: QUIET -> APPROACHING (1 hit) -> BREACHED (>= threshold)
# ============================================================

RED_LINES = [
    {
        'id': 'treaty_collapse',
        'plain': 'The Armenia-Azerbaijan peace deal being suspended or abandoned',
        'category': 'Treaty Collapse',
        'severity': 5,
        'breach_threshold': 2,
        'description': 'Peace-agreement suspension or withdrawal language from either capital',
        'keywords': [
            'peace treaty suspended', 'peace agreement suspended', 'treaty collapse',
            'withdraws from peace', 'peace process collapse', 'peace deal collapse',
            'abandons peace agreement', 'peace agreement dead', 'treaty is dead',
            'suspends peace process', 'exits peace process', 'nullifies agreement',
            'мирный договор приостановлен', 'выход из мирного соглашения',
            'срыв мирного процесса',
        ],
    },
    {
        'id': 'corridor_by_force',
        'plain': 'Baku talking about taking the Zangezur corridor by force',
        'category': 'Corridor by Force',
        'severity': 5,
        'breach_threshold': 2,
        'description': 'Revival of Azerbaijani force framing on the Zangezur corridor',
        'keywords': [
            'corridor by force', 'open the corridor by force', 'take zangezur by force',
            'zangezur by force', 'military solution corridor', 'seize the corridor',
            'force open zangezur', 'zangezur ultimatum',
            'зангезур силой', 'коридор силой',
        ],
    },
    {
        'id': 'border_kinetic',
        'plain': 'Shooting on the Armenia-Azerbaijan border',
        'category': 'Border Kinetic',
        'severity': 4,
        'breach_threshold': 2,
        'description': 'Armed incidents on the Armenia-Azerbaijan line (Syunik, Tavush, Nakhchivan)',
        'keywords': [
            'border clash armenia', 'armenia azerbaijan clash', 'cross-border shelling',
            'armenian soldier killed', 'azerbaijani fire armenia', 'shooting on the border',
            'syunik attack', 'tavush shelling', 'nakhchivan incident', 'ceasefire violation armenia',
            'exchange of fire armenia azerbaijan', 'positions shelled armenia',
            'перестрелка на границе', 'обстрел на армяно-азербайджанской границе',
        ],
    },
    {
        'id': 'constitutional_crisis',
        'plain': 'The referendum fight turning into a constitutional crisis',
        'category': 'Constitutional Crisis',
        'severity': 4,
        'breach_threshold': 2,
        'description': 'Referendum blocked, annulled, or dueling-authority language (gridlock going constitutional)',
        'keywords': [
            'referendum blocked', 'referendum annulled', 'constitutional court crisis',
            'referendum unconstitutional', 'blocks constitutional referendum',
            'refuses to recognize results', 'annul the election', 'parallel government',
            'constitutional crisis armenia', 'dissolve parliament armenia',
            'референдум заблокирован', 'конституционный кризис',
        ],
    },
    {
        'id': 'street_destabilization',
        'plain': 'Mass street mobilisation aimed at toppling the government',
        'category': 'Street Destabilization',
        'severity': 3,
        'breach_threshold': 3,
        'description': 'Mass mobilization with regime-change framing; church-led street escalation',
        'keywords': [
            'overthrow pashinyan', 'topple the government armenia', 'coup in armenia',
            'coup attempt armenia', 'storm parliament yerevan', 'mass protests yerevan',
            'clashes with police yerevan', 'church-led protest', 'karekin protest',
            'archbishop protest movement', 'civil disobedience armenia',
            'general strike armenia', 'уличные протесты ереван', 'свержение пашиняна',
            'переворот в армении',
        ],
    },
    {
        'id': 'russian_hard_lever',
        'plain': 'Moscow pulling a hard lever (gas, rail, the Gyumri base, nuclear fuel)',
        'category': 'Russian Hard Lever',
        'severity': 3,
        'breach_threshold': 2,
        'description': 'Moscow pulling an infrastructure or basing lever (Gyumri, rail, gas, Metsamor fuel)',
        'keywords': [
            'gyumri base reinforcement', '102nd base', 'russian troops armenia increase',
            'gazprom cuts armenia', 'gas cutoff armenia', 'gas price armenia gazprom',
            'russian railways armenia suspend', 'south caucasus railway halt',
            'metsamor fuel halt', 'rosatom suspends', 'russian border guards refuse',
            'russia halts gas armenia', 'gas supply to armenia suspended',
            'duty-free gas agreement suspended', 'russia bans armenian imports',
            'газпром армения', 'южно-кавказская железная дорога', 'мецамор',
        ],
    },
    {
        'id': 'iran_corridor_threat',
        'plain': 'Iran threatening the TRIPP / Zangezur route militarily',
        'category': 'Iran Corridor Threat',
        'severity': 3,
        'breach_threshold': 2,
        'description': 'Explicit Iranian military threat language against the TRIPP or Zangezur arrangement',
        'keywords': [
            'iran will not allow corridor', 'iran threatens corridor', 'irgc zangezur',
            'iran military exercise border armenia', 'iran red line zangezur',
            'iran warns trump route', 'tehran threatens tripp', 'iran blocks corridor',
            'red line corridor iran', 'иран не допустит коридор', 'кризис вокруг коридора иран',
        ],
    },
]


# ============================================================
# GREEN LINES -- de-escalation and consolidation markers
# status ladder: QUIET -> SIGNALED (1 hit) -> ACTIVE (>= threshold)
# ============================================================

GREEN_LINES = [
    {
        'id': 'treaty_signature',
        'category': 'Treaty Signature',
        'severity': 5,
        'active_threshold': 2,
        'description': 'Formal signature (beyond the Aug 2025 initialing) signals or completion',
        'keywords': [
            'peace treaty signed', 'signs peace agreement', 'formal signing ceremony',
            'signature of the peace treaty', 'peace agreement signed armenia azerbaijan',
            'treaty ratified', 'ратификация мирного договора', 'подписание мирного договора',
        ],
    },
    {
        'id': 'referendum_scheduled',
        'category': 'Referendum Milestone',
        'severity': 4,
        'active_threshold': 2,
        'description': 'Constitutional referendum scheduled, campaign launched, or passed',
        'keywords': [
            'referendum scheduled', 'sets referendum date', 'constitutional referendum date',
            'referendum campaign begins', 'referendum passes', 'constitution approved referendum',
            'new constitution adopted', 'референдум назначен', 'дата референдума',
        ],
    },
    {
        'id': 'tripp_groundbreaking',
        'category': 'TRIPP Milestone',
        'severity': 4,
        'active_threshold': 2,
        'description': 'TRIPP construction, customs framework, or operational milestone',
        'keywords': [
            'tripp groundbreaking', 'tripp construction begins', 'trump route construction',
            'tripp development company launch', 'corridor construction starts',
            'customs framework agreed', 'transit agreement signed', 'first cargo tripp',
            'trump route opens', 'tripp operational',
        ],
    },
    {
        'id': 'turkey_border_opening',
        'category': 'Turkiye Normalization',
        'severity': 4,
        'active_threshold': 2,
        'description': 'Armenia-Turkiye border opening or diplomatic normalization milestone',
        'keywords': [
            'turkey armenia border opens', 'border opening armenia turkey',
            'diplomatic relations armenia turkey', 'turkey armenia normalization agreement',
            'margara border', 'alican border crossing', 'kars gyumri railway',
            'turkish airlines yerevan', 'visa free armenia turkey',
            'граница армения турция',
        ],
    },
    {
        'id': 'delimitation_milestone',
        'category': 'Border Delimitation',
        'severity': 3,
        'active_threshold': 2,
        'description': 'Border delimitation commission progress or segment agreements',
        'keywords': [
            'border delimitation agreement', 'delimitation commission agrees',
            'border demarcation progress', 'delimitation protocol signed',
            'border segment agreed', 'делимитация границы',
        ],
    },
    {
        'id': 'humanitarian_steps',
        'category': 'Humanitarian CBM',
        'severity': 2,
        'active_threshold': 2,
        'description': 'Prisoner releases, transit resumption, and other confidence-building steps',
        'keywords': [
            'prisoners released armenia azerbaijan', 'detainees released baku',
            'fuel shipment armenia azerbaijan', 'cargo transit resumed',
            'transit ban lifted', 'goods exchange armenia azerbaijan',
            'обмен пленными',
        ],
    },
    {
        'id': 'eu_milestone',
        'category': 'EU Track',
        'severity': 3,
        'active_threshold': 2,
        'description': 'EU accession process or visa-liberalization milestone',
        'keywords': [
            'eu accession armenia', 'eu membership bill armenia', 'visa liberalization armenia',
            'eu candidate status armenia', 'eu armenia partnership agenda',
            'euma extended', 'eu monitoring mission extended',
            'вступление армении в ес',
        ],
    },
]




# ============================================================
# DIPLOMATIC TRACK -- treaty/referendum gate
# Ukraine discipline: framework triggers + stance negators. A "rules out
# a referendum" headline must never read as a referendum signal.
# ============================================================

TREATY_TRIGGERS = [
    'peace treaty', 'peace agreement', 'peace deal armenia', 'peace process armenia',
    'normalization armenia azerbaijan', 'treaty text', 'signing ceremony',
    'constitutional referendum', 'constitutional amendment armenia',
    'delimitation', 'demarcation', 'peace framework', 'washington agreement',
    'white house agreement armenia', 'мирный договор', 'мирное соглашение',
    'referendum on the constitution',
]

TREATY_NEGATORS = [
    'rules out referendum', 'no referendum', 'rejects the treaty', 'reject peace deal',
    'refuses to sign', 'will not sign', 'suspends talks', 'talks suspended',
    'peace talks frozen', 'walks away from talks', 'referendum impossible',
    'against the peace agreement', 'annul the agreement',
    'отказывается подписывать', 'против мирного договора', 'исключает референдум',
]

_TREATY_SCENARIOS = [
    (0,  'No Active Track'),
    (2,  'Tentative Treaty Signals'),
    (5,  'Active Treaty Track'),
    (9,  'Signature Window Conditions'),
]


def _score_diplomatic_track(scan_data, green_lines_triggered):
    trigger_hits = _check_keywords(scan_data, TREATY_TRIGGERS)
    negator_hits = _check_keywords(scan_data, TREATY_NEGATORS)

    active_green = sum(1 for g in green_lines_triggered if g['status'] == 'ACTIVE')
    signaled_green = sum(1 for g in green_lines_triggered if g['status'] == 'SIGNALED')

    raw = trigger_hits + (active_green * 3) + signaled_green
    score = max(0, raw - (negator_hits * 2))

    scenario = _TREATY_SCENARIOS[0][1]
    for floor, name in _TREATY_SCENARIOS:
        if score >= floor:
            scenario = name

    # De-escalatory modifier, canonical cap of -25 (diplomatic track canon).
    modifier = -min(25, score * 2) if score > 0 else 0
    if negator_hits >= 2 and score < 3:
        scenario = 'Track Contested'
        modifier = 0

    return {
        'score': score,
        'raw_trigger_hits': trigger_hits,
        'negator_hits': negator_hits,
        'scenario': scenario,
        'modifier': modifier,
        'reading': (
            'Treaty-track language present at framework level; stance negators ' +
            ('are actively contesting the track. ' if negator_hits else 'quiet. ') +
            'Reader completes the inference.'
        ) if trigger_hits else 'No treaty-track language detected this cycle.',
    }


# ============================================================
# TRIPP CORRIDOR VECTOR -- portable corridor-vector family, member #1
# Schema is generic on purpose: BRI vectors and the KSA IMEC vector will
# inherit these exact fields, and a future GPI corridor axis reads them
# uniformly. corridor stage: 0 dormant / 1 rhetorical / 2 framework /
# 3 implementation / 4 operational.
# ============================================================

TRIPP_PROGRESS_KEYWORDS = [
    'tripp', 'trump route', 'trump route for international peace',
    'tripp development company', 'tdc armenia', 'corridor construction',
    'zangezur corridor agreement', 'transit framework', 'customs framework',
    'syunik route', 'corridor groundbreaking', 'kars dilucu', 'dilucu railway',
    'first cargo', 'route operational', 'corridor investment', '99-year lease',
    'коридор трампа', 'маршрут трампа',
]

TRIPP_THREAT_KEYWORDS = [
    'iran will not allow', 'iran threatens corridor', 'iran red line',
    'irgc zangezur', 'tehran warns', 'iran rejects trump route',
    'russia rejects corridor', 'moscow opposes corridor', 'fsb corridor control',
    'corridor by force', 'against the trump route', 'sovereignty violated corridor',
    'protest against tripp', 'opposition rejects corridor', 'blockade of the route',
    'коридор угроза', 'против коридора',
]

_TRIPP_BLOCKERS = {
    'iran':       ['iran', 'tehran', 'irgc', 'иран'],
    'russia':     ['russia', 'moscow', 'kremlin', 'россия', 'москва'],
    'opposition': ['opposition', 'dashnak', 'karapetyan', 'kocharyan', 'оппозиция'],
}


def _score_tripp_corridor(scan_data):
    progress = _check_keywords(scan_data, TRIPP_PROGRESS_KEYWORDS)
    threat = _check_keywords(scan_data, TRIPP_THREAT_KEYWORDS)

    blockers = []
    if threat:
        for actor, net in _TRIPP_BLOCKERS.items():
            if _check_keywords(scan_data, net):
                blockers.append(actor)

    # Stage read from progress volume. Framework already exists in the
    # real world (TIF, Jan 2026), so any live progress chatter reads at
    # least stage 2; implementation language lifts to 3.
    if progress >= 6:
        stage, stage_name = 4, 'Operational Signals'
    elif progress >= 4:
        stage, stage_name = 3, 'Implementation'
    elif progress >= 2:
        stage, stage_name = 2, 'Framework Active'
    elif progress >= 1:
        stage, stage_name = 1, 'Rhetorical'
    else:
        stage, stage_name = 0, 'Dormant This Cycle'

    if threat >= 4:
        threat_band = 'high'
    elif threat >= 2:
        threat_band = 'elevated'
    elif threat >= 1:
        threat_band = 'simmering'
    else:
        threat_band = 'quiet'

    if stage >= 2 and threat_band in ('elevated', 'high'):
        status_read = (
            'Corridor progress and blocker pushback are rising together -- '
            'the pattern that has historically preceded pressure campaigns '
            'against infrastructure projects that redraw transit geography.'
        )
    elif stage >= 2:
        status_read = (
            'Corridor implementation signals present with blocker rhetoric '
            'quiet this cycle -- consistent with an uncontested build window.'
        )
    elif threat_band in ('elevated', 'high'):
        status_read = (
            'Blocker rhetoric active while progress signals are quiet -- '
            'consistent with preemptive framing ahead of expected milestones.'
        )
    else:
        status_read = 'Corridor axis quiet this cycle.'

    return {
        # -- portable corridor schema (BRI / IMEC vectors inherit) --
        'corridor_name':    'TRIPP',
        'class':            'us_anchor',
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
# RUSSIA INTERFERENCE + LEVERAGE VECTOR
# Sensor, not referee: measures reporting tempo in BOTH directions
# (interference coverage AND backsliding coverage). Never adjudicates.
# ============================================================

RU_INTERFERENCE_KEYWORDS = [
    'russian interference armenia', 'election interference armenia', 'kiriyenko armenia',
    'disinformation campaign armenia', 'fake websites armenia', 'imported voters',
    'hybrid operation armenia', 'influence operation armenia', 'kremlin meddling',
    'fsb plot armenia', 'coup plot armenia', 'russian oligarch armenia',
    'church kremlin armenia', 'moscow backs opposition armenia',
    'вмешательство в выборы армении', 'российское влияние армения',
]

RU_LEVER_KEYWORDS = [
    'gyumri base', '102nd military base', 'russian border guards armenia',
    'russian railways armenia', 'south caucasus railway', 'gazprom armenia',
    'gas price armenia', 'metsamor', 'rosatom armenia', 'nuclear fuel armenia',
    'eeu armenia', 'eurasian economic union armenia',
    'газпром армения', 'мецамор', 'база в гюмри',
]

BACKSLIDE_KEYWORDS = [
    'opposition leader arrested armenia', 'prosecution of opposition armenia',
    'archbishop arrested', 'karapetyan arrested', 'media pressure armenia',
    'political prisoners armenia', 'crackdown on opposition armenia',
    'democratic backsliding armenia', 'арест оппозиции армения',
]


def _score_russia_pressure(scan_data):
    interference_tempo = _check_keywords(scan_data, RU_INTERFERENCE_KEYWORDS)
    lever_events = _check_keywords(scan_data, RU_LEVER_KEYWORDS)
    backslide_tempo = _check_keywords(scan_data, BACKSLIDE_KEYWORDS)

    combined = interference_tempo + lever_events
    if combined >= 7:
        band = 'high'
    elif combined >= 4:
        band = 'elevated'
    elif combined >= 1:
        band = 'simmering'
    else:
        band = 'quiet'

    reading_parts = []
    if interference_tempo:
        reading_parts.append(
            f'Interference-reporting tempo at {interference_tempo} corroborated signals '
            '-- a level consistent with active influence-operation coverage cycles.')
    if lever_events:
        reading_parts.append(
            f'Infrastructure/basing lever coverage at {lever_events} signals '
            '(rail, gas, Gyumri, Metsamor class).')
    if backslide_tempo:
        reading_parts.append(
            f'Counter-direction honesty: domestic-crackdown reporting also active '
            f'({backslide_tempo} signals). The sensor measures tempo both ways and '
            'adjudicates neither.')
    reading = ' '.join(reading_parts) if reading_parts else \
        'Russia-pressure reporting quiet this cycle.'

    return {
        'band': band,
        'interference_tempo': interference_tempo,
        'lever_events': lever_events,
        'backslide_tempo': backslide_tempo,
        'reading': reading,
    }


# ============================================================
# WESTWARD DRIFT AXIS (custom drift axis -- the platform's cleanest)
# ============================================================

WEST_SIGNALS = [
    'eu accession armenia', 'eu membership armenia', 'eu candidate armenia',
    'visa liberalization armenia', 'euma', 'eu monitoring mission armenia',
    'csto exit', 'csto withdrawal', 'leaves csto', 'csto frozen armenia',
    'france arms armenia', 'caesar howitzer armenia', 'india arms armenia',
    'us strategic partnership armenia', 'us armenia charter', 'nato armenia cooperation',
    'western pivot armenia', 'real armenia',
]

RUSSIA_PULL_SIGNALS = [
    'csto return armenia', 'rejoins csto', 'deepen eeu armenia',
    'moscow visit pashinyan', 'russian mediation armenia', 'putin pashinyan meeting',
    'russia armenia alliance restored', 'pro-russian government armenia',
    'вернуться в одкб', 'союз с россией армения',
]


def _score_westward_drift(scan_data):
    west = _check_keywords(scan_data, WEST_SIGNALS)
    pull = _check_keywords(scan_data, RUSSIA_PULL_SIGNALS)
    drift_index = west - pull   # positive = drifting west

    if drift_index >= 5:
        band, posture = 'anchored_west', 'Westward anchoring signals dominant'
    elif drift_index >= 2:
        band, posture = 'drifting_west', 'Westward drift signals lead the tape'
    elif drift_index <= -2:
        band, posture = 'moscow_pull', 'Moscow-pull signals lead the tape'
    else:
        band, posture = 'contested', 'Drift direction contested this cycle'

    return {
        'west_signals': west,
        'russia_pull_signals': pull,
        'drift_index': drift_index,
        'band': band,
        'posture': posture,
    }


# ============================================================
# IRAN CONDITIONAL-BUFFER VECTOR
# Iran backed Armenia for years BECAUSE Armenia blocked the pan-Turkic
# land bridge. TRIPP breaks that logic. Iranian rhetoric intensity on
# Zangezur/TRIPP is itself the flip-meter from buffer toward friction.
# ============================================================

IRAN_COOPERATION_KEYWORDS = [
    'iran armenia gas swap', 'gas for electricity', 'iran armenia trade',
    'north-south corridor armenia', 'meghri free zone', 'iran armenia agreement',
    'araghchi yerevan', 'iranian minister armenia', 'iran armenia cooperation',
    'iran armenia border trade', 'иран армения сотрудничество',
]

IRAN_FLIP_KEYWORDS = [
    'iran warns corridor', 'iran threatens', 'irgc zangezur', 'iran red line',
    'tehran rejects tripp', 'iran against trump route', 'iran military exercise aras',
    'iran will not tolerate', 'geopolitical changes region iran',
    'иран предупреждает коридор', 'красная линия ирана',
]


def _score_iran_buffer(scan_data):
    cooperation = _check_keywords(scan_data, IRAN_COOPERATION_KEYWORDS)
    flip = _check_keywords(scan_data, IRAN_FLIP_KEYWORDS)

    # flip_meter 0-10: flip rhetoric weighted double against cooperation.
    flip_meter = max(0, min(10, (flip * 2) - cooperation + 2)) if flip else 0

    if flip >= 4:
        posture = 'flipping_friction'
        reading = ('Iranian corridor rhetoric at intensity levels consistent with '
                   'the buffer relationship flipping toward friction as TRIPP advances.')
    elif flip >= 2:
        posture = 'strained_buffer'
        reading = ('Cooperative buffer under strain -- Iranian pushback on the '
                   'corridor is active while bilateral cooperation channels remain open.')
    elif cooperation >= 2:
        posture = 'cooperative_buffer'
        reading = ('Buffer relationship reading cooperative this cycle -- trade and '
                   'energy channels active, corridor rhetoric quiet.')
    else:
        posture = 'quiet'
        reading = 'Iran axis quiet this cycle.'

    return {
        'posture': posture,
        'cooperation_signals': cooperation,
        'flip_signals': flip,
        'flip_meter': flip_meter,
        'reading': reading,
    }


# ============================================================
# TURKIYE NORMALIZATION VECTOR -- feeds spoke:turkey:armenia polarity
# ============================================================

TURKEY_PROGRESS_KEYWORDS = [
    'turkey armenia normalization', 'border opening turkey armenia',
    'armenia turkey diplomatic relations', 'turkish airlines yerevan',
    'visa facilitation armenia turkey', 'margara', 'alican crossing',
    'kars gyumri', 'kars dilucu railway', 'ankara yerevan talks',
    'special envoys armenia turkey', 'армения турция нормализация',
]

TURKEY_STALL_KEYWORDS = [
    'turkey suspends normalization', 'border remains closed', 'normalization frozen',
    'turkey precondition armenia', 'ankara conditions normalization',
    'no progress armenia turkey',
]


def _score_turkey_normalization(scan_data):
    progress = _check_keywords(scan_data, TURKEY_PROGRESS_KEYWORDS)
    stall = _check_keywords(scan_data, TURKEY_STALL_KEYWORDS)

    if progress >= 3 and progress > stall:
        relationship, band = 'alignment', 'warming'
        level = 2
        top_signal = 'Armenia-Turkiye normalization signals active (border/rail/flights class)'
    elif progress >= 1 and progress > stall:
        relationship, band = 'alignment', 'thawing'
        level = 1
        top_signal = 'Normalization track showing early progress signals'
    elif stall > progress:
        relationship, band = 'friction', 'stalled'
        level = 1
        top_signal = 'Normalization track reading stalled this cycle'
    else:
        relationship, band = 'friction', 'quiet'
        level = 0
        top_signal = 'Armenia-Turkiye axis quiet this cycle'

    return {
        'relationship': relationship,   # feeds spoke:turkey:armenia (REL_LABEL safe)
        'band': band,
        'level': level,                 # 0-5 scale, periphery reads are low-band
        'progress_signals': progress,
        'stall_signals': stall,
        'top_signal': top_signal,
    }


# ============================================================
# REFERENDUM CLOCK -- MULTIPLIER, never a standalone signal
# Port of Turkey's election-clock discipline: a scheduled referendum
# during a quiet period contributes nothing. It only amplifies an
# already-active stack.
# ============================================================

REFERENDUM_CLOCK_KEYWORDS = [
    'referendum date', 'referendum scheduled', 'referendum campaign',
    'vote on the constitution', 'constitutional vote armenia',
    'referendum this year', 'referendum bill', 'referendum question',
    'snap elections armenia', 'early elections armenia', 'snap parliamentary election',
    'draft constitution armenia',
    'дата референдума', 'референдум по конституции',
]


def _referendum_clock_multiplier(scan_data, red_lines_triggered):
    hits = _check_keywords(scan_data, REFERENDUM_CLOCK_KEYWORDS)
    stack_active = any(r['status'] in ('BREACHED', 'APPROACHING') for r in red_lines_triggered)
    if hits >= 2 and stack_active:
        return {'active': True, 'multiplier': 0.20, 'hits': hits,
                'reading': 'Referendum-window conditions amplifying an active signal stack.'}
    if hits >= 1 and stack_active:
        return {'active': True, 'multiplier': 0.10, 'hits': hits,
                'reading': 'Early referendum-clock chatter amplifying an active stack.'}
    return {'active': False, 'multiplier': 0.0, 'hits': hits,
            'reading': ''}


# ============================================================
# RUMINT -- pre-leak / concept-seeding chatter (light port)
# Armenia is RUMINT-rich: coup plots, church intrigue, oligarch arrests.
# ============================================================

RUMINT_KEYWORDS = [
    'coup rumor armenia', 'plot against pashinyan', 'assassination plot armenia',
    'secret plan armenia', 'leaked document armenia', 'sources say armenia coup',
    'preparing unrest armenia', 'church plot', 'oligarch plot armenia',
]


def _score_rumint(scan_data):
    hits = _check_keywords(scan_data, RUMINT_KEYWORDS)
    if hits >= 3:
        return {'active': True, 'band': 'elevated', 'hits': hits,
                'label': 'Destabilization-chatter cluster',
                'reading': ('Plot/coup chatter clustering above baseline -- '
                            'historically precedes either arrests or nothing; '
                            'flagged, down-weighted, never decisive.')}
    if hits >= 1:
        return {'active': True, 'band': 'simmering', 'hits': hits,
                'label': 'Scattered destabilization chatter',
                'reading': 'Isolated plot chatter present; below cluster threshold.'}
    return {'active': False, 'band': 'off', 'hits': 0, 'label': '', 'reading': ''}


# ============================================================
# SO WHAT -- the analyst voice (estimative, precedent-anchored)
# ============================================================

def _build_so_what(scan_data, red_lines, green_lines, diplomatic, tripp,
                   russia, drift, iran, turkey, ref_clock):
    breached = [r for r in red_lines if r['status'] == 'BREACHED']
    approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
    active_green = [g for g in green_lines if g['status'] == 'ACTIVE']

    # Priority ladder
    if breached and any(r['severity'] >= 5 for r in breached):
        priority = 'critical'
    elif breached:
        priority = 'high'
    elif approaching or russia['band'] in ('elevated', 'high') \
            or iran['posture'] == 'flipping_friction':
        priority = 'elevated'
    else:
        priority = 'normal'

    # Scenario line
    if breached:
        cats = ', '.join(sorted({r['category'] for r in breached}))
        scenario = f'Red-line breach: {cats}'
    elif diplomatic['scenario'] in ('Active Treaty Track', 'Signature Window Conditions') \
            and not approaching:
        scenario = 'Treaty implementation window -- ' + diplomatic['scenario']
    elif approaching:
        cats = ', '.join(sorted({r['category'] for r in approaching}))
        scenario = f'Pressure approaching: {cats}'
    else:
        scenario = 'Baseline -- post-initialing implementation period'

    # Assessment paragraph -- dynamic, estimative, both-directions honest.
    parts = []
    parts.append(
        'The Armenia read is a peace-implementation contest, not a ceasefire watch: '
        'the treaty was initialed in August 2025, the TRIPP framework followed in '
        'January 2026, and the gating item is a constitutional referendum the '
        'governing coalition cannot call from parliament alone.')
    if diplomatic['score'] > 0:
        parts.append(
            f"Treaty track: {diplomatic['scenario']} "
            f"({diplomatic['raw_trigger_hits']} framework signals, "
            f"{diplomatic['negator_hits']} negators).")
    if tripp['stage'] >= 1 or tripp['threat_band'] != 'quiet':
        parts.append(f"TRIPP corridor: {tripp['stage_name']} with blocker rhetoric "
                     f"{tripp['threat_band']}"
                     + (f" ({', '.join(tripp['blocker_actors'])})" if tripp['blocker_actors'] else '')
                     + '.')
    if russia['band'] != 'quiet':
        parts.append(f"Russia pressure: {russia['band']}. {russia['reading']}")
    if drift['band'] != 'contested' or drift['west_signals'] or drift['russia_pull_signals']:
        parts.append(f"Alignment drift: {drift['posture'].lower()} "
                     f"(index {drift['drift_index']:+d}).")
    if iran['posture'] not in ('quiet',):
        parts.append(f"Iran buffer: {iran['reading']}")
    if turkey['band'] not in ('quiet',):
        parts.append(f"Turkiye normalization reading {turkey['band']}.")
    if ref_clock['active']:
        parts.append(ref_clock['reading'])
    if active_green:
        names = ', '.join(g['category'] for g in active_green)
        parts.append(f'De-escalation markers active: {names}.')
    if not breached and not approaching and not active_green \
            and russia['band'] == 'quiet' and tripp['stage'] == 0:
        parts.append('All vectors quiet this cycle. Silence is a valid analytical '
                     'output; manufactured signal is not.')

    return {
        'scenario': scenario,
        'priority': priority,
        'assessment': ' '.join(parts),
        'situation': scenario,
        'breached_count': len(breached),
        'approaching_count': len(approaching),
        'active_green_count': len(active_green),
        'disclaimer': CONVERGENCE_DISCLAIMER,
    }


# ============================================================
# TOP SIGNALS -- canonical schema (short_text / long_text / priority / category)
# ============================================================

def _build_top_signals(red_lines, green_lines, diplomatic, tripp, russia,
                       drift, iran, turkey, scan_data):
    signals = []

    for r in red_lines:
        if r['status'] == 'BREACHED':
            signals.append({
                'priority': 1,
                'category': r['id'],
                'short_text': f"RED LINE BREACHED: {r.get('plain') or r['category']} ({r['outlets']} outlets)",
                'long_text': f"{r['description']}. Carried by {r['outlets']} outlets this cycle "
                             f"-- a level consistent with the tripwire condition being live.",
                'pressure_type': 'kinetic' if r['id'] in
                    ('border_kinetic', 'corridor_by_force') else 'diplomatic',
            })
    for r in red_lines:
        if r['status'] == 'APPROACHING':
            signals.append({
                'priority': 2,
                'category': r['id'],
                'short_text': f"Approaching: {r['category']}",
                'long_text': f"{r['description']}. {r['trigger']}",
                'pressure_type': 'kinetic' if r['id'] in
                    ('border_kinetic', 'corridor_by_force') else 'diplomatic',
            })

    for g in green_lines:
        if g['status'] == 'ACTIVE':
            signals.append({
                'priority': 2,
                'category': g['id'],
                'short_text': f"GREEN LINE: {g['category']} active ({g['outlets']} outlets)",
                'long_text': f"{g['description']}. De-escalatory marker active this cycle.",
                'pressure_type': 'diplomatic',
            })

    if tripp['stage'] >= 2 or tripp['threat_band'] in ('elevated', 'high'):
        signals.append({
            'priority': 2 if tripp['threat_band'] in ('elevated', 'high') else 3,
            'category': 'tripp_corridor',
            'short_text': f"TRIPP: {tripp['stage_name']} / blockers {tripp['threat_band']}",
            'long_text': tripp['status_read'],
            'pressure_type': 'economic',
        })

    if russia['band'] in ('elevated', 'high'):
        signals.append({
            'priority': 2,
            'category': 'russia_pressure',
            'short_text': f"Russia pressure {russia['band']} "
                          f"({russia['interference_tempo']} interference / "
                          f"{russia['lever_events']} lever signals)",
            'long_text': russia['reading'],
            'pressure_type': 'diplomatic',
        })

    if drift['band'] in ('drifting_west', 'anchored_west', 'moscow_pull'):
        signals.append({
            'priority': 3,
            'category': 'westward_drift',
            'short_text': f"Alignment drift: {drift['band']} (index {drift['drift_index']:+d})",
            'long_text': drift['posture'],
            'pressure_type': 'diplomatic',
        })

    if iran['posture'] in ('strained_buffer', 'flipping_friction'):
        signals.append({
            'priority': 2 if iran['posture'] == 'flipping_friction' else 3,
            'category': 'iran_buffer',
            'short_text': f"Iran buffer: {iran['posture']} (flip meter {iran['flip_meter']}/10)",
            'long_text': iran['reading'],
            'pressure_type': 'diplomatic',
        })

    if turkey['band'] in ('warming', 'thawing'):
        signals.append({
            'priority': 3,
            'category': 'turkey_normalization',
            'short_text': f"Turkiye normalization {turkey['band']}",
            'long_text': turkey['top_signal'],
            'pressure_type': 'diplomatic',
        })

    signals.sort(key=lambda s: s['priority'])
    return signals[:8]


# ============================================================
# CROSS-THEATER FINGERPRINT SLICES
# The tracker composes and writes; the interpreter supplies the slices.
# ============================================================

def _build_fingerprints(red_lines, green_lines, diplomatic, tripp, russia,
                        drift, iran, turkey, scan_data):
    return {
        'westward_drift': {
            'band': drift['band'],
            'drift_index': drift['drift_index'],
        },
        'tripp_corridor': {
            'corridor_name': tripp['corridor_name'],
            'class': tripp['class'],
            'stage': tripp['stage'],
            'threat_band': tripp['threat_band'],
            'blocker_actors': tripp['blocker_actors'],
        },
        'iran_facing': {
            'posture': iran['posture'],
            'tripp_flip_meter': iran['flip_meter'],
            'cooperation_signals': iran['cooperation_signals'],
        },
        'turkey_spoke': {
            'level': turkey['level'],
            'relationship': turkey['relationship'],
            'top_signal': turkey['top_signal'],
        },
        'russia_pressure': {
            'band': russia['band'],
            'interference_tempo': russia['interference_tempo'],
            'lever_events': russia['lever_events'],
        },
    }


# ============================================================
# DATED BACKGROUND TRACKS (v1.1.0) -- what has already happened
# ============================================================
# Background, never this cycle's evidence. The scan asks whether they hold.

PEACE_BASELINE = {
    'as_of': '2026-11-03',
    'treaty': ('Initialled in Washington in August 2025, not signed. Baku\'s precondition: '
               'Armenia removes what it reads as territorial claims from its constitution.'),
    'rules': ('Putting a new constitution to referendum needs two-thirds of parliament (70 of '
              '105). Civil Contract won 64 seats on June 7, 2026 -- six short -- and the '
              'opposition has ruled out support. A referendum also needs "yes" from 25% of '
              'all registered voters.'),
    'status': ('Oct 22: Pashinyan floated snap elections to win the missing seats. Oct 29: he '
               'called early elections unlikely and promised an offer the opposition "cannot '
               'refuse". Draft constitution due by end-2026; signing targeted for 2027-28.'),
    'tripp': ('TRIPP: parliament ratified the US-Armenia framework in late October (US holds 74% '
              'of the development company, 49+ years). Groundbreaking now expected early 2027.'),
    'sources': ['https://oc-media.org/explainer-could-armenia-have-a-snap-election-as-soon-as-next-year/',
                'https://report.az/en/region/tripp-groundbreaking-expected-in-early-2027'],
}

LEVER_BASELINE = {
    'as_of': '2026-11-03',
    'what': ('Armenia buys ~2.7 bcm/yr of Russian gas at a fixed $177.5 per 1,000 m3 under a deal '
             'that runs to end-2026 / early 2027; another ~0.5 bcm comes from Iran in a '
             'gas-for-electricity swap.'),
    'status': ('Late September: Armenian press, citing Russian sources, reported a possible '
               'permanent cutoff from Nov 1 unless Yerevan met Moscow\'s demands (drop the Gyumri '
               'base debate, the EU law, prosecutions of pro-Russian figures). Nov 2: Gazprom '
               'Armenia said supplies continue as usual. The threat did not materialise; the '
               'price deal\'s expiry is the next real date.'),
    'constraint': ('Aug 2026 government programme downgraded Russia from "strategic alliance" '
                   'to a "transforming" partnership; CSTO participation frozen since 2024.'),
    'sources': ['https://1news.az/en/news/20261102124008131-Gazprom-Gas-supplies-to-Armenia-continue-as-usual',
                'https://oc-media.org/armenia-downgrades-relations-with-russia-in-new-government-programme/'],
}


def _line(lines, line_id):
    return next((l for l in lines if l['id'] == line_id), {})


def _peace_track(red_lines, green_lines, diplomatic, ref_clock):
    tc = _line(red_lines, 'treaty_collapse')
    cc = _line(red_lines, 'constitutional_crisis')
    sig = _line(green_lines, 'treaty_signature')
    ref = _line(green_lines, 'referendum_scheduled')
    if tc.get('status') in ('BREACHED', 'APPROACHING') or cc.get('status') == 'BREACHED':
        status, read = 'strain', ('Collapse or crisis language is in the reporting this cycle -- the '
                                  'peace track is being contested, not just delayed.')
    elif sig.get('status') == 'ACTIVE' or ref.get('status') == 'ACTIVE':
        status, read = 'holding', ('A signature or referendum milestone is carried by two or more '
                                   'outlets -- the gate is moving.')
    elif diplomatic.get('negator_hits', 0) >= 1 or cc.get('status') == 'APPROACHING':
        status, read = 'contested', ('The track is alive but contested: rejection language sits next '
                                     'to the treaty talk. The referendum math has not changed.')
    elif diplomatic.get('score', 0) > 0:
        status, read = 'holding', ('Treaty-track talk without rejection language. The gate is still '
                                   'the referendum: six seats short.')
    else:
        status, read = 'quiet', ('The treaty is not in this scan\'s reporting. Unread, not stalled -- '
                                 'the referendum gate is the standing baseline.')
    if ref_clock.get('active'):
        read += ' Referendum / snap-election talk is live alongside it.'
    return {'status': status, 'read': read, 'title': 'THE PEACE GATE — TREATY, REFERENDUM, TRIPP',
            'evidence': (tc.get('evidence') or []) + (sig.get('evidence') or []) + (ref.get('evidence') or []),
            'baseline': PEACE_BASELINE}


def _lever_track(red_lines, russia):
    hl = _line(red_lines, 'russian_hard_lever')
    st = hl.get('status', 'QUIET')
    if st == 'BREACHED':
        status, read = 'strain', 'Two or more outlets report Moscow pulling a hard lever this cycle.'
    elif st == 'APPROACHING' or russia.get('band') in ('elevated', 'high'):
        status, read = 'contested', ('Lever language is in the reporting (gas, rail, Gyumri, Metsamor '
                                     'class); no confirmed cut.')
    elif russia.get('band') == 'simmering':
        status, read = 'holding', 'Russia-lever reporting is low; supplies and basing unchanged.'
    else:
        status, read = 'quiet', 'Russian levers are not in this scan\'s reporting. Unread, not calm.'
    return {'status': status, 'read': read, 'title': 'MOSCOW\'S LEVERS — GAS, RAIL, GYUMRI',
            'evidence': hl.get('evidence') or [], 'baseline': LEVER_BASELINE}


# ============================================================
# FOUR WHEELS (v1.1.0) -- Armenia as a spoke
# ============================================================
# One payload per hub, written by the tracker to spoke:{hub}:armenia (30h TTL).
# Level = how hard that hub is working this spoke THIS cycle, 0-4. No wheel
# may print L5 from here: nothing on these vectors is hostilities.

_BAND_LEVEL = {'quiet': 0, 'simmering': 1, 'elevated': 2, 'high': 3}
_IRAN_LEVEL = {'quiet': 0, 'cooperative_buffer': 1, 'strained_buffer': 2, 'flipping_friction': 3}


def build_spokes(red_lines, russia, iran, turkey, tripp, drift):
    hl = _line(red_lines, 'russian_hard_lever').get('status')
    ru_lvl = _BAND_LEVEL.get(russia.get('band'), 0)
    if hl == 'BREACHED':
        ru_lvl = max(ru_lvl, 4)
    elif hl == 'APPROACHING':
        ru_lvl = max(ru_lvl, 3)
    ict = _line(red_lines, 'iran_corridor_threat').get('status')
    ir_lvl = _IRAN_LEVEL.get(iran.get('posture'), 0)
    if ict in ('BREACHED', 'APPROACHING'):
        ir_lvl = max(ir_lvl, 3)
    us_lvl = min(3, int(tripp.get('stage', 0) or 0))
    return {
        'russia': {'level': min(ru_lvl, 4), 'node_class': 'friction',
                   'relationship': 'friction' if drift.get('band') != 'moscow_pull' else 'alignment',
                   'top_signal': (_line(red_lines, 'russian_hard_lever').get('plain')
                                  if hl in ('BREACHED', 'APPROACHING')
                                  else f"Russia pressure {russia.get('band', 'quiet')}; drift {drift.get('band', 'contested')}"),
                   'note': 'Moscow\'s levers: gas price, rail concession, Gyumri base, Metsamor fuel.'},
        'iran': {'level': ir_lvl, 'node_class': 'conditional_buffer',
                 'relationship': 'friction' if ir_lvl >= 2 else 'buffer',
                 'top_signal': f"Iran posture: {iran.get('posture', 'quiet').replace('_', ' ')} "
                               f"(flip meter {iran.get('flip_meter', 0)}/10)",
                 'note': 'Iran backed Armenia as a block on the pan-Turkic land bridge; TRIPP tests that.'},
        'turkey': {'level': int(turkey.get('level', 0) or 0), 'node_class': 'normalisation_track',
                   'relationship': turkey.get('relationship', 'friction'),
                   'top_signal': turkey.get('top_signal', ''),
                   'note': 'Normalisation is chained to the Azerbaijan treaty.'},
        'us': {'level': us_lvl, 'node_class': 'corridor_anchor', 'relationship': 'anchor',
               'top_signal': f"TRIPP: {tripp.get('stage_name', 'Dormant')}; blockers {tripp.get('threat_band', 'quiet')}",
               'note': 'The US holds 74% of the TRIPP development company.'},
    }


def _top_indicator(red_lines, peace, lever, iran, spokes, health):
    breached = sorted([r for r in red_lines if r['status'] == 'BREACHED'], key=lambda r: -r['severity'])
    approaching = sorted([r for r in red_lines if r['status'] == 'APPROACHING'], key=lambda r: -r['severity'])
    if breached:
        r = breached[0]
        line = (f"{r.get('plain') or r['category']} -- carried by {r['outlets']} outlets this cycle. "
                'A corroborated tripwire, not a forecast.')
    elif peace['status'] == 'strain':
        line = 'The peace track is under strain: collapse or crisis language is in the reporting.'
    elif approaching:
        r = approaching[0]
        line = (f"Closest tripwire: {r.get('plain') or r['category']} -- not breached; "
                f"{r['trigger'].rstrip('.').lower()}.")
    else:
        line = ('The peace deal still waits on a referendum Pashinyan cannot call -- six seats short -- '
                'and no tripwire is corroborated this cycle.')
    hot = sorted(((h, s['level']) for h, s in spokes.items() if s['level'] >= 2), key=lambda x: -x[1])
    if len(hot) >= 2:
        line += (' Two or more outside hubs are pressing at once ('
                 + ', '.join(h.title() if h != 'us' else 'US' for h, _ in hot) + ').')
    if health.get('thin'):
        line = 'Thin read -- ' + line
    return line


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def interpret_signals(scan_data):
    """Main entry point. Called from rhetoric_tracker_armenia.py.
    Returns interpretation dict with canonical top_signals."""
    try:
        red_lines = _score_red_lines(scan_data)
        green_lines = _score_green_lines(scan_data)
        diplomatic = _score_diplomatic_track(scan_data, green_lines)
        tripp = _score_tripp_corridor(scan_data)
        russia = _score_russia_pressure(scan_data)
        drift = _score_westward_drift(scan_data)
        iran = _score_iran_buffer(scan_data)
        turkey = _score_turkey_normalization(scan_data)
        ref_clock = _referendum_clock_multiplier(scan_data, red_lines)
        rumint = _score_rumint(scan_data)
        health = corpus_health(scan_data, _corpus(scan_data), min_articles=20, min_outlets=4)
        peace = _peace_track(red_lines, green_lines, diplomatic, ref_clock)
        lever = _lever_track(red_lines, russia)
        spokes = build_spokes(red_lines, russia, iran, turkey, tripp, drift)
        top_indicator = _top_indicator(red_lines, peace, lever, iran, spokes, health)

        so_what = _build_so_what(scan_data, red_lines, green_lines, diplomatic,
                                 tripp, russia, drift, iran, turkey, ref_clock)
        top_signals = _build_top_signals(red_lines, green_lines, diplomatic,
                                         tripp, russia, drift, iran, turkey,
                                         scan_data)
        fingerprints = _build_fingerprints(red_lines, green_lines, diplomatic,
                                           tripp, russia, drift, iran, turkey,
                                           scan_data)

        breached = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']

        # Composite modifier: de-escalatory diplomatic modifier + red load,
        # amplified by the referendum clock when active.
        red_load = sum(r['severity'] for r in breached) * 2 \
                 + sum(r['severity'] for r in approaching)
        composite_modifier = diplomatic['modifier'] + red_load
        composite_modifier = int(round(
            composite_modifier * (1.0 + ref_clock['multiplier'])))

        return {
            'so_what':             so_what,
            'top_signals':         top_signals,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in red_lines
                                          if r['status'] in ('BREACHED', 'APPROACHING')), default=0),
                'rule':              'BREACHED = breach language from 2+ outlets; APPROACHING = 1 outlet; WATCHING = social only.',
            },
            'green_lines': {
                'triggered':        green_lines,
                'active_count':     len(active_gl),
                'signaled_count':   len([g for g in green_lines
                                         if g['status'] == 'SIGNALED']),
                'diplomatic_score': diplomatic['score'],
            },
            'diplomatic_track':           diplomatic,
            'tripp_corridor':             tripp,
            'russia_pressure':            russia,
            'westward_drift':             drift,
            'iran_buffer':                iran,
            'turkey_normalization':       turkey,
            'referendum_clock':           ref_clock,
            'rumint':                     rumint,
            'top_indicator':              top_indicator,
            'thin_read':                  health['thin'],
            'corpus_health':              health,
            'peace_track':                peace,
            'lever_track':                lever,
            'spokes':                     spokes,
            'cross_theater_fingerprints': fingerprints,
            'composite_modifier':         composite_modifier,
            'interpreter_version':        INTERPRETER_VERSION,
            'interpreted_at':             datetime.now(timezone.utc).isoformat(),
            'disclaimer':                 CONVERGENCE_DISCLAIMER,
        }

    except Exception as e:
        print(f'[Armenia Interpreter] Error: {str(e)[:120]}')
        return {
            'so_what': {
                'scenario':           'Interpreter error',
                'priority':           'normal',
                'assessment':         str(e)[:200],
                'situation':          'Interpreter error',
                'breached_count':     0,
                'approaching_count':  0,
                'active_green_count': 0,
                'disclaimer':         CONVERGENCE_DISCLAIMER,
            },
            'top_signals':                [],
            'red_lines':                  {'triggered': [], 'breached_count': 0,
                                           'approaching_count': 0, 'highest_severity': 0},
            'green_lines':                {'triggered': [], 'active_count': 0,
                                           'signaled_count': 0, 'diplomatic_score': 0},
            'diplomatic_track':           {'score': 0, 'scenario': 'Unknown',
                                           'modifier': 0, 'negator_hits': 0},
            'tripp_corridor':             {'corridor_name': 'TRIPP', 'class': 'us_anchor',
                                           'stage': 0, 'stage_name': 'Unknown',
                                           'threat_band': 'quiet', 'blocker_actors': [],
                                           'progress_signals': 0, 'threat_signals': 0,
                                           'status_read': ''},
            'russia_pressure':            {'band': 'quiet', 'interference_tempo': 0,
                                           'lever_events': 0, 'backslide_tempo': 0,
                                           'reading': ''},
            'westward_drift':             {'band': 'contested', 'drift_index': 0,
                                           'west_signals': 0, 'russia_pull_signals': 0,
                                           'posture': 'Unknown'},
            'iran_buffer':                {'posture': 'quiet', 'flip_meter': 0,
                                           'cooperation_signals': 0, 'flip_signals': 0,
                                           'reading': ''},
            'turkey_normalization':       {'relationship': 'friction', 'band': 'quiet',
                                           'level': 0, 'progress_signals': 0,
                                           'stall_signals': 0, 'top_signal': ''},
            'referendum_clock':           {'active': False, 'multiplier': 0.0, 'hits': 0,
                                           'reading': ''},
            'rumint':                     {'active': False, 'band': 'off', 'hits': 0,
                                           'label': '', 'reading': ''},
            'cross_theater_fingerprints': {},
            'composite_modifier':         0,
            'interpreter_version':        INTERPRETER_VERSION,
            'error':                      str(e)[:200],
        }
