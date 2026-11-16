"""Week 8 deterministic summaries using Week 3 spans and Week 6 semantics.

No model calls, tokenizer downloads, or human-reference consumption occur here.
Source-supported means checked against supplied evidence, not human-verified.
"""
from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
import math
import re

import nltk

from scripts.entity_extractor import EntityExtractor, PRICE_CONTEXT_RE, QUANTITY
from scripts.signal_extractor import _boolean, _negated


FIELDS = {
    'bedrooms': ('L_Keyword2', 'BedroomsTotal'),
    'bathrooms': ('LM_Dec_3', 'BathroomsTotalDecimal'),
    'price': ('L_SystemPrice', 'ListPrice'),
    'city': ('L_City', 'City'),
}
UNCERTAIN = re.compile(
    r'\b(?:no|not|without|lacks?|never|potential|possibly|possibility|opportunity|'
    r'imagine|envision|could|may|might|planned|proposed|optional|future|'
    r'room for|space for|room to|space to|build|add|install|membership|'
    r'nearby|near|walking distance|minutes from|close to|across the street)\b', re.I)
MULTI_UNIT = re.compile(
    r'\b(?:guest (?:house|home|unit)|adu|duplex|triplex|fourplex|(?:dwelling|residential) units|'
    r'main (?:home|house|residence)|additional bedrooms?|half baths?|'
    r'half bathrooms?|[\w]+ or [\w]+ bedrooms?)\b', re.I)
MODEL_RANGE = re.compile(
    r'\b(?:homes|residences|floor plans)\s+(?:range|ranging)|'
    r'\d\s*[-–]?\s*(?:,|to|or|and|[-–])\s*(?:\d\s*[-–]?\s*,?\s*(?:and\s+)?)?\d\s*[- ]?bedrooms?\b', re.I)
DESCRIPTION = re.compile(
    r'\b(?:single[- ](?:level|story)|ranch[- ]style|located|situated|'
    r'overlooking|renovated|remodeled|updated|views?|historic|bungalow)\b', re.I)
STOP = {'a', 'an', 'the', 'this', 'is', 'and', 'with', 'of', 'in', 'to', 'home', 'property', 'has'}


def mapping(value):
    return value if isinstance(value, Mapping) else {}


def number(value, field):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        result = float(str(value).replace(',', '').strip().lstrip('$'))
    except (ValueError, TypeError):
        return None
    if not math.isfinite(result) or result < 0 or (field == 'price' and result == 0):
        return None
    if field == 'bedrooms' and not result.is_integer():
        return None
    return int(result) if result.is_integer() else result


def feature_key(label):
    low = label.casefold()
    if re.search(r'\bpools?\b', low):
        if re.search(r'\b(?:community|association|shared)\b', low):
            return 'community_pool'
        if 'private' in low:
            return 'private_pool'
        return 'pool'
    for key in ('garage', 'fireplace', 'patio', 'kitchen', 'balcony', 'parking', 'closet'):
        if key in low:
            return key
    return re.sub(r'[^\w]+', ' ', low).strip()


def words(text):
    return set(re.findall(r'\w+', text.casefold())) - STOP


