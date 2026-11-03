"""
hungary_signal_interpreter.py
Asifah Analytics -- Europe Backend Module
v1.1.0 -- Nov 3, 2026   (v1.0.0 May 17 2026)

HUNGARY SIGNAL INTERPRETER

v1.1.0 -- PLAIN LANGUAGE, EVIDENCE, AND THE TWO NEW STORIES
  * Good news is no longer filed as a red line. v1.0 printed "Hungary Returns
    Seized Ukrainian Assets -- BREACHED" and "EU Loan Unlock -- BREACHED". The
    reversal's milestones are now a dated REVERSAL LEDGER (background, sourced);
    the scan asks the live question: is the reversal HOLDING, TESTED or ERODING?
  * Red lines are RISKS only, scored per article on the whole corpus with
    publisher counting (europe_evidence): BREACHED needs 2+ outlets.
      orban_revival_signal, russia_counter_pressure, druzhba_pipeline_dispute,
      ukraine_track_rupture
  * Two stories v1.0 could not see:
      ACCOUNTABILITY -- the arrests of Orban-era officials (two ex-ministers in
        September, ex-central-bank governor Matolcsy on Oct 21). Read neutrally:
        the government calls it accountability; Fidesz calls it political
        retribution and points to the removal of the president by
        constitutional amendment. Both frames are tracked.
      ORBAN'S INTERNATIONAL TRACK -- the reported US-backed push (with Russian
        and Chinese support reported) for Orban as UN Secretary-General. Read as
        its own track, NOT as a domestic "comeback": the revival red line stays
        about Fidesz at home.
  * Spokes: russia (axis_reversal_watch), us (opposition_channel), china
    (investment_partner, capped L2).
  * top_indicator (one plain sentence), THIN READ, posture.

Contract kept for consumers (europe_regional_bluf, GPI, Russia tracker):
  so_what / red_lines{triggered, breached_count, approaching_count,
  highest_severity} / green_lines / diplomatic_track{score, active_count,
  signaled_count, maximum_pressure} / historical_matches. Red lines keep
  `pressure_type` ('diplomatic' | 'economic') for GPI axis routing.

Author: RCGG / Asifah Analytics
"""
from datetime import datetime, timezone

from europe_evidence import build_corpus, score_line, score_green, find, corpus_health

INTERPRETER_VERSION = '1.1.0'
THIN_MIN_ARTICLES = 30


# ============================================================
# REVERSAL LEDGER -- dated background, NOT scored. Update as events land.
# ============================================================
REVERSAL_LEDGER = {
    'as_of': '2026-10-28',
    'events': [
        {'date': '2026-04-12', 'what': 'Tisza wins 138 of 199 seats -- a two-thirds majority; Orban out after 16 years.'},
        {'date': '2026-05-06', 'what': 'Hungary returns the seized Oschadbank cash and gold to Ukraine.'},
        {'date': '2026-05-29', 'what': 'EU agrees to release EUR 16.4bn of frozen funds (EUR 10bn now, the rest with reforms).'},
        {'date': '2026-06',    'what': 'Budapest lifts its veto on opening Ukraine\'s first two EU accession clusters (11-point plan with Kyiv).'},
        {'date': '2026-09-29', 'what': 'Two Orban-era ministers (Seszták, Hankó) taken into custody after immunity is lifted.'},
        {'date': '2026-10-12', 'what': 'Ukraine passes the minority-rights law Budapest required; two more clusters expected Oct 13.'},
        {'date': '2026-10-21', 'what': 'Ex-central-bank governor Matolcsy taken into custody (central-bank foundation assets).'},
        {'date': '2026-10-22', 'what': 'Paks II (Rosatom) under review; termination decision expected end-2026 / early 2027.'},
        {'date': '2026-10-26', 'what': 'WSJ: Trump officials back Orban for UN Secretary-General; Russia and China reportedly supportive.'},
    ],
    'still_open': [
        'Russian energy: Tisza\'s target to end dependence is 2035; the EU gas phase-out deadline is November 2027.',
        'Paks II: review, not cancellation.',
        'The constitutional supermajority cuts both ways -- reform capacity and overreach risk.',
    ],
    'sources': [
        'https://www.euronews.com/my-europe/2026/05/29/hungary-unlocks-164bn-in-eu-funds-after-magyar-secures-deal-with-brussels',
        'https://www.euronews.com/2026/10/12/ukraine-passes-minority-rights-law-paving-way-for-breakthrough-in-eu-accession-talks',
        'https://euronews.com/2026/09/29/with-two-orban-era-ministers-detained-magyars-operation-purge-takes-shape',
        'https://euobserver.com/244500/big-fish-hooked-in-hungary-as-orbans-ex-bank-chief-placed-in-custody-day-163-of-the-tisza-government/',
        'https://brusselssignal.eu/2026/10/hungary-open-to-replacing-russias-rosatom-in-nuclear-plans/',
        'https://www.euronews.com/2026/10/26/trump-officials-back-orban-bid-for-un-secretary-general-wsj-reports',
    ],
}


