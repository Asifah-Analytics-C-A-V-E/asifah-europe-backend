"""
Armenia Signal Interpreter v1.0.0 (Jul 12 2026)
================================================
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

INTERPRETER_VERSION = '1.0.0'

CONVERGENCE_DISCLAIMER = (
    'This composite is a CONVERGENCE indicator, NOT a probability of action. '
    'Active signals indicate pressure conditions are present; they do not '
    'predict whether or when any specific outcome will occur.'
)


# ============================================================
# CORPUS KEYWORD MATCHER (Turkey clone, Armenia article keys)
# ============================================================

def _check_keywords(scan_data, keywords):
    """Match keywords against the scan corpus. URL slugs are de-hyphenated
    so multi-word keywords match headline slugs (the Ukraine v1.2 lesson)."""
    if not keywords:
        return 0
    corpus_parts = []
    for key in ('articles_en', 'articles_hy', 'articles_ru'):
        for art in (scan_data.get(key) or []):
            corpus_parts.append((art.get('title') or '').lower())
            corpus_parts.append((art.get('description') or '').lower())
            corpus_parts.append((art.get('summary') or '').lower())
            corpus_parts.append((art.get('content') or '').lower())
            _url = (art.get('url') or art.get('link') or '').lower()
            if _url:
                corpus_parts.append(
                    _url.replace('-', ' ').replace('_', ' ').replace('/', ' '))
    for key in ('reddit_signals', 'telegram_messages', 'bluesky_signals'):
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
# RED LINES -- escalation tripwires
# status ladder: QUIET -> APPROACHING (1 hit) -> BREACHED (>= threshold)
# ============================================================

RED_LINES = [
    {
        'id': 'treaty_collapse',
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
        'category': 'Russian Hard Lever',
        'severity': 3,
        'breach_threshold': 2,
        'description': 'Moscow pulling an infrastructure or basing lever (Gyumri, rail, gas, Metsamor fuel)',
        'keywords': [
            'gyumri base reinforcement', '102nd base', 'russian troops armenia increase',
            'gazprom cuts armenia', 'gas cutoff armenia', 'gas price armenia gazprom',
            'russian railways armenia suspend', 'south caucasus railway halt',
            'metsamor fuel halt', 'rosatom suspends', 'russian border guards refuse',
            'газпром армения', 'южно-кавказская железная дорога', 'мецамор',
        ],
    },
    {
        'id': 'iran_corridor_threat',
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


def _score_red_lines(scan_data):
    out = []
    for line in RED_LINES:
        hits = _check_keywords(scan_data, line['keywords'])
        if hits >= line['breach_threshold']:
            status = 'BREACHED'
        elif hits >= 1:
            status = 'APPROACHING'
        else:
            status = 'QUIET'
        out.append({
            'id': line['id'], 'category': line['category'],
            'severity': line['severity'], 'status': status,
            'hits': hits, 'description': line['description'],
        })
    return out


def _score_green_lines(scan_data):
    out = []
    for line in GREEN_LINES:
        hits = _check_keywords(scan_data, line['keywords'])
        if hits >= line['active_threshold']:
            status = 'ACTIVE'
        elif hits >= 1:
            status = 'SIGNALED'
        else:
            status = 'QUIET'
        out.append({
            'id': line['id'], 'category': line['category'],
            'severity': line['severity'], 'status': status,
            'hits': hits, 'description': line['description'],
        })
    return out


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
            f'Interference-reporting tempo at {interference_tempo} matched signals '
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
    'дата референдума', 'референдум по конституции',
]


def _referendum_clock_multiplier(scan_data, red_lines_triggered):
    hits = _check_keywords(scan_data, REFERENDUM_CLOCK_KEYWORDS)
    stack_active = any(r['status'] != 'QUIET' for r in red_lines_triggered)
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
                'short_text': f"RED LINE BREACHED: {r['category']} ({r['hits']} signals)",
                'long_text': f"{r['description']}. {r['hits']} matched signals this cycle "
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
                'long_text': f"{r['description']}. Early signals present ({r['hits']}), "
                             f"below breach threshold.",
                'pressure_type': 'kinetic' if r['id'] in
                    ('border_kinetic', 'corridor_by_force') else 'diplomatic',
            })

    for g in green_lines:
        if g['status'] == 'ACTIVE':
            signals.append({
                'priority': 2,
                'category': g['id'],
                'short_text': f"GREEN LINE: {g['category']} active ({g['hits']} signals)",
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
                                          if r['status'] != 'QUIET'), default=0),
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
