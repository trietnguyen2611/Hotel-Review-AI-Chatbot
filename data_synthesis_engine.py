"""
data_synthesis_engine.py
========================
Non-Formulaic Conversational Response Synthesis Engine for Hotel Review QA.

Design Principles:
1. STRICT ZERO-FORMULA RULE:
   Never recite robotic metadata strings like:
   "Guests at {h_name} ({star}, {tot_revs} total reviews) share predominantly positive feedback regarding {asp} across {count} related reviews."
2. 12 DISTINCT SYNTACTIC ARCHETYPES:
   Rotates across 12 diverse conversational sentence structures, speaking naturally
   as a hospitable travel concierge answering a traveler's direct inquiry.
3. SEAMLESS QUOTE BLENDING:
   Quotes from verified customer reviews are woven into sentences with varied attribution verbs
   ("one guest remarked", "reviews describe it as", "several travelers highlighted").
4. SENTIMENT-ADAPTIVE TONE:
   - Positive (score >= 3.8): Warm, confident, highlighting strengths and delights.
   - Mixed/Neutral (3.0 - 3.7): Balanced, acknowledging strengths while noting nuances.
   - Critical (< 3.0): Candid, objective advice pointing out reported shortcomings.
"""

import random
import re
from typing import List, Optional, Dict, Any

ASPECT_LEXICONS = {
    'Service': {
        'positive_terms': ['attentive staff', 'warm hospitality', 'prompt check-in', 'courteous assistance', 'helpful front desk'],
        'critical_terms': ['slow response times', 'occasional check-in delays', 'inconsistent service'],
        'focus_nouns': ['customer service', 'front desk hospitality', 'staff responsiveness', 'overall service']
    },
    'Facility': {
        'positive_terms': ['clean and modern rooms', 'comfortable bedding', 'spacious layout', 'well-maintained facilities'],
        'critical_terms': ['dated room furnishings', 'sound insulation issues', 'minor maintenance needs'],
        'focus_nouns': ['room comfort and cleanliness', 'room facilities', 'living space and amenities']
    },
    'Food': {
        'positive_terms': ['delicious breakfast buffet', 'fresh culinary choices', 'rich morning spread', 'quality dining'],
        'critical_terms': ['limited breakfast variety', 'pricey dining options', 'crowded buffet hours'],
        'focus_nouns': ['dining and breakfast experience', 'culinary offerings', 'breakfast buffet']
    },
    'Amenity': {
        'positive_terms': ['well-kept swimming pool', 'relaxing spa amenities', 'fully equipped fitness center', 'pleasant pool area'],
        'critical_terms': ['small pool size', 'limited gym equipment', 'crowded amenity hours'],
        'focus_nouns': ['leisure amenities and pool', 'recreational facilities', 'amenities']
    },
    'Location': {
        'positive_terms': ['convenient central location', 'easy access to attractions', 'scenic surroundings', 'walkable neighborhood'],
        'critical_terms': ['street traffic noise', 'distance from city center', 'busy surrounding streets'],
        'focus_nouns': ['location and accessibility', 'neighborhood convenience', 'geographic setting']
    },
    'Experience': {
        'positive_terms': ['relaxing getaway', 'memorable and pleasant stay', 'enjoyable atmosphere', 'high overall satisfaction'],
        'critical_terms': ['mixed impressions', 'room for quality improvements', 'expectations not fully met'],
        'focus_nouns': ['overall stay experience', 'general atmosphere', 'guest satisfaction']
    },
    'Loyalty': {
        'positive_terms': ['highly recommended', 'frequently revisited by travelers', 'strong guest loyalty'],
        'critical_terms': ['hesitant to return', 'mixed recommendations'],
        'focus_nouns': ['guest recommendation', 'return value']
    },
    'Branding': {
        'positive_terms': ['reliable hospitality standards', 'living up to its brand reputation', 'exceptional luxury prestige'],
        'critical_terms': ['inconsistent with brand expectations', 'varying standards'],
        'focus_nouns': ['brand experience', 'hospitality reputation']
    }
}

ATTRIBUTION_VERBS_POS = [
    "one traveler noted",
    "recent reviews highlight that",
    "a guest specifically praised",
    "visitors frequently describe",
    "multiple reviews appreciate that",
    "guests often remark",
    "several travelers commended"
]

ATTRIBUTION_VERBS_CRIT = [
    "one guest observed that",
    "recent feedback flagged that",
    "a traveler noted concerns regarding",
    "some reviews pointed out that",
    "an occasional comment mentioned that"
]

def clean_quote(quote: str, max_chars: int = 140) -> str:
    if not quote:
        return ""
    q = quote.strip().replace('"', '').replace("'", "").replace('\n', ' ')
    q = re.sub(r'\s+', ' ', q).strip()
    if len(q) > max_chars:
        q = q[:max_chars].rsplit(' ', 1)[0] + '...'
    return q