# ============================================================
# RED LINES -- risks to the reversal (evidence-scored)
# ============================================================
RED_LINES = [
    {
        'id':       'orban_revival_signal',
        'label':    'Fidesz comeback at home',
        'detail':   'Fidesz regaining ground domestically: poll leads, mass rallies, a comeback narrative. '
                    'This is about Hungarian voters -- Orban\'s UN bid is tracked separately.',
        'severity': 3, 'color': '#f97316', 'icon': '⚠️',
        'category': 'diplomatic_signal', 'pressure_type': 'diplomatic',
        'precedent': 'Orban lost in 2002, spent eight years in opposition and returned in 2010 with two-thirds.',
        'breach':   ['fidesz leads poll', 'fidesz ahead in poll', 'fidesz overtakes tisza', 'orban comeback',
                     'fidesz mass rally', 'tens of thousands rally for orban'],
        'approach': ['fidesz rally', 'orban rally', 'fidesz gains', 'orban returns to', 'fidesz campaign',
                     'orban plans return'],
    },
    {
        'id':       'russia_counter_pressure',
        'label':    'Moscow pushes back on Budapest',
        'detail':   'Russian retaliation against the reversal: gas cut-offs, Rosatom legal action over Paks II, '
                    'Kremlin warnings to the Magyar government.',
        'severity': 3, 'color': '#dc2626', 'icon': '🇷🇺',
        'category': 'economic_signal', 'pressure_type': 'economic',
        'precedent': 'Moscow has used gas pricing and supply as leverage on Central European governments since 2006.',
        'breach':   ['gazprom cuts gas to hungary', 'russia halts gas to hungary', 'rosatom sues hungary',
                     'paks arbitration', 'russia retaliates against hungary', 'russia suspends gas to hungary'],
        'approach': ['rosatom warns', 'kremlin warns hungary', 'russia warns hungary', 'paks ii termination',
                     'paks contract dispute', 'no legal grounds', 'russia criticises magyar', 'russia criticizes magyar'],
    },
    {
        'id':       'druzhba_pipeline_dispute',
        'label':    'Druzhba oil supply disrupted',
        'detail':   'Russian crude to Hungary via Druzhba halted, damaged or cut. Under Orban the outage became the '
                    'lever for the EU-loan veto; now it tests whether Budapest still reaches for that lever.',
        'severity': 2, 'color': '#f59e0b', 'icon': '🛢️',
        'category': 'economic_signal', 'pressure_type': 'economic',
        'precedent': 'Feb 2026: a strike in western Ukraine took Druzhba offline for months; Orban blocked the EU loan.',
        'breach':   ['druzhba halted', 'druzhba suspended', 'druzhba pipeline damaged', 'druzhba shut',
                     'oil flows to hungary halted', 'oil supplies to hungary halted'],
        'approach': ['druzhba disruption', 'druzhba outage', 'druzhba flows reduced', 'druzhba repair',
                     'strike on druzhba'],
    },
    {
        'id':       'ukraine_track_rupture',
        'label':    'Budapest-Kyiv track breaks down',
        'detail':   'Hungary re-imposes or threatens a veto on Ukraine\'s EU path, or the Transcarpathian minority '
                    'dispute flares again.',
        'severity': 2, 'color': '#f97316', 'icon': '🇺🇦',
        'category': 'diplomatic_signal', 'pressure_type': 'diplomatic',
        'precedent': '2023-2026: Budapest blocked Ukraine\'s accession steps over minority rights.',
        'breach':   ['hungary blocks ukraine', 'hungary reimposes veto', 'hungary vetoes ukraine',
                     'hungary blocks cluster', 'hungary blocks accession'],
        'approach': ['hungary threatens veto', 'minority rights dispute', 'hungary ukraine tensions',
                     'hungary summons ukrainian ambassador', 'transcarpathia tensions'],
    },
]


