"""
rhetoric_tracker_uk.py -- United Kingdom Rhetoric & Pressure Tracker v1.0.0
Asifah Analytics -- Europe backend -- built Nov 4 2026 (night)

Runs on the shared engine (europe_rhetoric_engine.py, a port of the WHA
engine). This file is the CONFIG plus the UK mini wheel.

THE SO WHAT (why the UK matters)
  Local:    a seventh prime minister in ten years (Burnham, Jul 2026), a gilt
            market that ended a government in 2022, and a union under strain on
            three fronts at once -- a pro-independence majority at Holyrood, a
            Plaid Cymru First Minister in Cardiff, and the Irish Sea border.
  Regional: Britain is Europe's second military power and a nuclear state, the
            co-leader of post-ceasefire planning for Ukraine, and the country
            Russia probes most -- cables, spy ships, sabotage, poisonings.
  Global:   the City of London prices and insures much of the world's risk; the
            overseas edge (Falklands, Gibraltar, Chagos/Diego Garcia, the Cyprus
            bases) makes British domestic choices into other people's security
            questions; AUKUS ties London to the Indo-Pacific.
  The unasked question: how much room does Britain have to act on its own?
  Every vector here moves that answer -- money (gilts), the union (Faslane is in
  Scotland), the US guarantee (Falklands, Chagos), and whether a war it is not
  fighting reaches its bases anyway (Akrotiri, March 2026).

ACTORS (12) -> VECTORS (8)
  government      government
  opposition      opposition          (both flanks, symmetric -- Reform, the
                                       Conservatives, the Greens and the left)
  union           scotland, wales, northern_ireland
  overseas        falklands_gibraltar, chagos, cyprus_bases
  us_relationship us_uk
  russia_hybrid   russia_hybrid
  europe_security ukraine_europe
  indo_pacific    aukus

Dated facts (re-verify ~Dec 19 2026): Burnham PM since 20 Jul 2026, Healey
Chancellor, Miliband Foreign Secretary; Autumn Budget 28 Oct 2026. Holyrood May
2026: SNP 58 + Greens 15 of 129 (pro-independence majority). Senedd May 2026:
Plaid Cymru largest party (~43 of 96), Reform UK second (34), Labour 9; Rhun ap
Iorwerth First Minister. Gibraltar treaty signed Jul 2026. Chagos treaty (May
2025) stalled after US opposition. Iranian-made drone hit RAF Akrotiri 2 Mar 2026.

COPYRIGHT (c) 2025-2026 Asifah Analytics. All rights reserved.
"""

from datetime import datetime, timezone

from europe_rhetoric_engine import CountryRhetoricTracker

VERSION = '1.0.0'