class ListingSummarizer:
    def __init__(self):
        self.extractor = EntityExtractor()
        try:
            self.tokenizer = deepcopy(nltk.data.load('tokenizers/punkt/english.pickle'))
        except LookupError as exc:
            raise RuntimeError('Install the NLTK English punkt resource before running Week 8; no automatic downloads are performed.') from exc
        self.tokenizer._params.abbrev_types.update({'sq', 'ft', 'sqft', 'approx', 'dr', 'st', 'ave', 'blvd', 'rd', 'mr', 'mrs'})

    def sentences(self, remarks):
        """Punkt boundaries; exact source substrings (including decimal numbers)."""
        if not isinstance(remarks, str) or not remarks.strip():
            return []
        spans = []
        for a, b in self.tokenizer.span_tokenize(remarks):
            # Punkt can leave the final '!' of an all-caps advert as its own
            # sentence. Reattach punctuation without changing the source slice.
            if spans and not re.search(r'\w', remarks[a:b]):
                spans[-1] = (spans[-1][0], b)
            else:
                spans.append((a, b))
        return [remarks[a:b].strip() for a, b in spans if remarks[a:b].strip()]

    @staticmethod
    def _limit(value):
        if isinstance(value, bool) or not isinstance(value, int):
            return 2
        return min(3, max(2, value))

    def lead2_summary(self, remarks):
        return ' '.join(self.sentences(remarks)[:2])

    @lru_cache(maxsize=4096)
    def _analyze(self, sentence):
        claims, features, denied = {}, [], set()
        spans = self.extractor.extract_spans(sentence)
        for start, end, label in spans:
            text = sentence[start:end]
            if label in ('BEDROOM', 'BATHROOM', 'PRICE'):
                field = {'BEDROOM': 'bedrooms', 'BATHROOM': 'bathrooms', 'PRICE': 'price'}[label]
                value = self.extractor._price_value(text) if field == 'price' else self.extractor._quantity_value(text)
                if value is not None:
                    claims.setdefault(field, set()).add(value)
            elif label == 'AMENITY':
                # Clauses separated by 'but' have independent polarity.
                before = re.split(r';|\bbut\b', sentence[:start], flags=re.I)[-1]
                after = re.split(r';|\bbut\b', sentence[end:], flags=re.I)[0]
                key = feature_key(text)
                if key == 'pool':
                    scope = before[-35:]
                    if re.search(r'\b(?:community|association|shared)\b', scope, re.I):
                        key = 'community_pool'
                        text = 'community pool'
                negated = _negated(sentence, start, end) or bool(re.search(
                    r'\b(?:no|without|lacks?|not)\b[^;.!?]*$', before, re.I)) or bool(re.match(
                    r'\s+(?:(?:is|are|was|were)\s+)?(?:absent|removed|unavailable|not\b)', after, re.I))
                if negated:
                    denied.add(key)
                    continue
                if UNCERTAIN.search(before) or re.match(r'\s+(?:could|may|might|can|will|to be)\b', after, re.I):
                    continue
                features.append({'key': key, 'value': text.strip(), 'source': 'remarks', 'evidence': sentence})
        return claims, features, denied

    def _context(self, remarks, source=None):
        sentences = self.sentences(remarks)
        analyses = [self._analyze(s) for s in sentences]
        conflicts = set()
        all_claims = {}
        positive, negative = set(), set()
        for claims, features, denied in analyses:
            for key, values in claims.items():
                all_claims.setdefault(key, set()).update(values)
            positive.update(f['key'] for f in features)
            negative.update(denied)
        conflicts.update(positive & negative)
        if 'pool' in negative:
            conflicts.update(positive & {'pool', 'private_pool', 'community_pool'})
        if 'pool' in positive and negative & {'private_pool', 'community_pool'}:
            conflicts.add('pool')
        field_conflicts = {k for k, v in all_claims.items() if len(v) > 1}
        source = mapping(source)
        supported = {}
        for field, names in FIELDS.items():
            candidates = []
            for name in names:
                raw = source.get(name)
                if field == 'city':
                    value = raw.strip() if isinstance(raw, str) else None
                    if not value or value.casefold() in {'other', 'unknown', 'none', 'null', 'n/a'} or re.search(r'[.!?\n]', value):
                        continue
                else:
                    value = number(raw, field)
                if value is not None:
                    candidates.append((name, value))
            if candidates and len({v for _, v in candidates}) == 1:
                name, value = candidates[0]
                supported[field] = {'value': value, 'source': name, 'evidence': f'{name}={source[name]}'}
            elif candidates:
                field_conflicts.add(field)
        # A supplied total wins over textual mentions; exclude conflicting text.
        for field, fact in supported.items():
            if field in all_claims and any(v != fact['value'] for v in all_claims[field]):
                field_conflicts.add(field)
        for field in ('bedrooms', 'bathrooms', 'price'):
            if field in supported or field in field_conflicts:
                continue
            ambiguous_units = any(
                MULTI_UNIT.search(s) and (not UNCERTAIN.search(s) or bool(claims))
                for s, (claims, _, _) in zip(sentences, analyses)
            )
            if field in ('bedrooms', 'bathrooms') and (ambiguous_units or MODEL_RANGE.search(remarks if isinstance(remarks, str) else '')):
                continue
            values = all_claims.get(field, set())
            if len(values) != 1:
                continue
            value = next(iter(values))
            for sentence, (claims, _, _) in zip(sentences, analyses):
                if value not in claims.get(field, set()) or UNCERTAIN.search(sentence):
                    continue
                if field in ('bedrooms', 'bathrooms') and re.search(
                    r'\b(?:each|per unit|additional|secondary|upstairs|downstairs|main level|guest unit)\b', sentence, re.I
                ):
                    continue
                if field == 'price' and not PRICE_CONTEXT_RE.search(sentence):
                    continue
                # Full/half components are not automatically a total bathroom count.
                if field == 'bathrooms' and re.search(r'\b(?:full|half|additional|each)\b', sentence, re.I):
                    continue
                supported[field] = {'value': value, 'source': 'remarks', 'evidence': sentence}
                break
        features = []
        for _, found, _ in analyses:
            features.extend(f for f in found if f['key'] not in conflicts)
        for column, key, label in (
            ('PoolPrivateYN', 'private_pool', 'private pool'),
            ('GarageYN', 'garage', 'garage'), ('FireplaceYN', 'fireplace', 'fireplace'),
        ):
            state = _boolean(source.get(column))
            if state is False:
                conflicts.add(key)
                if key == 'private_pool':
                    conflicts.add('pool')  # Unscoped pool cannot prove community access.
            elif state is True and key not in negative and not (key == 'private_pool' and 'pool' in negative):
                features.append({'key': key, 'value': label, 'source': column, 'evidence': f'{column}={source[column]}'})
        pool_tokens = {x.strip().casefold() for x in str(source.get('PoolFeatures') or '').split(',')}
        if pool_tokens == {'none'}:
            conflicts.update({'pool', 'private_pool', 'community_pool'})
        elif pool_tokens & {'community', 'association'} and not negative & {'pool', 'community_pool'}:
            features.append({'key': 'community_pool', 'value': 'community pool', 'source': 'PoolFeatures', 'evidence': str(source['PoolFeatures'])})
        # Prefer informative, supported phrases; stable ties follow source order.
        distinct = {}
        for f in sorted(features, key=lambda f: -len(f['value'].split())):
            if f['key'] not in conflicts:
                distinct.setdefault(f['key'], f)
        if 'private_pool' in distinct or 'community_pool' in distinct:
            distinct.pop('pool', None)
        return sentences, analyses, supported, list(distinct.values()), conflicts, field_conflicts

    def supported_evidence(self, remarks, listing_data):
        """Audit trail; never labels source evidence as a human verification."""
        data = mapping(listing_data)
        source = mapping(data.get('source_fields')) if 'source_fields' in data else data
        _, _, facts, features, conflicts, field_conflicts = self._context(remarks, source)
        return {'fields': facts, 'features': features, 'conflicting_features': sorted(conflicts),
                'conflicting_fields': sorted(field_conflicts), 'human_verified': False,
                'status': 'automatically_source_supported_not_human_verified'}

    def _select(self, remarks, entities, limit, source=None, covered=None):
        sentences, analyses, facts, features, conflicts, field_conflicts = self._context(remarks, source)
        hints = mapping(entities)
        if isinstance(hints.get('entities'), Mapping):
            hints = hints['entities']
        covered = set(covered or ())
        candidates = []
        supported_features = {f['key'] for f in features}
        for i, (sentence, (claims, found, denied)) in enumerate(zip(sentences, analyses)):
            if denied & conflicts or any(f['key'] in conflicts for f in found) or any(k in field_conflicts for k in claims):
                continue
            tags = {f['key'] for f in found if f['key'] in supported_features}
            score = min(len(tags), 3) * 2.0 + (0.35 if i == 0 else 0)
            if DESCRIPTION.search(sentence):
                tags.add('description')
                score += 0.5
            for field, values in claims.items():
                fact = facts.get(field, {}).get('value')
                expected = number(hints.get(field), field)
                if fact in values and (expected is None or expected == fact):
                    tags.add(field)
                    score += 3 if field in ('bedrooms', 'bathrooms') else 2
            city = facts.get('city', {}).get('value') or hints.get('city')
            if isinstance(city, str) and city.strip() and re.search(r'(?<!\w)' + re.escape(city.strip()) + r'(?!\w)', sentence, re.I):
                tags.add('city'); score += 1.5
            if not tags and covered:
                continue
            if covered and not tags - covered:
                continue
            score -= 3 * len(set(claims) & covered)
            # Penalize marketing-only and excessively long sentences, without editing text.
            score -= max(0, len(sentence.split()) - 45) * 0.06
            candidates.append((i, sentence, tags, score))
        selected = []
        while candidates and len(selected) < limit:
            ranked = []
            for candidate in candidates:
                i, sentence, tags, base = candidate
                if any(' '.join(sentence.casefold().split()) == ' '.join(s.casefold().split()) for _, s, _, _ in selected):
                    continue
                similarity = max((len(words(sentence) & words(s)) / max(1, len(words(sentence) | words(s))) for _, s, _, _ in selected), default=0)
                if similarity >= .72 or (tags and tags <= covered):
                    continue
                ranked.append((base + 1.5 * len(tags - covered) - 4 * similarity, -i, candidate))
            if not ranked:
                break
            chosen = max(ranked, key=lambda x: (x[0], x[1]))[2]
            selected.append(chosen); covered.update(chosen[2]); candidates.remove(chosen)
        return [s for _, s, _, _ in sorted(selected)]

    def extractive_summary(self, remarks, entities, num_sentences=2):
        """Select exact sentences; hints are scored only when supported by text."""
        return ' '.join(self._select(remarks, entities, self._limit(num_sentences)))

    def _hybrid_facts(self, remarks, source):
        """Recover explicit whole-property counts without changing extractive rules."""
        facts = self.supported_evidence(remarks, source)['fields'].copy()
        text = remarks if isinstance(remarks, str) else ''
        # Multiple buildings and alternative floor plans must not become totals.
        multiple = bool(re.search(r'\b(?:guest (?:house|home|unit)|adu|duplex|triplex|ancillary buildings)\b', text, re.I))
        if multiple or MODEL_RANGE.search(text):
            return facts
        for field, noun in (('bedrooms', r'bedrooms?'), ('bathrooms', r'(?:bathrooms?|baths?)')):
            if field in facts:
                continue
            supplied={number(source.get(name),field) for name in FIELDS[field]} - {None}
            if len(supplied)>1:
                continue
            found = []
            pattern = rf'\b({QUANTITY})[ -]+(?:(?:pristine|roomy|spacious|generously sized|full|en-suite|ensuite)\s*(?:and\s+)?)*{noun}\b'
            for sentence in self.sentences(text):
                for match in re.finditer(pattern, sentence, re.I):
                    prefix = re.sub(r'\([^)]*\)', '', sentence[:match.start()])
                    suffix = sentence[match.end():]
                    # Scope to this claim, not unrelated location/marketing text.
                    if re.search(r'\b(?:each|per unit|additional|secondary|upstairs|downstairs|guest|planned|proposed|future|could|would|not|no|without)\b', prefix, re.I):
                        continue
                    if re.match(r'\s+(?:upstairs|downstairs|per unit)\b', suffix, re.I):
                        continue
                    if field == 'bathrooms' and '.' not in match.group(1) and re.search(r'\bhalf[- ]bath', text, re.I):
                        continue
                    value = self.extractor._quantity_value(match.group())
                    if value is not None:
                        found.append((value, sentence))
            values = {v for v, _ in found}
            if len(values) == 1:
                value, sentence = found[0]
                facts[field] = {'value': value, 'source': 'remarks', 'evidence': sentence}
        return facts

    def hybrid_evidence(self, remarks, listing_data):
        """Hybrid-only supported facts, conditions and short feature phrases.

        Every feature retains a source span. Conservative polarity and project
        gates take priority over coverage; no references or listing IDs are used.
        """
        data = mapping(listing_data)
        source = mapping(data.get('source_fields')) if 'source_fields' in data else data
        text = remarks if isinstance(remarks, str) else ''
        facts = self._hybrid_facts(text, source)
        conditions = []
        unbuilt = bool(re.search(r'\b(?:before construction begins|not (?:yet )?(?:been )?(?:built|constructed)|currently a homesite|vacant (?:land|lot)|proposed (?:home|residence))\b', text, re.I))
        for pattern, label in (
            (r'\bstripped to the studs\b', 'stripped to the studs'),
            (r'\bawaiting (?:a )?(?:\w+ )?restoration\b', 'awaiting restoration'),
            (r'\b(?:sold|selling|sale|offered|selling it|being sold)\s+[\"\x27]?(?:strictly\s+)?as[- /]is\b|\bas[- ]is condition\b', 'offered as-is'),
            (r'\b(?:needs?|requires?|in need of)\s+(?:(?:some|a little)\s+)?(?:renovation|repairs|work)\b|\bfixer[- ]upper\b', 'in need of renovation'),
            (r'\b(?:needs?|in need of)\s+(?:(?:some|a little)\s+)?TLC\b', 'in need of TLC'),
            (r'\bunder construction\b', 'under construction'),
        ):
            for sentence in self.sentences(text):
                match = re.search(pattern, sentence, re.I)
                if match and not re.search(r'\b(?:no|not|without)\b',sentence[:match.start()],re.I):
                    conditions.append(label); break
        if not conditions and re.search(r'(?:Fixer|RepairsMajor)',str(source.get('PropertyCondition') or ''),re.I):
            conditions.append('in need of renovation')
        if unbuilt:
            conditions.insert(0, 'a site for proposed construction, not a completed residence' if re.search(r'\b(?:proposed|plans|construction|constructed)\b',text,re.I) else 'vacant land')
            # Counts in structured data may describe the proposed design as well.
            facts = {k:v for k,v in facts.items() if k not in ('bedrooms','bathrooms')}
        if re.search(r'\brenderings?\b', text, re.I):
            conditions.append('renderings may not reflect the final condition')
        features = []
        # Rank distinctive physical facts above generic room names. Patterns
        # extract noun phrases, not unrestricted sentence rewrites.
        q = QUANTITY
        rules = [
            ('acreage', 10, r'\b(?:\d+(?:\.\d+)?[- ]acres?|quarter[- ]acre)\b'),
            ('solar', 10, r'\b(?:(?:paid[- ]off|owned)\s+)?solar(?:\s+(?:panels?|system|array))?\b'),
            ('battery', 9, r'\b(?:dual\s+)?Tesla Powerwall(?:\s+backup)?\b'),
            ('guest', 10, r'\b(?:(?:detached|separate)\s+)?(?:guest (?:house|unit)|backhouse|ADU)\b'),
            ('vineyard', 10, r'\b(?:\d+(?:\.\d+)?[- ]acre\s+)?vineyards?\b|\bwinery\b'),
            ('lake', 10, r'\b(?:\d+(?:\.\d+)?[- ]acre\s+)?(?:bass-filled\s+)?lake\b'),
            ('equestrian', 10, r'\bequestrian facilities\b'),
            ('garage', 7, rf'\b(?:(?:detached|attached)\s+)?{q}[ -]+car[ -]+(?:(?:attached|detached)\s+)?garage\b'),
            ('parking', 7, r'\b(?:RV parking|boat parking|dual driveways|two driveways)\b'),
            ('kitchen', 9, r'\b(?:(?:newly|beautifully|fully)\s+)?(?:renovated|remodeled|updated|upgraded|custom upgraded)\s+(?:chef.s\s+)?kitchen\b'),
            ('view', 8, r'\b(?:(?:panoramic|sweeping|spectacular)\s+)?(?:mountain|ocean|city[- ](?:to[- ]ocean|lights?)|valley|canyon)\s+views?\b'),
            ('pool', 8, r'\b(?:(?:private|community|shared|swimming|sparkling)\s+)?pools?\b'),
            ('patio', 7, r'\b(?:(?:private|covered|enclosed|landscaped)\s+)?(?:patio|courtyard)\b'),
            ('deck', 7, r'\b(?:(?:refreshed|updated|expansive|private)\s+)?deck\b'),
            ('garden', 6, r'\b(?:(?:landscaped|mature|rose|Victorian-inspired)\s+)?gardens?\b'),
            ('pond', 8, r'\b(?:recirculating\s+)?pond\b'),
            ('waterfall', 8, r'\bwaterfall\b'),
            ('laundry', 6, r'\b(?:in[- ]unit (?:laundry|washer/dryer)|laundry (?:room|area))\b'),
            ('balcony', 6, r'\b(?:(?:private|large)\s+)?balcony\b'),
            ('flooring', 7, r'\b(?:(?:new|brand-new|hardwood|hard wood|travertine|white oak|wood)\s+)(?:flooring|floors)\b'),
            ('doors', 7, r'\b(?:bifold|French) doors\b'),
            ('fireplace', 5, r'\b(?:(?:living[- ]room|wood-burning)\s+)?fireplace\b'),
            ('gym', 6, r'\b(?:fitness center|exercise room|gym)\b'),
            ('tennis', 6, r'\btennis courts?\b'),
            ('landscaping', 8, r'\b(?:drought-tolerant landscaping|artificial turf|low-maintenance (?:yard|backyard))\b'),
            ('flex', 8, r'\bflex space\b'),
            ('terrace', 7, r'\b(?:rooftop|expansive) terrace\b'),
            ('spa', 6, r'\bspa\b'),
            ('carport', 6, r'\bcarport\b'),
            ('carpet', 7, r'\bnew carpet\b'),
            ('age', 11, r'\b55\+ age-qualified community\b|\bsenior community\b'),
            ('glass', 8, r'\bfloor-to-ceiling(?:, full-wall)? sliding glass doors\b'),
            ('countertops', 8, r'\b(?:granite|quartz) countertops?\b'),
            ('parking_boat', 8, r'\bparking (?:with )?space for boats, trailers, (?:and|or) recreational vehicles\b'),
            ('size', 6, r'\b[\d,]+\+?[- ](?:square[- ](?:foot|feet)|sq\.?\s*ft\.?|SF)\b'),
        ]
        sentences = self.sentences(text)
        denied = set()
        uncertain = set()
        for key, priority, pattern in rules:
            for sentence in sentences:
                for match in re.finditer(pattern, sentence, re.I):
                    before = re.split(r'[;]|\bbut\b', sentence[:match.start()], flags=re.I)[-1]
                    after = sentence[match.end():]
                    if _negated(sentence, match.start(), match.end()) or re.search(r'\b(?:no|without|lacks?|not)\b[^,;]*$', before, re.I) or re.match(r'\s+(?:(?:is|are)\s+)?(?:absent|removed|unavailable|not\b)', after, re.I):
                        denied.add(key); continue
                    if unbuilt or re.search(r'\b(?:future|planned|plans|proposed|potential|could|would|may|might|dream|envision|membership|room for|space for|room to add|nearby|near|minutes from|walking distance)\b', before, re.I) or re.match(r'\s+(?:could|may|might|can|will|to be|potential)\b', after, re.I):
                        uncertain.add(key); continue
                    if key == 'size' and (MODEL_RANGE.search(sentence) or re.search(r'\b(?:range|ranging|guest|flex space)\b',sentence,re.I)):
                        continue
                    value = match.group().lower()
                    if key == 'acreage':
                        value = re.sub(r'(\d)[- ]acre\b',r'\1 acres',value)
                        if value == 'quarter-acre': value = 'a quarter-acre lot'
                        else: value += ' of land'
                    if key == 'size':
                        value = re.sub(r'[- ](?:square[- ](?:foot|feet)|sq\.?\s*ft\.?|sf)\.?$', ' square feet', value)
                        if re.search(r'\bmain residence\b',sentence,re.I): value += ' in the main residence'
                    if key == 'garage': value = re.sub(r'[- ]car[- ]', '-car ', value)
                    if key == 'parking': value = value.replace('rv', 'RV')
                    if key == 'doors': value = value.replace('french', 'French')
                    if key == 'pool':
                        if re.search(r'\b(?:community|association|shared|resort.style amenities)\b', sentence, re.I):
                            value = 'community pool'
                        elif re.search(r'\b(?:backyard|private|garden)\b', sentence, re.I):
                            value = 'private pool'
                        # Preserve an unscoped swimming pool without inventing ownership.
                        elif set(str(source.get('PoolFeatures') or '').casefold().split(',')) & {'community','association'}:
                            value = 'community pool'
                        else:
                            value = 'swimming pool'
                    value = re.sub(r'\btesla powerwall\b', 'Tesla Powerwall', value)
                    value = re.sub(r'\badu\b', 'ADU', value)
                    features.append({'key':key,'value':value,'priority':priority,'evidence':sentence,'source':'remarks'})
        if any(f['key']=='pond' for f in features) and any(f['key']=='waterfall' for f in features):
            for f in features:
                if f['key']=='pond': f['value'] += ' and waterfall'; f['priority']=9
            features=[f for f in features if f['key']!='waterfall']
        existing = self.supported_evidence(text, source)
        # Structured flags are useful only when not contradicted by remarks or
        # future-feature language. A positive pool flag cannot override that.
        for f in existing['features']:
            key = 'pool' if 'pool' in f['key'] else f['key']
            if f['source'] == 'remarks' or unbuilt or key in uncertain:
                continue
            if key == 'pool' and re.search(r'\b(?:future pool|room for a pool|adding a pool|pool could)\b', text, re.I):
                continue
            features.append(dict(f, key=key, priority=3))
        blocked = set(existing['conflicting_features'])
        distinct = {}
        for f in sorted(features, key=lambda f:-f['priority']):
            if f['key'] in denied or (f['key'] in blocked and not (f['key']=='pool' and 'community' in f['value'])):
                continue
            if f['key']=='pool' and (('pool' in blocked and 'community' not in f['value']) or ('private' in f['value'] and 'private_pool' in blocked)):
                continue
            distinct.setdefault(f['key'],f)
        return {'fields': facts, 'features':list(distinct.values()), 'conditions':conditions,
                'human_verified':False, 'status':'automatically_source_supported_not_human_verified'}

    def hybrid_summary(self, remarks, listing_data, num_sentences=2):
        data = mapping(listing_data)
        source = mapping(data.get('source_fields')) if 'source_fields' in data else data
        evidence = self.hybrid_evidence(remarks, listing_data)
        conflicts = self.supported_evidence(remarks, listing_data)
        facts = {k:v['value'] for k,v in evidence['fields'].items()}
        text = remarks if isinstance(remarks,str) else ''
        kind = 'property'
        for pattern,label in ((r'\b(?:condo|condominium)\b','condo'),(r'\b(?:townhome|townhouse)\b','townhome'),(r'\bestate\b','estate'),(r'\b(?:home|house|residence)\b','home')):
            if re.search(pattern,text[:300],re.I) and not (label=='estate' and not re.search(r'\b(?:this|the|acre|single-story|Covenant) estate\b',text[:300],re.I)):
                kind=label; break
        if re.search(r'\b(?:currently a homesite|vacant land|vacant lot)\b',text,re.I): kind='homesite'
        descriptor=''
        for pattern,label in ((r'\b(?:single-story|single-level) (?:home|residence|estate)\b','single-story '),(r'\b(?:two-story|2 story) (?:home|house|residence|condominium)\b','two-story '),(r'\bupper-level condo\b','upper-level '),(r'\b(?:ground-floor|first floor) condo\b','ground-floor '),(r'\b(?:\d{4} )?Victorian\b','Victorian ')):
            if re.search(pattern,text,re.I): descriptor=label; break
        kind=descriptor+kind
        lead = 'This '+kind
        if 'city' in facts:
            lead += f" in {facts['city']}"
        counts = [f"{facts[k]:g} {label}{'' if facts[k] == 1 else 's'}" for k,label in (('bedrooms','bedroom'),('bathrooms','bathroom')) if k in facts]
        if counts:
            lead = 'This '+kind+' with '+' and '.join(counts)
            if 'city' in facts: lead += f" in {facts['city']}"
        if 'price' in facts:
            lead += ' is' + f" listed at ${facts['price']:,.2f}".removesuffix('.00')
        if not counts and 'price' not in facts and 'city' in facts:
            lead = f"This property is in {facts['city']}"
        if counts and 'price' not in facts: lead += ' is described in the listing'
        parts = [lead+'.'] if facts else []
        conditions = evidence['conditions']
        if conditions:
            physical=[c for c in conditions if not c.startswith('renderings')]
            condition_text='The property is '+ ' and '.join(physical) if physical else ''
            if any(c.startswith('renderings') for c in conditions):
                condition_text += ('; renderings' if condition_text else 'Renderings') + ' may not reflect the final condition'
            parts.append(condition_text+'.')
        features = evidence['features'][:5]
        if features:
            values = [f['value'] for f in features]
            joined = ', '.join(values[:-1]) + (', and ' if len(values)>2 else ' and ') + values[-1] if len(values)>1 else values[0]
            if len(parts) >= self._limit(num_sentences):
                parts[-1] = parts[-1][:-1] + '; described features include ' + joined + '.'
            else:
                parts.append('Features include ' + joined + '.')
        if not facts and not conditions and not conflicts['conflicting_features'] and not conflicts['conflicting_fields'] and isinstance(remarks,str) and len(self.sentences(remarks))==1 and len(remarks.split())<=8:
            # A short fragment needs no synthetic wrapper.
            return remarks.strip() if not re.search(r'\b(?:no|without|could|future|not)\b',remarks,re.I) else ' '.join(parts)
        if not features and not conditions:
            for sentence in self._select(remarks, facts, self._limit(num_sentences)-len(parts), source=source, covered=set(facts)):
                if not set(self._analyze(sentence)[0]) & set(facts) and len(sentence.split())<=45:
                    parts.append(sentence)
        if self._limit(num_sentences)==3 and len(parts)==2 and len(features)>1 and not conditions:
            values=[f['value'] for f in features]
            parts=parts[:1]+['Features include '+values[0]+'.','Additional features include '+', '.join(values[1:])+'.']
        return ' '.join(parts)