# ============================================================
# GREEN LINES -- the reversal moving forward (one outlet may activate)
# ============================================================
GREEN_LINES = [
    {'id': 'tisza_eu_normalization', 'label': 'EU money and rule-of-law track moving', 'icon': '🇪🇺', 'weight': 1.2,
     'detail': 'Frozen EU funds flowing, Article 7 winding down, reforms Brussels asked for.',
     'active': ['eu releases funds to hungary', 'commission releases funds', 'hungary receives eu funds',
                'article 7 closed', 'article 7 procedure ended', 'hungary joins eppo'],
     'signaled': ['hungary eu funds', 'article 7', 'rule of law reform', 'magyar brussels', 'recovery funds hungary']},
    {'id': 'hungary_ukraine_warming', 'label': 'Budapest-Kyiv warming', 'icon': '🤝', 'weight': 1.1,
     'detail': 'Accession clusters opened with Hungary\'s consent; Magyar-Zelensky contact.',
     'active': ['magyar zelensky meeting', 'magyar met zelensky', 'zelensky and magyar', 'hungary lifts veto',
                'clusters opened', 'accession cluster opened'],
     'signaled': ['hungary ukraine', 'minority rights law', 'transcarpathia', 'zelensky magyar']},
    {'id': 'paks_ii_review', 'label': 'Paks II moving away from Rosatom', 'icon': '🔌', 'weight': 1.0,
     'detail': 'The Rosatom-built nuclear expansion under review; replacement contractors considered.',
     'active': ['paks ii terminated', 'rosatom contract cancelled', 'replace rosatom', 'hungary drops rosatom'],
     'signaled': ['paks ii review', 'paks ii', 'rosatom hungary']},
    {'id': 'russian_energy_exit', 'label': 'Russian energy exit underway', 'icon': '⚡', 'weight': 1.0,
     'detail': 'Non-Russian crude via Adria, LNG via Krk, gas contracts unwound.',
     'active': ['hungary ends russian gas', 'mol non-russian crude', 'adria pipeline hungary', 'krk lng hungary'],
     'signaled': ['russian gas phase-out', 'energy diversification hungary', 'adria pipeline']},
    {'id': 'sanctions_compliance_increase', 'label': 'Budapest stops blocking Russia sanctions', 'icon': '🛂',
     'weight': 1.0, 'detail': 'Sanctions packages pass without a Hungarian hold-out.',
     'active': ['hungary backs sanctions', 'hungary supports sanctions package', 'sanctions package adopted'],
     'signaled': ['russia sanctions hungary', 'hungary sanctions vote']},
]


# ============================================================
# TRACKS (scored, not red lines)
# ============================================================
ACCOUNTABILITY_PROCEEDING = ['arrested', 'taken into custody', 'detained', 'charged', 'indicted', 'immunity lifted',
                             'asset recovery office', 'matolcsy', 'seszták', 'sesztak', 'hankó', 'hanko',
                             'operation purge']
ACCOUNTABILITY_CONTESTED = ['political persecution', 'politically motivated', 'witch hunt', 'show trial',
                            'arbitrariness', 'revenge', 'retribution', 'judicial independence',
                            'venice commission', 'sulyok']
ACCOUNTABILITY_SCOPE = ['orban', 'fidesz', 'former minister', 'ex-minister', 'central bank', 'matolcsy',
                        'mnb', 'hungar']

UN_FLOATED = ['secretary-general', 'secretary general', 'un chief', 'united nations chief', 'lead the un',
              'head the un', 'guterres successor']
UN_NOMINATED = ['nominates orban', 'nominated orban', 'formally nominated', 'nomination of orban',
                'security council vote on orban', 'straw poll']
UN_OPPOSED = ['will not support orban', 'oppose orban', 'opposes orban', 'veto orban', 'against orban\'s candidacy']

UN_BASELINE = {
    'as_of': '2026-10-26',
    'what': ('WSJ reported Trump administration officials favour Orban for UN Secretary-General, possibly as a joint '
             'US-Russia-China candidate; no decision announced.'),
    'rules': ('Needs 9 of 15 Security Council votes and no veto from the five permanent members; a member state '
              'must nominate. Russia\'s deputy foreign minister said permanent members do not nominate candidates. '
              'Guterres\'s term ends Dec 31.'),
    'reactions': ('Poland\'s foreign minister does not foresee supporting him; Ukraine\'s foreign minister pointed to '
                  'his record of blocking EU decisions. Orban\'s spokesperson earlier called a related report fake news.'),
    'sources': ['https://www.euronews.com/2026/10/26/trump-officials-back-orban-bid-for-un-secretary-general-wsj-reports'],
}