ACTORS = {
    'government': {
        'name': 'Government & the Treasury', 'flag': '🇬🇧', 'icon': '🏛️', 'vector': 'government',
        'role': 'Prime Minister Andy Burnham (since Jul 2026), Chancellor John Healey, the cabinet, the Budget',
        'baseline': 18,
        'keywords': ['burnham', 'andy burnham', 'downing street', 'number 10', 'no 10', 'healey', 'chancellor',
                     'treasury', 'cabinet', 'prime minister', 'labour government', 'uk government', 'british government',
                     'budget', 'autumn budget', 'spending review', 'fiscal rules', 'gilts', 'gilt yields',
                     'bank of england', 'obr', 'office for budget responsibility', 'miliband', 'whitehall'],
        'tripwires': [
            ('cabinet_resignation', 3, ['cabinet minister resigns', 'resigns from the cabinet', 'quits the cabinet',
                                        'cabinet resignation', 'chancellor resigns', 'foreign secretary resigns']),
            ('leadership_challenge', 3, ['leadership challenge', 'no confidence in burnham', 'move against burnham',
                                         'labour leadership contest', 'confidence vote']),
            ('gilt_selloff', 3, ['gilt sell-off', 'gilt selloff', 'gilt rout', 'gilts tumble', 'gilt market turmoil',
                                 'gilt yields soar', 'gilt yields surge', 'emergency bond buying',
                                 'bank of england intervenes', 'bank of england steps in']),
            ('emergency_budget', 3, ['emergency budget', 'emergency fiscal statement', 'u-turn on the budget',
                                     'budget u-turn']),
        ],
    },
    'opposition': {
        'name': 'Opposition — both flanks', 'flag': '🗳️', 'icon': '⚖️', 'vector': 'opposition',
        'role': 'Reform UK (Farage) and the Conservatives (Badenoch) on the right; the Greens, independents and '
                'the Labour left on the left. Read symmetrically: the same rules for both flanks.',
        'baseline': 14,
        'keywords': ['reform uk', 'farage', 'nigel farage', 'conservatives', 'tories', 'badenoch', 'kemi badenoch',
                     'green party', 'greens', 'polanski', 'restore britain', 'opinion poll', 'polling', 'by-election',
                     'local elections', 'labour left', 'independent alliance', 'opposition'],
        'tripwires': [
            ('violent_disorder', 3, ['violent disorder', 'riots erupt', 'rioting in', 'riot police',
                                     'disorder spreads', 'mosque attacked', 'asylum hotel attacked']),
            ('mass_protest', 2, ['tens of thousands march', 'hundreds of thousands march', 'mass protest in london',
                                 'national demonstration']),
            ('defection', 2, ['defects to reform', 'defected to reform', 'defects to the greens', 'crosses the floor']),
            ('by_election_upset', 2, ['wins by-election', 'by-election shock', 'overturns majority']),
        ],
    },
    'scotland': {
        'name': 'Scotland', 'flag': '🏴', 'icon': '🦄', 'vector': 'union',
        'role': 'First Minister John Swinney, the SNP-led Scottish Government, Holyrood\'s pro-independence '
                'majority (May 2026), the Greens, Scottish Labour and Reform',
        'baseline': 10,
        'keywords': ['scotland', 'scottish', 'holyrood', 'snp', 'swinney', 'john swinney', 'scottish government',
                     'indyref2', 'indyref', 'scottish independence', 'independence referendum', 'section 30',
                     'scottish greens', 'scottish labour', 'faslane', 'edinburgh'],
        'tripwires': [
            ('section_30_request', 3, ['section 30 order', 'section 30 request', 'requests a section 30',
                                       'formally requests a referendum', 'demands a second referendum']),
            ('referendum_bill', 3, ['referendum bill', 'independence referendum bill', 'sets a date for a referendum',
                                    'referendum date', 'de facto referendum']),
            ('indy_court_case', 2, ['supreme court independence', 'court ruling on independence']),
        ],
    },
    'wales': {
        'name': 'Wales', 'flag': '🏴', 'icon': '🐉', 'vector': 'union',
        'role': 'First Minister Rhun ap Iorwerth (Plaid Cymru, since May 2026), the Senedd -- Plaid the largest '
                'party, Reform UK second, Labour cut to 9 seats after a century in charge',
        'baseline': 6,
        'keywords': ['wales', 'welsh', 'senedd', 'cardiff bay', 'plaid cymru', 'plaid', 'ap iorwerth',
                     'rhun ap iorwerth', 'welsh government', 'welsh independence', 'yes cymru', 'cymru',
                     'welsh labour', 'reform wales'],
        'requires_any': ['wales', 'welsh', 'senedd', 'plaid', 'cymru', 'ap iorwerth', 'cardiff'],
        'tripwires': [
            ('welsh_indy_move', 3, ['welsh independence referendum', 'referendum on welsh independence',
                                    'plaid calls for independence referendum']),
            ('senedd_crisis', 2, ['senedd confidence vote', 'welsh budget defeated', 'welsh government collapses',
                                  'ap iorwerth no confidence']),
            ('cardiff_london_clash', 2, ['legal challenge to westminster', 'sewel convention breached',
                                         'overrides the senedd', 'internal market act challenge']),
        ],
    },
    'northern_ireland': {
        'name': 'Northern Ireland', 'flag': '🇬🇧', 'icon': '🌉', 'vector': 'union',
        'role': 'Stormont power-sharing, the Windsor Framework and the Irish Sea border, unionist and nationalist '
                'parties (DUP, Sinn Féin), border-poll politics, dissident paramilitaries',
        'baseline': 8,
        'keywords': ['northern ireland', 'stormont', 'windsor framework', 'irish sea border', 'dup', 'sinn fein',
                     'michelle o\'neill', 'belfast', 'border poll', 'united ireland', 'unionist', 'loyalist',
                     'dissident republican', 'new ira', 'psni'],
        'tripwires': [
            ('stormont_collapse', 3, ['stormont collapses', 'collapse of stormont', 'power-sharing collapses',
                                      'walks out of stormont', 'first minister resigns']),
            ('border_poll_call', 3, ['secretary of state calls a border poll', 'border poll called',
                                     'border poll announced']),
            ('paramilitary_attack', 3, ['new ira attack', 'dissident republican bomb', 'police officer shot in',
                                        'loyalist attack', 'pipe bomb', 'car bomb in']),
        ],
    },
    'falklands_gibraltar': {
        'name': 'Falklands, Gibraltar & the South Atlantic', 'flag': '🇫🇰', 'icon': '⚓', 'vector': 'overseas',
        'role': 'The Falklands garrison and Argentina\'s claim, Sea Lion oil, South Georgia and the British '
                'Antarctic Territory; Gibraltar and the 2026 UK-EU treaty',
        'baseline': 6,
        'keywords': ['falklands', 'falkland islands', 'malvinas', 'mount pleasant', 'south georgia', 'sea lion',
                     'british antarctic territory', 'south atlantic', 'gibraltar', 'la linea', 'gibraltar treaty',
                     'fabian picardo'],
        'tripwires': [
            ('south_atlantic_incident', 4, ['military incident falklands', 'incident near the falklands',
                                            'argentine warship', 'british warship falklands', 'royal navy deploys to the falklands',
                                            'typhoons scrambled falklands']),
            ('argentine_measure', 3, ['sanctions on oil companies', 'sanctions on companies operating in the falklands',
                                      'suspends flights to the falklands', 'bans falklands-flagged']),
            ('us_falklands_shift', 3, ['trump falklands', 'us position on the falklands', 'washington falklands',
                                       'us neutral on falklands']),
            ('gibraltar_row', 2, ['gibraltar border closed', 'spain blocks gibraltar', 'gibraltar treaty suspended',
                                  'gibraltar airspace']),
        ],
    },
    'chagos': {
        'name': 'Chagos & Diego Garcia', 'flag': '🏝️', 'icon': '🛫', 'vector': 'overseas',
        'role': 'The 2025 UK-Mauritius treaty, its stalled ratification, US objections, and the US-UK base on '
                'Diego Garcia',
        'baseline': 4,
        'keywords': ['chagos', 'chagos islands', 'diego garcia', 'mauritius', 'british indian ocean territory',
                     'chagossian', 'ramgoolam'],
        'tripwires': [
            ('chagos_ratified', 2, ['chagos treaty ratified', 'ratifies the chagos', 'chagos bill passes',
                                    'chagos deal passes']),
            ('us_blocks_chagos', 3, ['us opposes chagos', 'trump chagos', 'washington blocks chagos',
                                     'chagos deal paused', 'pauses chagos']),
            ('diego_garcia_access', 3, ['diego garcia access', 'bombers from diego garcia', 'strikes from diego garcia',
                                        'denied use of diego garcia', 'diego garcia lease']),
        ],
    },
    'cyprus_bases': {
        'name': 'The Cyprus bases (Akrotiri & Dhekelia)', 'flag': '🇨🇾', 'icon': '✈️', 'vector': 'overseas',
        'role': 'RAF Akrotiri and Dhekelia, the Sovereign Base Areas -- strike and surveillance flights over the '
                'Middle East; hit by an Iranian-made drone launched from Lebanon on 2 Mar 2026',
        'baseline': 5,
        'keywords': ['akrotiri', 'raf akrotiri', 'dhekelia', 'sovereign base areas', 'sovereign bases',
                     'british bases in cyprus', 'uk bases in cyprus', 'episkopi'],
        'tripwires': [
            # THE red line Rachel named: Iran (or a proxy) firing at the British bases.
            # Present-tense / new-event phrasing on purpose: recaps of the March 2026 strike
            # ("a drone hit Akrotiri in March") must not re-breach the line every week.
            ('akrotiri_struck', 4, ['missile hits akrotiri', 'missiles hit akrotiri', 'drone hits akrotiri',
                                    'drones hit akrotiri', 'missiles fired at akrotiri', 'fires missiles at akrotiri',
                                    'iran fires missiles at cyprus', 'missiles target akrotiri', 'drones target akrotiri',
                                    'akrotiri under attack', 'new attack on akrotiri', 'second attack on akrotiri',
                                    'missile strike on british base in cyprus', 'drone strike on british base in cyprus',
                                    'sirens at akrotiri']),
            ('akrotiri_used_for_strikes', 3, ['jets from akrotiri', 'flew from akrotiri', 'launched from akrotiri',
                                              'raf typhoons from akrotiri', 'akrotiri used for strikes']),
            ('cyprus_restricts_bases', 3, ['cyprus restricts use of the bases', 'nicosia demands', 'cyprus asks britain',
                                           'protest at akrotiri', 'bases must not be used']),
        ],
    },
    'us_uk': {
        'name': 'The US relationship', 'flag': '🇺🇸', 'icon': '🤝', 'vector': 'us_relationship',
        'role': 'Burnham and Trump, intelligence sharing, tariffs and the trade deal, NATO burden-sharing, the US '
                'positions on the Falklands and Chagos, what Washington asks of Britain in the Iran war',
        'baseline': 10,
        'keywords': ['special relationship', 'trump burnham', 'burnham trump', 'us-uk', 'uk-us', 'us uk trade',
                     'tariffs on britain', 'us ambassador to the uk', 'white house', 'intelligence sharing',
                     'five eyes', 'nato', 'washington'],
        'requires_any': ['trump', 'washington', 'white house', 'u.s.', 'american', 'united states',
                         'special relationship', 'five eyes', 'nato', 'pentagon'],
        'tripwires': [
            ('intel_sharing_suspended', 3, ['suspends intelligence sharing', 'halts intelligence sharing',
                                            'intelligence sharing suspended']),
            ('us_tariffs_uk', 2, ['tariffs on british', 'tariffs on the uk', 'tariff on uk goods']),
            ('us_guarantee_doubt', 3, ['would not defend britain', 'questions commitment to britain',
                                       'trump falklands', 'trump says britain was not there']),
            ('us_uk_deal', 1, ['us-uk trade deal signed', 'technology prosperity deal', 'us and uk sign']),
        ],
    },
    'russia_hybrid': {
        'name': 'Russia inside Britain', 'flag': '🇷🇺', 'icon': '🕵️', 'vector': 'russia_hybrid',
        'role': 'Sabotage and arson plots, undersea cables and pipelines, spy ships in UK waters, poisonings, '
                'cyber attacks, disinformation -- the war Russia fights against Britain without declaring it',
        'baseline': 8,
        'keywords': ['russian sabotage', 'sabotage plot', 'arson', 'undersea cable', 'subsea cable', 'yantar',
                     'spy ship', 'russian submarine', 'russian warship', 'english channel', 'north sea',
                     'gru', 'kremlin', 'novichok', 'poisoning', 'cyber attack', 'russian spies', 'espionage',
                     'mi5', 'counter-terrorism police', 'national security act'],
        'requires_any': ['russia', 'russian', 'kremlin', 'gru', 'moscow', 'yantar', 'novichok', 'wagner'],
        'tripwires': [
            ('sabotage_confirmed', 4, ['convicted of sabotage', 'charged with sabotage', 'russian-backed arson',
                                       'arson attack on behalf of russia', 'sabotage on uk soil',
                                       'russia behind the attack on']),
            ('assassination_plot', 4, ['novichok', 'poisoned in', 'assassination plot in the uk',
                                       'plot to kill in britain']),
            ('cable_cut', 3, ['undersea cable cut', 'subsea cable damaged', 'cable damaged in the north sea',
                              'pipeline damaged', 'cable sabotage']),
            ('spy_ship_shadowed', 2, ['royal navy shadows', 'yantar', 'spy ship in uk waters',
                                      'russian warship in the channel']),
            ('cyber_attack', 3, ['cyber attack on the nhs', 'russian hackers', 'cyber attack blamed on russia']),
        ],
    },
    'ukraine_europe': {
        'name': 'Ukraine & European security', 'flag': '🇺🇦', 'icon': '🛡️', 'vector': 'europe_security',
        'role': 'Military aid (Storm Shadow), the UK-French-led "coalition of the willing" for a post-ceasefire '
                'force, defence spending, NATO\'s eastern flank (Estonia)',
        'baseline': 10,
        'keywords': ['ukraine', 'kyiv', 'zelensky', 'coalition of the willing', 'storm shadow', 'reassurance force',
                     'peacekeepers', 'defence spending', 'ministry of defence', 'british troops', 'estonia',
                     'nato summit', 'european security'],
        'requires_any': ['uk', 'britain', 'british', 'london', 'starmer', 'burnham', 'healey', 'royal navy',
                         'raf', 'ministry of defence', 'mod'],
        'tripwires': [
            ('uk_troops_ukraine', 3, ['british troops deployed to ukraine', 'uk troops arrive in ukraine',
                                      'british soldiers in ukraine', 'reassurance force deploys']),
            ('uk_casualty_ukraine', 4, ['british soldier killed in ukraine', 'british troops killed']),
            ('defence_spending_up', 1, ['defence spending to rise', 'raises defence spending', '3% of gdp on defence',
                                        '3.5% on defence']),
        ],
    },
    'aukus': {
        'name': 'AUKUS & the Indo-Pacific', 'flag': '🇦🇺', 'icon': '🌊', 'vector': 'indo_pacific',
        'role': 'The AUKUS submarine programme with the US and Australia (Barrow, Adelaide), carrier deployments, '
                'Taiwan Strait transits, Five Eyes',
        'baseline': 5,
        'keywords': ['aukus', 'ssn-aukus', 'barrow-in-furness', 'barrow', 'carrier strike group', 'hms prince of wales',
                     'taiwan strait', 'indo-pacific', 'australia', 'five eyes'],
        'requires_any': ['aukus', 'uk', 'britain', 'british', 'royal navy', 'hms'],
        'tripwires': [
            ('aukus_cut', 3, ['aukus scrapped', 'aukus cancelled', 'pentagon review of aukus', 'aukus in doubt',
                              'pulls out of aukus']),
            ('taiwan_transit', 3, ['royal navy taiwan strait', 'british warship transits the taiwan strait',
                                   'hms sails through the taiwan strait']),
            ('aukus_milestone', 1, ['aukus milestone', 'aukus contract', 'aukus agreement signed']),
        ],
    },
}