def synthesize_concierge_answer(
    h_name: str,
    aspect: str,
    consensus: str = 'positive',
    quotes: Optional[List[str]] = None,
    star: str = 'Standard',
    score: float = 4.0,
    rng: Optional[random.Random] = None,
    is_followup: bool = False
) -> str:
    """
    Synthesize an organic, non-formulaic conversational response.
    Never uses rigid robotic templates or statistical counts.
    """
    if rng is None:
        rng = random.Random()

    asp_key = aspect.capitalize() if aspect else 'Experience'
    lexicon = ASPECT_LEXICONS.get(asp_key, ASPECT_LEXICONS['Experience'])
    asp_noun = lexicon['focus_nouns'][rng.randint(0, len(lexicon['focus_nouns']) - 1)]

    # Clean quote
    raw_quote = ""
    if quotes:
        for q in quotes:
            cleaned = clean_quote(q)
            if cleaned:
                raw_quote = cleaned
                break

    is_positive = (consensus.lower() == 'positive') or (score >= 3.8 and consensus.lower() != 'critical')
    attr_verb = rng.choice(ATTRIBUTION_VERBS_POS if is_positive else ATTRIBUTION_VERBS_CRIT)
    quote_clause = f' ({attr_verb}: "{raw_quote}")' if raw_quote else ""

    if is_positive:
        pos_term = rng.choice(lexicon['positive_terms'])
        
        # 10 Diverse Positive Syntactic Archetypes
        templates = [
            # 1. Direct Evaluative
            f"Overall, the {asp_noun} at {h_name} is considered a major highlight by recent travelers{quote_clause}. You can expect {pos_term} and a dependable standard throughout your stay.",
            # 2. Traveler Impression Lead
            f"Guests frequently praise the {asp_noun} when recounting their stay at {h_name}{quote_clause}. The general impression is that the property delivers {pos_term}.",
            # 3. Actionable Travel Advice
            f"If {asp_noun} is top of mind for your trip, {h_name} proves to be a solid choice. Visitors consistently report positive experiences{quote_clause}, pointing to {pos_term}.",
            # 4. Reviewer Narrative & Quote Lead
            f"According to recent guest feedback for {h_name}, the {asp_noun} makes a very favorable impression{quote_clause}. It stands out as one of the key reasons travelers enjoy staying here.",
            # 5. Aspect-First Consensus
            f"On the {asp_noun} front, feedback for {h_name} sits firmly on the positive side{quote_clause}. Many guests appreciate the {pos_term} provided during their visit.",
            # 6. Conversational Concierge Lead
            f"You will find that {h_name} performs remarkably well regarding {asp_noun}{quote_clause}. Guests often note {pos_term}, making it comfortable and convenient.",
            # 7. Atmosphere & Quality Focus
            f"The standard of {asp_noun} at {h_name} has received glowing feedback from guests{quote_clause}. It is widely viewed as a well-managed aspect that adds value to the stay.",
            # 8. Welcoming Hospitality Focus
            f"Customer impressions of {asp_noun} at {h_name} are largely positive{quote_clause}. Recent visitors mention {pos_term}, reflecting attentive management.",
            # 9. Practical Traveler Perspective
            f"From a traveler's perspective, {h_name} offers great quality when it comes to {asp_noun}{quote_clause}. The {pos_term} is a recurring positive theme in verified reviews.",
            # 10. Natural Concise Synthesis
            f"Guests staying at {h_name} have shared very positive comments regarding {asp_noun}{quote_clause}. The consistent mention of {pos_term} makes it an appealing option."
        ]
        
        if is_followup:
            followup_templates = [
                f"Regarding the {asp_noun} there, feedback continues to be very positive{quote_clause}. Guests highlight {pos_term} as a definite plus.",
                f"As for the {asp_noun}, you can expect great quality as well{quote_clause}. Visitors frequently commend the {pos_term} at this property.",
                f"The {asp_noun} there is also well-received by guests{quote_clause}. It tends to be noted as comfortable and well-maintained.",
                f"Looking at customer feedback for its {asp_noun}, travelers share enthusiastic remarks{quote_clause}, praising the {pos_term}."
            ]
            return rng.choice(followup_templates)
        
        return rng.choice(templates)
        
    else:
        crit_term = rng.choice(lexicon['critical_terms'])
        # Diverse Critical / Mixed Syntactic Archetypes
        crit_templates = [
            f"Guest opinions regarding {asp_noun} at {h_name} show some variability{quote_clause}. While some travelers had a satisfactory experience, others noted {crit_term}.",
            f"Feedback on the {asp_noun} at {h_name} is somewhat mixed{quote_clause}. While many appreciate the overall stay, a few reviewers pointed to {crit_term} as an area for improvement.",
            f"Customer reviews suggest occasional inconsistencies with {asp_noun} at {h_name}{quote_clause}. Travelers who prioritize this aspect may want to keep reported {crit_term} in mind.",
            f"Regarding {asp_noun}, experiences at {h_name} vary among guests{quote_clause}. While basic expectations are met, several comments mentioned {crit_term}."
        ]
        if is_followup:
            return f"Regarding the {asp_noun} there, feedback is somewhat mixed{quote_clause}. Some guests had an agreeable experience while others mentioned {crit_term}."
        return rng.choice(crit_templates)

def synthesize_hotel_overview(
    h_name: str,
    star: str,
    score: float,
    loc: str,
    addr: str,
    quotes: Optional[List[str]] = None,
    rng: Optional[random.Random] = None
) -> str:
    """
    Synthesize an organic, informative overview of a hotel property without formulaic phrases.
    """
    if rng is None:
        rng = random.Random()

    quote_str = ""
    if quotes:
        for q in quotes:
            cleaned = clean_quote(q)
            if cleaned:
                quote_str = f' Guests frequently note: "{cleaned}".'
                break

    patterns = [
        f"{h_name} is a {star} accommodation in {loc}, situated at {addr}. Guests generally rate their stay favorably at {score:.1f} out of 5.0 stars, appreciating its accessible location and welcoming ambiance.{quote_str}",
        f"Located at {addr} in {loc}, {h_name} offers {star} accommodations with an average guest rating of {score:.1f}/5.0 stars. It is well-regarded for providing reliable hospitality and comfortable facilities.{quote_str}",
        f"For travelers visiting {loc}, {h_name} ({star}) provides quality lodging at {addr}. Customer feedback averages {score:.1f}/5.0 stars, reflecting consistent comfort and attentive service standards.{quote_str}"
    ]
    return rng.choice(patterns)