# ============================================================
# HISTORICAL PRECEDENTS
# ============================================================
HISTORICAL_PRECEDENTS = [
    {
        'id': 'hungary_1989_transition', 'label': '1989 Hungarian Democratic Transition',
        'period': 'May-October 1989', 'icon': '🕊️',
        'context': ('Hungary cut the border fence with Austria, let East Germans through and declared a republic -- '
                    'the first Warsaw Pact country to leave the Soviet orbit by its own political process.'),
        'analog_for': ['tisza_eu_normalization', 'hungary_ukraine_warming'],
    },
    {
        'id': 'hungary_1956_revolution', 'label': '1956 Hungarian Revolution',
        'period': 'October-November 1956', 'icon': '⚔️',
        'context': ('The uprising was crushed by Soviet troops. Caution for any rapid turn away from Moscow -- '
                    'though today\'s Hungary sits inside NATO and the EU, the backstop 1956 lacked.'),
        'analog_for': ['russia_counter_pressure', 'druzhba_pipeline_dispute'],
    },
    {
        'id': 'orban_2002_opposition_decade', 'label': 'Orban 2002-2010 Opposition Years',
        'period': 'May 2002 - April 2010', 'icon': '♻️',
        'context': ('Orban lost in 2002, rebuilt Fidesz in opposition and returned in 2010 with a two-thirds '
                    'majority. Fidesz is durable out of power.'),
        'analog_for': ['orban_revival_signal'],
    },
]


# ============================================================
# HELPERS
# ============================================================
def _corpus(scan_data):
    arts = scan_data.get('_corpus') or []
    if not arts:   # cached / test payloads: actors' top articles
        for a in (scan_data.get('actors') or {}).values():
            arts = arts + list(a.get('top_articles') or [])
    return build_corpus({'articles_en': arts, 'telegram_messages': []})


def _lvl(actors, key):
    return int(((actors or {}).get(key) or {}).get('escalation_level', 0) or 0)


def _scoped(corpus, terms):
    """Items carrying a term AND an accountability-scope word (Hungary / Orban
    era) -- 'arrested' alone is every crime story in Europe."""
    sub = [c for c in corpus if any(w in c['text'] for w in ACCOUNTABILITY_SCOPE)]
    return find(sub, terms)


# ============================================================
# SCORING
# ============================================================
def _score_red_lines(scan_data, corpus):
    ct = scan_data.get('cross_theater') or {}
    out = []
    for rl in RED_LINES:
        sc = score_line(corpus, rl['breach'], rl['approach'])
        status, via = sc['status'], 'evidence'
        # The tracker's revival trigger set (2+ distinct triggers) can lift the
        # revival line to APPROACHING, never to BREACHED on its own.
        if rl['id'] == 'orban_revival_signal' and ct.get('orban_revival_signal') and status in ('INACTIVE', 'WATCHING'):
            status, via = 'APPROACHING', 'trigger_set'
        if rl['id'] == 'druzhba_pipeline_dispute' and ct.get('druzhba_pipeline_status') == 'disrupted' \
                and status in ('INACTIVE', 'WATCHING'):
            status, via = 'APPROACHING', 'status_flag'
        if status == 'INACTIVE':
            continue
        n = sc['breach_outlets'] if status == 'BREACHED' else max(sc['breach_outlets'], sc['approach_outlets'])
        ev = sc['evidence'][0] if sc['evidence'] else None
        trig = (f"{status.title()} on {n} outlet{'s' if n != 1 else ''}"
                + (f' -- e.g. "{ev["title"][:90]}" ({ev["outlet"]})' if ev else '')) if via == 'evidence' \
            else 'Lifted by the tracker\'s own trigger set -- not yet corroborated by outlets'
        base = {k: v for k, v in rl.items() if k not in ('breach', 'approach')}
        out.append({**base, **sc, 'status': status, 'via': via, 'trigger': trig, 'source': rl['precedent']})
    rank = {'BREACHED': 3, 'APPROACHING': 2, 'WATCHING': 1}
    out.sort(key=lambda r: (-rank.get(r['status'], 0), -r['severity']))
    return out