VECTORS = {
    'government': {'name': 'Government & the Treasury', 'plain': 'the government and public money',
                   'actors': ['government']},
    'opposition': {'name': 'Opposition (both flanks)', 'plain': 'the opposition and the street', 'actors': ['opposition']},
    'union': {'name': 'The Union', 'plain': 'Scotland, Wales and Northern Ireland',
              'actors': ['scotland', 'wales', 'northern_ireland']},
    'overseas': {'name': 'The Overseas Edge', 'plain': 'the territories and bases abroad',
                 'actors': ['falklands_gibraltar', 'chagos', 'cyprus_bases']},
    'us_relationship': {'name': 'The US Relationship', 'plain': 'relations with Washington', 'actors': ['us_uk']},
    'russia_hybrid': {'name': 'Russia inside Britain', 'plain': 'Russian sabotage, spying and pressure',
                      'actors': ['russia_hybrid']},
    'europe_security': {'name': 'Ukraine & European Security', 'plain': 'Ukraine and NATO\'s eastern flank',
                        'actors': ['ukraine_europe']},
    'indo_pacific': {'name': 'AUKUS & the Indo-Pacific', 'plain': 'AUKUS and the Indo-Pacific', 'actors': ['aukus']},
}

RED_LINES = [
    {'id': 'akrotiri', 'label': 'Missiles or drones fired at the British bases in Cyprus (by Iran or a proxy)',
     'tripwires': ['akrotiri_struck'],
     'why': ('It happened once already (an Iranian-made drone from Lebanon, 2 Mar 2026, limited damage). A repeat -- '
             'above all ballistic missiles from Iran itself -- would make Britain a target in a war it says it is '
             'not fighting. Three things follow: (1) London has to decide whether to answer, and Parliament is '
             'divided on the Iran war; (2) the question of NATO\'s Article 5 goes on the table, because the treaty '
             'covers allied forces in the Mediterranean; (3) Cyprus, an EU member, comes under pressure to restrict '
             'the bases -- which would cut Britain\'s main platform for Middle East operations.')},
    {'id': 'gilts', 'label': 'A gilt-market crisis: the Bank of England steps in, or an emergency budget',
     'tripwires': ['gilt_selloff', 'emergency_budget'],
     'why': ('In 2022 the bond market ended a government in six weeks. The City pulse on the stability page '
             'watches the early shape (yields up and the pound down together); this line is the event itself.')},
    {'id': 'indyref2', 'label': 'A formal move toward a second Scottish independence referendum',
     'tripwires': ['section_30_request', 'referendum_bill'],
     'why': ('Holyrood has a pro-independence majority again (SNP + Greens, May 2026). A formal request or a '
             'referendum bill turns talk into a constitutional fight with Westminster -- and Britain\'s nuclear '
             'deterrent is based at Faslane, in Scotland.')},
    {'id': 'south_atlantic', 'label': 'A military incident in the South Atlantic', 'tripwires': ['south_atlantic_incident'],
     'why': ('Argentina reopened the Falklands dispute in September 2026 after Washington declined to back '
             'Britain. An incident would show the dispute has moved from words to ships.')},
    {'id': 'russia_sabotage', 'label': 'Confirmed Russian sabotage, a cut cable or an assassination plot on British soil',
     'tripwires': ['sabotage_confirmed', 'assassination_plot', 'cable_cut'],
     'why': ('Russia has fought an undeclared campaign against Britain since Salisbury (2018). A confirmed attack on '
             'infrastructure or people is the point where it stops being espionage and becomes an act of war in '
             'all but name.')},
    {'id': 'troops_ukraine', 'label': 'British troops deployed in Ukraine, or British troops killed there',
     'tripwires': ['uk_troops_ukraine', 'uk_casualty_ukraine'],
     'why': ('Britain co-leads planning for a post-ceasefire force. Boots on the ground make Britain a party on the '
             'ground; a casualty would test public support and Russia\'s threats against "Western troops".')},
    {'id': 'diego_garcia', 'label': 'A change to US access at Diego Garcia, or Washington blocking the Chagos deal',
     'tripwires': ['diego_garcia_access', 'us_blocks_chagos'],
     'why': ('Diego Garcia is one of the most important US bases in the world for the Middle East and the Indian '
             'Ocean. Britain owns the sovereignty question; Washington owns the use.')},
    {'id': 'stormont', 'label': 'Stormont collapses, or paramilitary violence returns',
     'tripwires': ['stormont_collapse', 'paramilitary_attack'],
     'why': 'Power-sharing has collapsed before (2017-20, 2022-24). Violence would be a different order of problem.'},
]
GREEN_LINES = [
    {'id': 'chagos_done', 'label': 'Chagos treaty ratified', 'tripwires': ['chagos_ratified'],
     'why': 'Closes the legal question over Diego Garcia -- if Washington accepts it.'},
    {'id': 'defence_up', 'label': 'Defence spending raised', 'tripwires': ['defence_spending_up'],
     'why': 'More room to act alone -- the opposite of the gilt red line.'},
    {'id': 'aukus_ok', 'label': 'AUKUS milestone', 'tripwires': ['aukus_milestone'],
     'why': 'Keeps Britain in the Indo-Pacific for a generation.'},
    {'id': 'us_deal', 'label': 'A US-UK deal signed', 'tripwires': ['us_uk_deal'],
     'why': 'Evidence the relationship still delivers.'},
]

MEANINGS = {
    'government': {
        'plain': ('Andy Burnham became prime minister on 20 July 2026, the seventh in ten years. John Healey is '
                  'Chancellor; his first Budget (28 Oct) was received calmly and the fiscal rules held.'),
        'economy': ('The government\'s room to act depends on the gilt market: in 2022 a budget the market did not '
                    'believe ended a prime minister in six weeks.'),
        'not_implied': 'Budget rows and cabinet gossip are ordinary Westminster weather, not instability.',
    },
    'opposition': {
        'plain': ('Reform UK and Labour have swapped the polling lead since the summer; the Conservatives trail both. '
                  'The Greens and independents compete for Labour\'s left.'),
        'not_implied': ('Polls and protests are normal democratic noise. This tracker reads both flanks by the same '
                        'rules; only violence or a collapse in order raises the level.'),
    },
    'union': {
        'plain': ('Three pressure points at once: a pro-independence majority at Holyrood (SNP and Greens, May 2026); '
                  'a Plaid Cymru First Minister in Wales after Labour\'s century in charge ended; and the Irish Sea '
                  'border under the Windsor Framework.'),
        'global': ('The union is also a defence question: the nuclear deterrent is at Faslane in Scotland, and '
                   'Northern Ireland is the UK\'s only land border with the EU.'),
        'not_implied': ('Plaid Cymru supports independence in the long run but governs Wales without a referendum '
                        'plan; Welsh signals are watched for drift, not treated as a crisis.'),
    },
    'overseas': {
        'plain': ('The Falklands, Gibraltar, the Chagos Islands (Diego Garcia) and the Cyprus bases. Each is a '
                  'British promise to someone else -- islanders, Washington, Mauritius, Cyprus.'),
        'global': ('In 2026 the US position moved on both the Falklands and Chagos, and an Iranian-made drone hit '
                   'RAF Akrotiri. The overseas edge is where other people\'s wars and disputes reach Britain first.'),
        'not_implied': 'Sovereignty speeches and anniversary coverage are routine, not escalation.',
    },
    'akrotiri': {
        'plain': ('RAF Akrotiri in Cyprus is Britain\'s main air base for the Middle East. On 2 March 2026 an '
                  'Iranian-made drone launched from Lebanon hit it, causing limited damage.'),
        'global': ('A strike on the bases makes Britain a target in a war it says it is not fighting, raises the '
                   'NATO Article 5 question (the treaty covers allied forces in the Mediterranean), and puts Cyprus, '
                   'an EU member, under pressure to restrict the bases.'),
        'not_implied': 'Reporting that the bases are used for patrols or exercises is routine.',
    },
    'us': {
        'plain': ('The "special relationship" now runs through Burnham and Trump: intelligence (Five Eyes), nuclear '
                  'cooperation, trade, and US positions on the Falklands and Chagos that moved in 2026.'),
        'not_implied': 'Warm or cold words from Washington are not a policy change until something is signed or stopped.',
    },
    'russia': {
        'plain': ('Russia has run an undeclared campaign against Britain since the 2018 Salisbury poisoning: sabotage '
                  'and arson plots, spy ships over cables and pipelines, cyber attacks, disinformation.'),
        'not_implied': 'A Royal Navy ship shadowing a Russian vessel is routine; a cut cable or a charge is not.',
    },
    'ukraine': {
        'plain': ('Britain is one of Ukraine\'s largest military backers and co-leads, with France, planning for a '
                  'post-ceasefire "reassurance force".'),
        'not_implied': 'Aid announcements and summit statements are routine.',
    },
    'aukus': {
        'plain': ('AUKUS: Britain, the US and Australia building nuclear-powered attack submarines together (Barrow '
                  'and Adelaide). It ties Britain to the Indo-Pacific for decades.'),
        'not_implied': 'Programme updates are routine; a cancellation or a Taiwan Strait transit is not.',
    },
}