def _score_green_lines(corpus):
    out = []
    for g in GREEN_LINES:
        sc = score_green(corpus, g['active'], g['signaled'])
        if sc['status'] == 'DORMANT':
            continue
        base = {k: v for k, v in g.items() if k not in ('active', 'signaled')}
        n = sc['active_outlets'] or sc['signaled_outlets']
        out.append({**base, **sc, 'trigger': f"{sc['status'].title()} on {n} outlet{'s' if n != 1 else ''}"})
    out.sort(key=lambda g: (g['status'] != 'ACTIVE', -g['weight']))
    return out


def _accountability_track(corpus):
    pro = _scoped(corpus, ACCOUNTABILITY_PROCEEDING)
    con = _scoped(corpus, ACCOUNTABILITY_CONTESTED)
    npro, ncon = len(pro['outlets']), len(con['outlets'])
    if npro >= 2 and ncon >= 2:
        status = 'contested'
        read = (f'Arrests and charges against Orban-era officials are in the news ({npro} outlets), and so is the '
                f'pushback ({ncon} outlets): the government calls it accountability, Fidesz calls it political '
                'retribution. Watch the courts, not the adjectives.')
    elif npro >= 2:
        status = 'proceeding'
        read = (f'The accountability drive is moving ({npro} outlets): Orban-era officials face custody or charges. '
                'Fidesz\'s line -- political retribution -- is not corroborated this cycle.')
    elif ncon >= 2:
        status = 'framing'
        read = (f'The "political persecution" frame is out front ({ncon} outlets) without a new arrest in view.')
    elif npro or ncon:
        status = 'signalled'
        read = 'One outlet carries the accountability story this cycle -- signalled, not corroborated.'
    else:
        status = 'quiet'
        read = 'No accountability-drive reporting in this cycle\'s corpus; the ledger below is the background.'
    return {'status': status, 'proceeding_outlets': npro, 'contested_outlets': ncon, 'read': read,
            'evidence': (pro['evidence'][:2] + con['evidence'][:2])[:4]}


def _international_track(corpus):
    orban = [c for c in corpus if 'orban' in c['text'] or 'orbán' in c['text']]
    fl = find(orban, UN_FLOATED)
    nom = find(orban, UN_NOMINATED)
    opp = find(orban, UN_OPPOSED)
    nf, nn, no = len(fl['outlets']), len(nom['outlets']), len(opp['outlets'])
    if nn >= 2:
        status = 'nominated'
        read = (f'Orban\'s UN Secretary-General candidacy is formally in play ({nn} outlets). '
                'The nominating state and the Security Council arithmetic are the story now.')
    elif nf >= 2:
        status = 'floated'
        read = (f'The Orban-for-UN-chief story is live ({nf} outlets). Three hubs, one node: Washington, with '
                'Moscow and Beijing reportedly on side, converging on an ousted Hungarian leader while his former '
                'ministers face arrest at home. Read it as an exit path as much as a comeback -- and note the '
                'open question of which state would nominate him.')
    elif nf == 1:
        status = 'signalled'
        read = 'One outlet carries the Orban UN story this cycle.'
    else:
        status = 'quiet'
        read = 'The Orban UN bid is not in this cycle\'s corpus; the dated baseline below is the context.'
    if no >= 2 and status in ('floated', 'nominated'):
        read += f' Opposition to the bid is corroborated ({no} outlets).'
    return {'status': status, 'floated_outlets': nf, 'nominated_outlets': nn, 'opposed_outlets': no,
            'read': read, 'baseline': UN_BASELINE,
            'evidence': (nom['evidence'][:2] + fl['evidence'][:2] + opp['evidence'][:1])[:4]}


def _posture(red_lines):
    st = {r['id']: r['status'] for r in red_lines}
    if st.get('orban_revival_signal') == 'BREACHED' or st.get('ukraine_track_rupture') == 'BREACHED':
        return 'eroding'
    if any(r['status'] in ('BREACHED', 'APPROACHING') for r in red_lines):
        return 'tested'
    return 'holding'


POSTURE_WORDS = {
    'holding': ('REVERSAL HOLDING', '🪜', '#22c55e'),
    'tested':  ('REVERSAL BEING TESTED', '⚖️', '#f59e0b'),
    'eroding': ('REVERSAL ERODING', '⚠️', '#f97316'),
}