TRIPWIRE_PLAIN = {
    'cabinet_resignation': ('a cabinet resignation', 'governance'),
    'leadership_challenge': ('a challenge to the prime minister\'s leadership', 'governance'),
    'gilt_selloff': ('a gilt-market sell-off or Bank of England intervention', 'economic'),
    'emergency_budget': ('an emergency budget or budget U-turn', 'economic'),
    'violent_disorder': ('violent disorder on the streets', 'kinetic'),
    'mass_protest': ('a mass protest', 'governance'),
    'defection': ('an MP defecting', 'governance'),
    'by_election_upset': ('a by-election upset', 'governance'),
    'section_30_request': ('a formal request for a second Scottish referendum', 'governance'),
    'referendum_bill': ('a Scottish referendum bill or date', 'governance'),
    'indy_court_case': ('a court case on Scottish independence', 'governance'),
    'welsh_indy_move': ('a move toward a Welsh independence referendum', 'governance'),
    'senedd_crisis': ('a crisis in the Welsh Government', 'governance'),
    'cardiff_london_clash': ('a legal clash between Cardiff and Westminster', 'governance'),
    'stormont_collapse': ('the collapse of power-sharing at Stormont', 'governance'),
    'border_poll_call': ('a border poll being called', 'governance'),
    'paramilitary_attack': ('a paramilitary attack in Northern Ireland', 'kinetic'),
    'south_atlantic_incident': ('a military incident in the South Atlantic', 'kinetic'),
    'argentine_measure': ('a new Argentine measure against the Falklands', 'diplomatic'),
    'us_falklands_shift': ('a shift in the US position on the Falklands', 'diplomatic'),
    'gibraltar_row': ('a Gibraltar border or treaty row', 'diplomatic'),
    'chagos_ratified': ('the Chagos treaty being ratified', 'diplomatic'),
    'us_blocks_chagos': ('Washington blocking or pausing the Chagos deal', 'diplomatic'),
    'diego_garcia_access': ('a change to the use of Diego Garcia', 'kinetic'),
    'akrotiri_struck': ('missiles or drones hitting the British bases in Cyprus', 'kinetic'),
    'akrotiri_used_for_strikes': ('the Cyprus bases being used for strikes', 'kinetic'),
    'cyprus_restricts_bases': ('Cyprus pressing to restrict the British bases', 'diplomatic'),
    'intel_sharing_suspended': ('intelligence sharing being suspended', 'diplomatic'),
    'us_tariffs_uk': ('US tariffs on British goods', 'economic'),
    'us_guarantee_doubt': ('Washington questioning its commitment to Britain', 'diplomatic'),
    'us_uk_deal': ('a US-UK deal being signed', 'diplomatic'),
    'sabotage_confirmed': ('confirmed Russian-backed sabotage in Britain', 'kinetic'),
    'assassination_plot': ('a poisoning or assassination plot in Britain', 'kinetic'),
    'cable_cut': ('an undersea cable or pipeline damaged', 'kinetic'),
    'spy_ship_shadowed': ('a Russian spy ship or warship in UK waters', 'kinetic'),
    'cyber_attack': ('a Russian cyber attack on British systems', 'kinetic'),
    'uk_troops_ukraine': ('British troops deploying to Ukraine', 'kinetic'),
    'uk_casualty_ukraine': ('British troops killed in Ukraine', 'kinetic'),
    'defence_spending_up': ('defence spending being raised', 'economic'),
    'aukus_cut': ('AUKUS being cut or put in doubt', 'diplomatic'),
    'taiwan_transit': ('a Royal Navy transit of the Taiwan Strait', 'kinetic'),
    'aukus_milestone': ('an AUKUS milestone', 'diplomatic'),
}

TRIPWIRE_MEANING = {
    'cabinet_resignation': 'government', 'leadership_challenge': 'government', 'gilt_selloff': 'government',
    'emergency_budget': 'government', 'violent_disorder': 'opposition', 'mass_protest': 'opposition',
    'defection': 'opposition', 'by_election_upset': 'opposition', 'section_30_request': 'union',
    'referendum_bill': 'union', 'indy_court_case': 'union', 'welsh_indy_move': 'union', 'senedd_crisis': 'union',
    'cardiff_london_clash': 'union', 'stormont_collapse': 'union', 'border_poll_call': 'union',
    'paramilitary_attack': 'union', 'south_atlantic_incident': 'overseas', 'argentine_measure': 'overseas',
    'us_falklands_shift': 'overseas', 'gibraltar_row': 'overseas', 'chagos_ratified': 'overseas',
    'us_blocks_chagos': 'overseas', 'diego_garcia_access': 'overseas', 'akrotiri_struck': 'akrotiri',
    'akrotiri_used_for_strikes': 'akrotiri', 'cyprus_restricts_bases': 'akrotiri',
    'intel_sharing_suspended': 'us', 'us_tariffs_uk': 'us', 'us_guarantee_doubt': 'us', 'us_uk_deal': 'us',
    'sabotage_confirmed': 'russia', 'assassination_plot': 'russia', 'cable_cut': 'russia',
    'spy_ship_shadowed': 'russia', 'cyber_attack': 'russia', 'uk_troops_ukraine': 'ukraine',
    'uk_casualty_ukraine': 'ukraine', 'defence_spending_up': 'ukraine', 'aukus_cut': 'aukus',
    'taiwan_transit': 'aukus', 'aukus_milestone': 'aukus',
}

SO_WHAT_RULES = [
    {'tripwires': ['akrotiri_struck'], 'weight': 8.0,
     'confirmed': ('The British bases in Cyprus have been hit, confirmed by 2+ outlets. Britain is now a target in '
                   'the Iran war whether or not it calls itself a party. Watch three things: whether London '
                   'retaliates or stays defensive; whether NATO\'s Article 5 is raised (the treaty covers allied '
                   'forces in the Mediterranean); and whether Cyprus moves to restrict the bases -- Britain\'s main '
                   'Middle East platform.'),
     'single': ('One outlet reports an attack on the British bases in Cyprus; not yet corroborated. In March 2026 '
                'the first reports were accurate -- treat this as serious but unconfirmed.')},
    {'tripwires': ['gilt_selloff', 'emergency_budget'], 'weight': 7.0,
     'confirmed': ('A gilt-market crisis is confirmed by 2+ outlets. This is the 2022 shape: the bond market setting '
                   'the government\'s agenda. Every other vector on this page -- defence, Ukraine, AUKUS -- costs '
                   'money that just got more expensive.'),
     'single': 'One outlet reports gilt-market stress or an emergency budget; check the City pulse on the stability page.'},
    {'tripwires': ['sabotage_confirmed', 'assassination_plot', 'cable_cut'], 'weight': 6.5,
     'confirmed': ('Russian action on British soil or seabed is confirmed. The line between espionage and attack '
                   'has been crossed; watch for expulsions, sanctions and NATO consultations.')},
    {'tripwires': ['section_30_request', 'referendum_bill', 'welsh_indy_move', 'stormont_collapse', 'border_poll_call'],
     'weight': 6.0,
     'confirmed': ('A constitutional move on the union is confirmed. Read Scotland, Wales and Northern Ireland '
                   'together: pressure on one makes the others\' demands cheaper to make -- and Faslane makes '
                   'Scotland a defence question, not just a political one.')},
    {'tripwires': ['south_atlantic_incident', 'us_falklands_shift', 'us_blocks_chagos', 'diego_garcia_access',
                   'us_guarantee_doubt'], 'weight': 5.5,
     'confirmed': ('The overseas edge moved, and Washington is part of it. The common thread of 2026: the US '
                   'guarantee is now conditional, and London is adjusting territory by territory.')},
    {'tripwires': ['uk_troops_ukraine', 'uk_casualty_ukraine'], 'weight': 6.0,
     'confirmed': ('British forces in Ukraine is confirmed. Britain becomes a party on the ground; Russia has said '
                   'Western troops would be targets.')},
    {'tripwires': ['violent_disorder', 'paramilitary_attack'], 'weight': 5.0,
     'confirmed': ('Violence on British streets is confirmed by 2+ outlets. Read it by the same rules whichever '
                   'flank it comes from; watch whether it spreads beyond one town (2024 did).')},
    {'tripwires': ['aukus_cut', 'taiwan_transit'], 'weight': 4.5,
     'confirmed': 'An AUKUS or Indo-Pacific move is confirmed -- Britain\'s reach to Asia either grew or shrank.'},
]
VECTOR_SO_WHAT = {
    'government': (3.2, 'Government and Treasury reporting is busier than usual. Check the gilt-and-pound reading on '
                        'the stability page before reading anything into the politics.'),
    'union': (3.4, 'Reporting on Scotland, Wales and Northern Ireland is up. ' + MEANINGS['union']['global']),
    'overseas': (3.4, 'Reporting on the territories and bases is up. ' + MEANINGS['overseas']['global']),
    'russia_hybrid': (3.2, 'Reporting on Russian pressure inside Britain is up. ' + MEANINGS['russia']['not_implied']),
    'us_relationship': (3.0, 'US-UK reporting is busier than usual -- watch for signed deals or stopped ones, not tone.'),
}
STANDING_SO_WHAT = [
    'The unasked question: how much room does Britain have to act on its own? Money (the gilt market), the union '
    '(Faslane is in Scotland) and the US guarantee (Falklands, Chagos) all set that answer -- and each moved in 2026.',
    'The war Britain says it is not fighting: an Iranian-made drone hit RAF Akrotiri in March 2026. While the Iran '
    'war runs, the Cyprus bases are the point where Middle East escalation lands on British territory first.',
]


# ════════════════════════════════════════════════════════════════════
# EXTRA READS -- the City pulse and the mini wheel
# ════════════════════════════════════════════════════════════════════
def _city_read(redis_get):
    d = redis_get('stability:uk:city_pulse') or {}
    return {'credibility': d.get('credibility_check') or {}, 'top_indicator': d.get('top_indicator'),
            'lens_levels': {k: (v or {}).get('level', 0) for k, v in (d.get('lenses') or {}).items()},
            'scanned_at': d.get('scanned_at')} if d else {}


def _city_signal(t, ctx):
    c = (ctx['extras'].get('city') or {}).get('credibility') or {}
    if c.get('state') == 'credibility_stress':
        return [t.sig('uk_credibility', 3, 'UK: gilt yields up and the pound down together -- the 2022 credibility signature',
                      c.get('text', '') + ' ' + MEANINGS['government']['economy'], 'economic', 'government',
                      actor='government', kind='market_read')]
    if c.get('state') == 'rates_rising':
        return [t.sig('uk_rates', 2, 'UK: gilt yields rising, the pound holding -- expensive, not yet a credibility problem',
                      c.get('text', ''), 'economic', 'government', actor='government', kind='market_read')]
    return []


FRESH_HOURS = 30