def _score_diplomatic_track(green_lines, red_lines, posture):
    active = [g for g in green_lines if g['status'] == 'ACTIVE']
    signaled = [g for g in green_lines if g['status'] != 'ACTIVE']
    score = sum(int(g['weight'] * 15) for g in active) + sum(int(g['weight'] * 6) for g in signaled)
    score += {'holding': 20, 'tested': 5, 'eroding': -15}[posture]
    score = max(0, min(100, score))
    if score >= 75:
        scenario, color, icon = 'STRONG NORMALIZATION -- reversal durable, EU integration accelerating', '#22c55e', '🟢'
    elif score >= 50:
        scenario, color, icon = 'ACTIVE NORMALIZATION -- reversal in progress with momentum', '#3b82f6', '🔵'
    elif score >= 30:
        scenario, color, icon = 'TENTATIVE NORMALIZATION -- reversal visible, momentum thin this cycle', '#f59e0b', '🟡'
    elif posture == 'holding':
        scenario, color, icon = 'QUIET -- reversal in place, little new movement this cycle', '#38bdf8', '🔵'
    elif score >= 15:
        scenario, color, icon = 'CONTESTED -- reversal signals offset by pressure', '#f97316', '🟠'
    else:
        scenario, color, icon = 'STALLED -- pressure without reversal momentum this cycle', '#6b7280', '⚪'
    return {'score': score, 'scenario': scenario, 'scenario_color': color, 'scenario_icon': icon,
            'maximum_pressure': posture == 'eroding' and score < 30,
            'active_count': len(active), 'signaled_count': len(signaled)}


def _match_historical(red_lines, green_lines):
    ids = {r['id'] for r in red_lines} | {g['id'] for g in green_lines if g['status'] == 'ACTIVE'}
    out = []
    for p in HISTORICAL_PRECEDENTS:
        rel = sum(1 for a in p['analog_for'] if a in ids)
        if rel:
            out.append({**p, 'relevance_score': rel})
    out.sort(key=lambda m: -m['relevance_score'])
    return out[:3]


def _top_indicator(posture, red_lines, accountability, intl, green_lines, health):
    br = [r for r in red_lines if r['status'] == 'BREACHED']
    if posture == 'eroding':
        line = f"The reversal is eroding: {br[0]['label'].lower()} is corroborated this cycle." if br else \
            'The reversal is eroding this cycle.'
    elif br:
        line = f"The reversal is being tested: {br[0]['label'].lower()} is corroborated by {br[0]['breach_outlets']} outlets."
    elif intl['status'] in ('floated', 'nominated'):
        line = ('Orban\'s next act is being written abroad: the UN Secretary-General push is in the news while his '
                'former officials face arrest at home -- and Budapest\'s turn toward Brussels is holding.')
    elif accountability['status'] in ('proceeding', 'contested'):
        line = ('Budapest\'s accountability drive is the story: Orban-era officials in custody, Fidesz calling it '
                'retribution -- the turn away from Moscow is holding.')
    elif any(r['status'] == 'APPROACHING' for r in red_lines):
        r = next(r for r in red_lines if r['status'] == 'APPROACHING')
        line = f"Holding, with a watch item: {r['label'].lower()} -- reported, not corroborated."
    elif any(g['status'] == 'ACTIVE' for g in green_lines):
        g = next(g for g in green_lines if g['status'] == 'ACTIVE')
        line = f"Hungary's turn from Moscow toward Brussels is holding -- this cycle's movement: {g['label'].lower()}."
    else:
        line = 'Hungary\'s turn from Moscow toward Brussels is holding; nothing this cycle tests it.'
    return ('Thin read -- ' + line) if health['thin'] else line


def _build_so_what(posture, red_lines, green_lines, accountability, intl, health):
    label, icon, color = POSTURE_WORDS[posture]
    situation = {
        'holding': ('Six months into the Magyar government, the reversal from Orban-era alignment with Moscow is in '
                    'place: EU money released, Ukraine\'s accession steps unblocked, Paks II under review. Nothing '
                    'in this cycle\'s reporting is pulling it back.'),
        'tested':  ('The reversal is in place but something in this cycle\'s reporting is pushing on it -- see the '
                    'red lines below for which lever and how many outlets carry it.'),
        'eroding': ('Corroborated reporting this cycle points against the reversal: a Fidesz comeback at home or a '
                    'break in the Budapest-Kyiv track.'),
    }[posture]
    threads = [accountability['read'], intl['read']]
    assessment = (
        'The unasked question is no longer "will Hungary turn?" -- it turned in April -- but "what is the price '
        'of staying turned?" Three things set that price: Moscow\'s energy levers (Druzhba, gas, Paks II), Fidesz\'s '
        'ability to frame the accountability drive as retribution, and where Orban lands -- in Hungarian politics, '
        'or in New York. ' + ' '.join(threads)
    )
    watch = [
        'Paks II decision (expected end-2026 / early 2027) and any Rosatom legal response',
        'Court rulings in the Seszták, Hankó and Matolcsy cases -- due process is the credibility test',
        'Whether any state formally nominates Orban for UN Secretary-General before Guterres\'s term ends Dec 31',
        'Druzhba flows and the Adria / Krk alternatives',
        'Magyar-Zelensky meeting and the next accession clusters',
    ]
    if health['thin']:
        label = 'THIN READ -- ' + label
        situation = ('THIN READ -- under-read scan (' + health['reason'] + '); quiet lines may be unread. ') + situation
    return {'scenario': label, 'scenario_icon': icon, 'scenario_color': color, 'situation': situation,
            'assessment': assessment, 'watch_list': watch,
            'breached_count': sum(1 for r in red_lines if r['status'] == 'BREACHED'),
            'approaching_count': sum(1 for r in red_lines if r['status'] == 'APPROACHING'),
            'green_lines_active': sum(1 for g in green_lines if g['status'] == 'ACTIVE')}


def _spokes(actors, red_lines, intl):
    st = {r['id']: r['status'] for r in red_lines}
    ru = _lvl(actors, 'hungary_russia_axis')
    if st.get('russia_counter_pressure') == 'BREACHED':
        ru = max(ru, 3)
    elif st.get('russia_counter_pressure') == 'APPROACHING':
        ru = max(ru, 2)
    us = _lvl(actors, 'orban_international')
    if intl['status'] == 'nominated':
        us = max(us, 3)
    elif intl['status'] == 'floated':
        us = max(us, 2)
    return {
        'russia': {'level': min(4, ru), 'node_class': 'axis_reversal_watch',
                   'note': 'Hungary turned away from Moscow in April; this wheel watches Moscow\'s levers on Budapest.'},
        'us':     {'level': min(3, us), 'node_class': 'opposition_channel',
                   'note': 'The visible US signal on Hungary runs through Orban: 2026 election backing, the UN push.'},
        'china':  {'level': min(2, _lvl(actors, 'china_investment')), 'node_class': 'investment_partner',
                   'note': 'Chinese battery/EV investment (CATL Debrecen, BYD Szeged) -- read low, capped at L2.'},
    }


# ============================================================
# MAIN ENTRY POINT
# ============================================================
def interpret_signals(scan_data):
    """Called from rhetoric_tracker_hungary.py with scan_data (+ `_corpus`)."""
    try:
        corpus = _corpus(scan_data)
        health = corpus_health(scan_data, corpus, THIN_MIN_ARTICLES)
        actors = scan_data.get('actors') or {}
        red_lines = _score_red_lines(scan_data, corpus)
        green_lines = _score_green_lines(corpus)
        posture = _posture(red_lines)
        diplomatic = _score_diplomatic_track(green_lines, red_lines, posture)
        accountability = _accountability_track(corpus)
        intl = _international_track(corpus)
        historical = _match_historical(red_lines, green_lines)
        so_what = _build_so_what(posture, red_lines, green_lines, accountability, intl, health)
        top_indicator = _top_indicator(posture, red_lines, accountability, intl, green_lines, health)
        breached = [r for r in red_lines if r['status'] == 'BREACHED']
        approaching = [r for r in red_lines if r['status'] == 'APPROACHING']
        active_gl = [g for g in green_lines if g['status'] == 'ACTIVE']
        return {
            'so_what':          so_what,
            'top_indicator':    top_indicator,
            'posture':          posture,
            'posture_label':    POSTURE_WORDS[posture][0],
            'thin_read':        health['thin'],
            'corpus_health':    health,
            'red_lines': {
                'triggered':         red_lines,
                'breached_count':    len(breached),
                'approaching_count': len(approaching),
                'highest_severity':  max((r['severity'] for r in breached), default=0),
            },
            'green_lines': {
                'triggered':         green_lines,
                'active_count':      len(active_gl),
                'signaled_count':    len(green_lines) - len(active_gl),
                'diplomatic_score':  diplomatic['score'],
            },
            'diplomatic_track':    diplomatic,
            'accountability_track': accountability,
            'international_track': intl,
            'reversal_ledger':     REVERSAL_LEDGER,
            'historical_matches':  historical,
            'spokes':              _spokes(actors, red_lines, intl),
            'interpreter_version': INTERPRETER_VERSION,
            'interpreted_at':      datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'[Hungary Interpreter] Error: {str(e)[:120]}')
        return {
            'so_what': {'scenario': 'Interpreter error -- unread, not calm', 'assessment': str(e)[:200],
                        'situation': '', 'watch_list': [], 'scenario_color': '#6b7280', 'scenario_icon': '⚪'},
            'top_indicator': 'Interpreter error this cycle -- unread, not calm.',
            'thin_read': True, 'posture': 'unread', 'spokes': {},
            'red_lines': {'triggered': [], 'breached_count': 0, 'approaching_count': 0, 'highest_severity': 0},
            'green_lines': {'triggered': [], 'active_count': 0, 'signaled_count': 0, 'diplomatic_score': 0},
            'diplomatic_track': {'score': 0, 'scenario': 'Unknown', 'maximum_pressure': False,
                                 'scenario_color': '#6b7280', 'scenario_icon': '⚪',
                                 'active_count': 0, 'signaled_count': 0},
            'historical_matches': [], 'reversal_ledger': REVERSAL_LEDGER,
            'interpreter_version': INTERPRETER_VERSION, 'error': str(e)[:200],
        }