# Hub = the UK. Nodes are of three kinds:
#   tracked   -- another Asifah tracker, read live from Redis
#   internal  -- one of this tracker's own actors (rendered by the page from vector/actor levels)
#   untracked -- a real relationship with no sensor yet; shown, and said to be unread
WHEEL_NODES = [
    {'id': 'argentina', 'name': 'Argentina (Falklands)', 'kind': 'tracked', 'key': 'rhetoric:argentina:latest',
     'vector': 'south_atlantic', 'relationship': 'challenger', 'page': 'rhetoric-argentina.html',
     'why': 'Argentina reopened the Falklands claim in Sep 2026; its tracker\'s South Atlantic vector is read here.'},
    {'id': 'cyprus', 'name': 'Cyprus (the bases)', 'kind': 'tracked', 'key': 'rhetoric:cyprus:latest',
     'relationship': 'host', 'page': 'rhetoric-cyprus.html',
     'why': 'Host of the Sovereign Base Areas; Nicosia\'s mood sets what Akrotiri can be used for.'},
    {'id': 'ukraine', 'name': 'Ukraine', 'kind': 'tracked', 'key': 'rhetoric:ukraine:latest',
     'relationship': 'security_partner', 'page': 'rhetoric-ukraine.html',
     'why': 'Britain co-leads post-ceasefire planning; a British force would be on the ground here.'},
    {'id': 'us', 'name': 'United States', 'kind': 'tracked', 'key': 'rhetoric:us:latest',
     'relationship': 'guarantor', 'page': 'rhetoric-us.html',
     'why': 'The guarantee behind the Falklands, Chagos/Diego Garcia, Five Eyes and the deterrent.'},
    {'id': 'russia', 'name': 'Russia', 'kind': 'tracked', 'key': 'rhetoric:russia:latest',
     'relationship': 'adversary_inbound', 'page': 'rhetoric-russia.html',
     'why': 'The adversary pressing inward: cables, spy ships, sabotage, poisonings.'},
    {'id': 'scotland', 'name': 'Scotland', 'kind': 'internal', 'actor': 'scotland', 'relationship': 'union'},
    {'id': 'wales', 'name': 'Wales', 'kind': 'internal', 'actor': 'wales', 'relationship': 'union'},
    {'id': 'northern_ireland', 'name': 'Northern Ireland', 'kind': 'internal', 'actor': 'northern_ireland',
     'relationship': 'union'},
    {'id': 'gibraltar_falklands', 'name': 'Gibraltar & the Falklands', 'kind': 'internal',
     'actor': 'falklands_gibraltar', 'relationship': 'territory'},
    {'id': 'chagos', 'name': 'Chagos / Diego Garcia', 'kind': 'internal', 'actor': 'chagos', 'relationship': 'territory'},
    {'id': 'australia', 'name': 'Australia (AUKUS)', 'kind': 'untracked', 'actor': 'aukus', 'relationship': 'treaty_partner',
     'why': 'No Australia tracker yet (planned on the Asia backend). The UK side of AUKUS is read by this tracker.'},
    {'id': 'mauritius', 'name': 'Mauritius', 'kind': 'untracked', 'relationship': 'claimant',
     'why': 'The Chagos claimant; no tracker. Read through the Chagos actor.'},
    {'id': 'caribbean', 'name': 'Caribbean Commonwealth', 'kind': 'untracked', 'relationship': 'commonwealth',
     'why': 'Jamaica, the Overseas Territories and the realms; debt, migration and offshore money. No tracker.'},
]
_LV = {'low': 0, 'normal': 1, 'elevated': 2, 'high': 3, 'surge': 4}


def _age_h(ts):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(str(ts).replace('Z', '+00:00'))).total_seconds() / 3600
    except Exception:
        return None


def _wheel_read(redis_get):
    """Live read of the tracked nodes. Internal nodes are filled in by the page
    from this tracker's own actor levels; untracked nodes are listed honestly."""
    nodes = []
    for n in WHEEL_NODES:
        node = {k: v for k, v in n.items() if k != 'key'}
        if n['kind'] == 'tracked':
            d = redis_get(n['key']) or {}
            ts = d.get('scanned_at') or d.get('timestamp') or d.get('last_updated')
            age = _age_h(ts) if ts else None
            if not d or age is None or age > FRESH_HOURS:
                node.update({'state': 'not_reporting', 'level': None,
                             'text': 'Not reporting this cycle (no fresh scan) -- unread, not calm.'})
            else:
                lvl = d.get('theatre_level')
                if n.get('vector'):
                    vl = (d.get('vector_levels') or {}).get(n['vector'])
                    lvl = _LV.get(vl, lvl) if isinstance(vl, str) else (vl if vl is not None else lvl)
                try:
                    lvl = int(lvl)
                except (TypeError, ValueError):
                    lvl = 0
                text = d.get('top_indicator') or d.get('bluf') or d.get('signal_text_short') or ''
                if isinstance(text, dict):
                    text = text.get('text') or text.get('headline') or ''
                node.update({'state': 'lit' if lvl >= 2 else 'dark', 'level': lvl,
                             'text': str(text)[:260], 'age_hours': round(age, 1)})
        else:
            node.update({'state': 'internal' if n['kind'] == 'internal' else 'untracked'})
        nodes.append(node)
    return {'hub': 'uk', 'title': 'THE UK WHEEL', 'nodes': nodes,
            'note': ('Tracked nodes are read live from their own trackers; the union and territory nodes are this '
                     'tracker\'s own actors; untracked nodes have no sensor yet and are shown so the gap is visible.')}