def build_top_signals(scan_data):
    """Canonical top_signals[] for the Europe BLUF / GPI (Hungary had none)."""
    interp = scan_data.get('interpretation') or {}
    FLAG = '\U0001f1ed\U0001f1fa'
    sigs = []
    for r in (interp.get('red_lines') or {}).get('triggered', [])[:3]:
        if r.get('status') not in ('BREACHED', 'APPROACHING'):
            continue
        b = r['status'] == 'BREACHED'
        sigs.append({'priority': 11 if b else 8, 'category': 'red_line', 'theatre': 'hungary',
                     'level': 3 if b else 2, 'icon': r.get('icon', '⚠️'), 'color': r.get('color', '#f97316'),
                     'pressure_type': r.get('pressure_type', 'diplomatic'),
                     'short_text': f"{FLAG} HUNGARY: {'Corroborated' if b else 'Watching'} -- {r.get('label', '')}",
                     'long_text': f"HUNGARY: {r.get('label', '')}. {r.get('trigger', '')}"})
    intl = interp.get('international_track') or {}
    if intl.get('status') in ('floated', 'nominated'):
        sigs.append({'priority': 9, 'category': 'orban_international', 'theatre': 'hungary', 'level': 2,
                     'icon': '🌐', 'color': '#3b82f6', 'pressure_type': 'diplomatic',
                     'short_text': f'{FLAG} HUNGARY: Orban UN Secretary-General push in the news',
                     'long_text': 'HUNGARY: ' + intl.get('read', '')})
    acc = interp.get('accountability_track') or {}
    if acc.get('status') in ('proceeding', 'contested'):
        sigs.append({'priority': 7, 'category': 'accountability', 'theatre': 'hungary', 'level': 2,
                     'icon': '⚖️', 'color': '#8b5cf6', 'pressure_type': 'diplomatic',
                     'short_text': f'{FLAG} HUNGARY: Accountability drive {acc["status"]}',
                     'long_text': 'HUNGARY: ' + acc.get('read', '')})
    for g in (interp.get('green_lines') or {}).get('triggered', [])[:2]:
        if g.get('status') == 'ACTIVE':
            sigs.append({'priority': 6, 'category': 'green_line', 'theatre': 'hungary', 'level': 1,
                         'icon': g.get('icon', '🕊️'), 'color': '#10b981', 'pressure_type': 'diplomatic',
                         'short_text': f"{FLAG} HUNGARY: {g.get('label', '')}",
                         'long_text': f"HUNGARY: {g.get('detail', '')} {g.get('trigger', '')}"})
    sigs.sort(key=lambda s: -s['priority'])
    return sigs[:6]


__version__ = INTERPRETER_VERSION
__module_id__ = 'hungary_signal_interpreter'
print(f'[Hungary Interpreter] Module loaded -- v{__version__}')