CONFIG = {
    'slug': 'uk', 'name': 'United Kingdom', 'flag': '🇬🇧', 'version': VERSION, 'facts_as_of': '2026-11-04',
    'actors': ACTORS, 'vectors': VECTORS,
    'rss_feeds': {
        'bbc_uk': {'url': 'https://feeds.bbci.co.uk/news/uk/rss.xml', 'name': 'BBC News', 'language': 'en', 'max': 50},
        'bbc_politics': {'url': 'https://feeds.bbci.co.uk/news/politics/rss.xml', 'name': 'BBC News', 'language': 'en', 'max': 40},
        'guardian_politics': {'url': 'https://www.theguardian.com/politics/rss', 'name': 'The Guardian', 'language': 'en', 'max': 40},
        'sky_politics': {'url': 'https://feeds.skynews.com/feeds/rss/politics.xml', 'name': 'Sky News', 'language': 'en', 'max': 30},
        'ukdj': {'url': 'https://ukdefencejournal.org.uk/feed/', 'name': 'UK Defence Journal', 'language': 'en', 'max': 30},
        'nation_cymru': {'url': 'https://nation.cymru/feed/', 'name': 'Nation.Cymru', 'language': 'en', 'max': 25},
        'mercopress': {'url': 'https://en.mercopress.com/rss', 'name': 'MercoPress', 'language': 'en', 'max': 25},
    },
    'google_queries': [
        ('Burnham government', 'en-GB', 'GB'), ('Healey Treasury gilts', 'en-GB', 'GB'),
        ('Reform UK Farage OR Badenoch OR Greens poll', 'en-GB', 'GB'),
        ('Swinney independence referendum OR Holyrood', 'en-GB', 'GB'),
        ('Plaid Cymru ap Iorwerth OR Senedd', 'en-GB', 'GB'),
        ('Stormont OR "Windsor Framework" OR "border poll"', 'en-GB', 'GB'),
        ('Falklands OR Gibraltar OR Chagos OR "Diego Garcia"', 'en-GB', 'GB'),
        ('Akrotiri OR "British bases" Cyprus', 'en-GB', 'GB'),
        ('Russian sabotage Britain OR "undersea cable" OR "spy ship"', 'en-GB', 'GB'),
        ('"coalition of the willing" Britain Ukraine', 'en-GB', 'GB'),
        ('AUKUS Britain', 'en-GB', 'GB'), ('Trump Burnham', 'en-US', 'US'),
    ],
    'gdelt_langs': (('eng', 'gdelt_en'),),
    'gdelt_en': ['Burnham government Britain', 'Akrotiri Cyprus base', 'Scotland independence referendum'],
    'newsapi_queries': ['Burnham', 'Akrotiri'],
    'brave_queries': ['UK government news Burnham', 'Britain Cyprus bases'],
    'scrub': ['new england', 'new south wales', 'prince of wales'],   # 'HMS Prince of Wales' is a carrier, not Wales
    'context_terms': ('uk', 'u.k.', 'britain', 'british', 'united kingdom', 'england', 'scotland', 'scottish',
                      'wales', 'welsh', 'northern ireland', 'london', 'westminster', 'whitehall', 'downing street',
                      'burnham', 'healey', 'farage', 'badenoch', 'swinney', 'holyrood', 'senedd', 'stormont',
                      'plaid cymru', 'falklands', 'gibraltar', 'chagos', 'diego garcia', 'akrotiri', 'dhekelia',
                      'royal navy', 'raf', 'mi5', 'mi6', 'gchq', 'faslane', 'aukus', 'gilts', 'bank of england'),
    'own_outlets': ('bbc', 'the guardian', 'sky news', 'the times', 'telegraph', 'financial times', 'independent',
                    'uk defence journal', 'nation.cymru', 'the scotsman', 'the herald', 'belfast telegraph',
                    'evening standard', 'itv'),
    'own_tld': '.co.uk/',
    'foreign_markers': ('new south wales', 'new england', 'canberra'),
    'exclusions': {
        'akrotiri_struck': ('anniversary', 'drill', 'exercise', 'simulation', 'documentary', 'one year since'),
        'south_atlantic_incident': ('1982', 'anniversary', 'veterans', 'documentary', 'film'),
        'assassination_plot': ('salisbury anniversary', 'inquiry', 'litvinenko inquiry', 'documentary', 'drama',
                               'series', '2018', '2006'),
        'violent_disorder': ('2024 riots', 'sentenced', 'jailed for', 'anniversary', 'last summer'),
        'paramilitary_attack': ('troubles', 'legacy', 'inquest', '1970s', '1980s', 'anniversary'),
        'gilt_selloff': ('2022', 'truss', 'anniversary', 'lessons of'),
        'section_30_request': ('rules out', 'will not request', 'no plans'),
        'welsh_indy_move': ('rules out', 'no plans', 'not a priority'),
        'uk_troops_ukraine': ('will not', 'rules out', 'no plans', 'if a ceasefire'),
        'spy_ship_shadowed': ('documentary',),
    },
    'red_lines': RED_LINES, 'green_lines': GREEN_LINES,
    'meanings': MEANINGS, 'tripwire_plain': TRIPWIRE_PLAIN, 'tripwire_meaning': TRIPWIRE_MEANING,
    'actor_meaning': {'government': 'government', 'opposition': 'opposition', 'scotland': 'union', 'wales': 'union',
                      'northern_ireland': 'union', 'falklands_gibraltar': 'overseas', 'chagos': 'overseas',
                      'cyprus_bases': 'akrotiri', 'us_uk': 'us', 'russia_hybrid': 'russia',
                      'ukraine_europe': 'ukraine', 'aukus': 'aukus'},
    'vector_pressure': {'government': 'economic', 'opposition': 'governance', 'union': 'governance',
                        'overseas': 'diplomatic', 'us_relationship': 'diplomatic', 'russia_hybrid': 'kinetic',
                        'europe_security': 'kinetic', 'indo_pacific': 'diplomatic'},
    'so_what_rules': SO_WHAT_RULES, 'vector_so_what': VECTOR_SO_WHAT, 'standing_so_what': STANDING_SO_WHAT,
    'quiet_so_what': ('The UK reads quiet this cycle. What would change that: a strike on the Cyprus bases, a gilt '
                      'crisis, a formal referendum move in Scotland, confirmed Russian sabotage, or British troops '
                      'deploying to Ukraine.'),
    'background': MEANINGS['government']['plain'],
    'spokes': [
        ('us', 'us_uk', 'treaty_ally',
         'Britain is the US\'s closest military and intelligence ally (Five Eyes, the deterrent, Diego Garcia) -- '
         'and in 2026 Washington\'s positions on the Falklands and Chagos moved under London\'s feet.'),
        ('russia', 'russia_hybrid', 'inbound_target',
         'Russia\'s undeclared campaign against Britain: sabotage and arson plots, spy ships over cables, poisonings.'),
        ('iran', 'cyprus_bases', 'target',
         'An Iranian-made drone launched from Lebanon hit RAF Akrotiri on 2 Mar 2026; the Cyprus bases fly Middle East missions.'),
    ],
    'hub_names': {'us': 'US', 'russia': 'Russia', 'iran': 'Iran'},
    'fingerprints': {'uk_bases_struck': ['akrotiri_struck'],
                     'uk_fiscal_stress': ['gilt_selloff', 'emergency_budget'],
                     'uk_union_stress': ['section_30_request', 'referendum_bill', 'stormont_collapse', 'welsh_indy_move'],
                     'uk_russia_hybrid': ['sabotage_confirmed', 'assassination_plot', 'cable_cut']},
    'extra_reads': {'city': _city_read, 'uk_wheel': _wheel_read},
    'extra_signals': [_city_signal],
}

tracker = CountryRhetoricTracker(CONFIG)


def scan_uk_rhetoric(force=False):
    return tracker.scan(force=force)


def register_uk_rhetoric_endpoints(app, force_gate=None, start_background=True):
    tracker.register(app, force_gate=force_gate, start_background=start_background, warmup_seconds=300)
