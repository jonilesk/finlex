"""Topic classification for organizing statutes into skill folders.

Maps ministry branches to top-level skill folders and uses keyword-based
rules to assign sub-topics within each folder.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TopicInfo:
    """Classification result for a statute."""

    skill: str  # top-level folder name
    subtopic: str  # sub-folder within skill (empty = flat in skill root)
    skill_title: str  # Finnish display name for the skill
    skill_description: str  # Finnish description for README


# Ministry ID → skill folder mapping
MINISTRY_TO_SKILL: dict[str, str] = {
    "fi.ministry-of-economic-affairs-and-employment": "tyolainsaadanto",
    "fi.ministry-of-social-affairs-and-health": "sosiaali-ja-terveys",
    "fi.ministry-of-justice": "oikeus",
    "fi.ministry-of-finance": "talous-ja-verotus",
    "fi.ministry-of-transport-and-communications": "liikenne-ja-viestinta",
    "fi.ministry-of-the-environment": "ymparisto-ja-rakentaminen",
    "fi.ministry-of-agriculture-and-forestry": "maatalous-ja-metsa",
    "fi.ministry-of-education-and-culture": "koulutus-ja-kulttuuri",
    "fi.ministry-of-the-interior": "sisaasiat",
    "fi.ministry-for-foreign-affairs": "ulkoasiat",
    "fi.ministry-of-defence": "puolustus",
    "fi.prime-ministers-office": "valtionhallinto",
    "fi.parliament": "valtionhallinto",
    "fi.bank-of-finland": "talous-ja-verotus",
}

# Skill metadata for README generation
SKILL_METADATA: dict[str, tuple[str, str]] = {
    "tyolainsaadanto": (
        "Työlainsäädäntö",
        "Suomen työ- ja elinkeinolainsäädäntö. Sisältää työsuhteita, työoloja, "
        "julkisia hankintoja, energiamarkkinoita ja elinkeinotoimintaa koskevat lait ja asetukset.",
    ),
    "sosiaali-ja-terveys": (
        "Sosiaali- ja terveyslainsäädäntö",
        "Sosiaali- ja terveydenhuoltoa, eläkkeitä, vakuutuksia, lääkkeitä, "
        "säteilyturvallisuutta ja päihdevalvontaa koskevat lait ja asetukset.",
    ),
    "oikeus": (
        "Oikeuslainsäädäntö",
        "Oikeudenkäyntiä, tuomioistuimia, rikoslainsäädäntöä, tietosuojaa, "
        "säätiöitä ja kansainvälistä oikeusapua koskevat lait ja asetukset.",
    ),
    "talous-ja-verotus": (
        "Talous- ja verolainsäädäntö",
        "Verotusta, rahoitusmarkkinoita, kuntahallintoa, tullia ja "
        "julkista taloutta koskevat lait ja asetukset.",
    ),
    "liikenne-ja-viestinta": (
        "Liikenne- ja viestintälainsäädäntö",
        "Tieliikennettä, ajoneuvoja, raideliikennettä, merenkulkua, "
        "viestintää ja kyberturvallisuutta koskevat lait ja asetukset.",
    ),
    "ymparisto-ja-rakentaminen": (
        "Ympäristö- ja rakentamislainsäädäntö",
        "Rakentamista, luonnonsuojelua, ympäristönsuojelua, "
        "asumista ja ilmastopolitiikkaa koskevat lait ja asetukset.",
    ),
    "maatalous-ja-metsa": (
        "Maatalous- ja metsälainsäädäntö",
        "Eläinten hyvinvointia, elintarviketurvallisuutta, maataloustukia, "
        "metsätaloutta ja kalastusta koskevat lait ja asetukset.",
    ),
    "koulutus-ja-kulttuuri": (
        "Koulutus- ja kulttuurilainsäädäntö",
        "Koulutusta, varhaiskasvatusta, kirkkolainsäädäntöä, "
        "kulttuuria, nuorisotoimintaa ja liikuntaa koskevat lait ja asetukset.",
    ),
    "sisaasiat": (
        "Sisäasioiden lainsäädäntö",
        "Poliisia, rajavartiolaitosta, pelastustoimea, maahanmuuttoa, "
        "rahapelejä ja turvallisuutta koskevat lait ja asetukset.",
    ),
    "ulkoasiat": (
        "Ulkoasioiden lainsäädäntö",
        "Kansainvälisiä sopimuksia, vientivalvontaa, kehitysyhteistyötä "
        "ja kansainvälistä oikeusapua koskevat lait ja asetukset.",
    ),
    "puolustus": (
        "Puolustuslainsäädäntö",
        "Puolustusvoimia, sotilaskurinpitoa, asevelvollisuutta, "
        "sotilastiedustelua ja maanpuolustusta koskevat lait ja asetukset.",
    ),
    "valtionhallinto": (
        "Valtionhallinnon lainsäädäntö",
        "Valtioneuvoston, eduskunnan ja valtionhallinnon toimintaa "
        "koskevat lait ja asetukset.",
    ),
    "yleinen": (
        "Yleinen lainsäädäntö",
        "Muut lait ja asetukset, jotka eivät kuulu erityisen "
        "hallinnonalan piiriin.",
    ),
}

# Sub-topic keyword rules: (pattern, subtopic_name)
# Checked in order — first match wins.
_SUBTOPIC_RULES: dict[str, list[tuple[str, str]]] = {
    "tyolainsaadanto": [
        (r"hankinn|kilpailu|tarjous", "hankinnat-ja-kilpailu"),
        (r"energia|sähkö|kaasu|päästö|hiili|tuuli|ydinvoim", "elinkeinot-ja-energia"),
        (r"kaivos|kemikaali|räjähd|pyrotekn|painelaite|hiss", "elinkeinot-ja-energia"),
        (r"työ|palkk|yhteistoiminta|vuosilom|oppisopim|lähett", "tyovoima-ja-tyosuhteet"),
        (r"kotoutumi|maahanmuut", "tyovoima-ja-tyosuhteet"),
        (r"kaupparekister|yritys|osuuskunt|osakeyhtiö", "elinkeinot-ja-energia"),
    ],
    "sosiaali-ja-terveys": [
        (r"eläke|eläkesäätiö|lisäeläke", "elakkeet-ja-vakuutukset"),
        (r"vakuut|tapaturm|liikennevakuut", "elakkeet-ja-vakuutukset"),
        (r"tervey|saira|lääk|tartuntatauti|geeni|kudos|veri|biopankki", "terveydenhuolto"),
        (r"säteil|tupak|alkohol|huumaus|nikotiini", "turvallisuus-ja-valvonta"),
        (r"sosiaali|toimeentulo|lastensuojel|vammais|kehitysvam|omaishoito", "sosiaalipalvelut"),
    ],
    "talous-ja-verotus": [
        (r"vero|verotus|veronkanto|arvonlisä|valmiste|autovero|kiinteistövero", "verotus"),
        (r"sijoitus|rahasto|arvopaperi|arvo-osuus|rahoitus|luotto|pankki|maksulaitos", "rahoitusmarkkinat"),
        (r"rahanpesu|terrorismi", "rahoitusmarkkinat"),
        (r"kunta|hyvinvointialue|maakunta|peruspalvelu", "kuntahallinto"),
        (r"tulli|tullilaki", "julkinen-talous"),
    ],
    "oikeus": [
        (r"oikeudenkäynti|tuomioistuin|hovioikeu|käräjäoikeu|hallinto-oikeu", "oikeudenkäynti"),
        (r"rikos|rangaistu|vankeu|yhdyskuntaseuraamu|syyttäj|kurinpito", "rikos-ja-rangaistus"),
        (r"säätiö|yhdistys|tietosuoj|luottotieto|henkilötieto|kuluttaja", "yksityisoikeus"),
        (r"vanhemmuus|isyys|adoptio|edunvalvon|holhous", "yksityisoikeus"),
        (r"kansainväli|eurooppa|tunnustami", "kansainvalinen-oikeus"),
    ],
    "liikenne-ja-viestinta": [
        (r"tieliikenne|ajoneuvo|ajokortti|ajokort|liikenneturva|yksityistie", "tieliikenne"),
        (r"raide|rata|rautatie|merenkulku|luotsau|alus|satama|ilmailu|lento", "raideliikenne-ja-merenkulku"),
        (r"viestintä|kyber|tietoturva|sähköi|teletoimint|radio|televisio", "viestinta-ja-kyberturvallisuus"),
    ],
    "ymparisto-ja-rakentaminen": [
        (r"rakennus|rakentami|maankäyttö|kaavoitu", "rakentaminen"),
        (r"luonnon|ympäristö|ilmasto|päästö|jäte", "luonnonsuojelu"),
        (r"asunto|asumis|vuokra|asumisoikeu|asuntosäästö", "asuminen"),
    ],
    "maatalous-ja-metsa": [
        (r"eläin|eläintauti|eläinlääk|eläimist", "elaimet-ja-elintarvikkeet"),
        (r"elintarvik|rehu|lannoit|siemen|kasvinsuojelu|torjunta-aine", "elaimet-ja-elintarvikkeet"),
        (r"maatalou|maaseu|maatilat|pelto|EU.*tuk|tukien toimeenpano", "maataloustuet"),
        (r"metsä|kalast|riista|metsästy|porotalou", "metsa-ja-kalastus"),
    ],
    "koulutus-ja-kulttuuri": [
        (r"kirkko|evankelis|seurakunt|hautaus|uskonnonvapau", "kirkko"),
        (r"koulu|opetus|yliopist|ammattikorkea|lukio|perusopetu|oppivelvollis|varhaiskasvatu|opiske", "koulutus"),
        (r"kulttuuri|nuoriso|liikunta|urheilu|kirjasto|museo|elokuva|taide", "kulttuuri-ja-nuoriso"),
    ],
    "ulkoasiat": [
        # Laws > 10KB are "merkittavat", rest are treaty ratifications
    ],
}

# Title-based exclusion patterns for filtering out noise
TITLE_EXCLUSION_PATTERNS: list[str] = [
    r"^lisäys\b.*menoarvioon",
    r"^lisäyksiä\b.*menoarvioon",
    r"^muutoksia\b.*menoarvioon",
    r"virkojen ja toimien perustamisesta$",
    r"virkojen toimien perustamisesta$",
    r"virkojen ja toimien perustamisesta eräisiin",
    r"menosääntöjen perusteiden muuttamisesta$",
    r"^laki aluevaihdosta\b",
    r"peruspalkkaisten virkojen",
]
_COMPILED_EXCLUSIONS = [re.compile(p, re.IGNORECASE) for p in TITLE_EXCLUSION_PATTERNS]

# Title-based fallback classification for statutes without ministry tag
_FALLBACK_RULES: list[tuple[str, str]] = [
    (r"vero|tulli|maksu|rahoitus|pankki|valuutta|budjet", "talous-ja-verotus"),
    (r"työ|eläke|vakuutus|tapaturma|sosiaali|tervey|saira", "sosiaali-ja-terveys"),
    (r"oikeu|rikos|tuomio|vankeu|rangaist|syyttäj", "oikeus"),
    (r"koulu|opetus|yliopist|opiske", "koulutus-ja-kulttuuri"),
    (r"liikenne|ajoneuv|tie|rata|merenkulk|ilmailu|lento", "liikenne-ja-viestinta"),
    (r"maatalou|metsä|kalast|eläin|maaseu|vilj", "maatalous-ja-metsa"),
    (r"ympärist|rakennu|asunto|luonnon", "ymparisto-ja-rakentaminen"),
    (r"poliis|raja|pelast|passi|ulkomaal", "sisaasiat"),
    (r"puolust|sotila|asevel|maanpuol", "puolustus"),
    (r"kansainväli|sopimuk|voimaansaat", "ulkoasiat"),
]
_COMPILED_FALLBACKS = [(re.compile(p, re.IGNORECASE), skill) for p, skill in _FALLBACK_RULES]


def is_excluded(title: str) -> bool:
    """Check if a statute should be excluded based on title patterns."""
    for pattern in _COMPILED_EXCLUSIONS:
        if pattern.search(title):
            return True
    return False


def classify_skill(ministry_id: str, title: str) -> str:
    """Determine the top-level skill folder for a statute.

    Uses ministry_id first, then falls back to title keywords.
    Returns skill folder name.
    """
    # Strip leading # if present
    ministry_id = ministry_id.lstrip("#")

    if ministry_id and ministry_id in MINISTRY_TO_SKILL:
        return MINISTRY_TO_SKILL[ministry_id]

    # Fallback: classify by title keywords
    title_lower = title.lower()
    for pattern, skill in _COMPILED_FALLBACKS:
        if pattern.search(title_lower):
            return skill

    return "yleinen"


def classify_subtopic(skill: str, title: str, xml_size: int = 0) -> str:
    """Determine the sub-topic within a skill folder.

    Args:
        skill: Top-level skill folder name.
        title: Statute title.
        xml_size: File size in bytes (used for ulkoasiat threshold).

    Returns:
        Sub-topic folder name, or empty string for flat placement.
    """
    # Special case: ulkoasiat uses size threshold
    if skill == "ulkoasiat":
        return "merkittavat" if xml_size > 10000 else "sopimukset"

    rules = _SUBTOPIC_RULES.get(skill, [])
    title_lower = title.lower()
    for pattern, subtopic in rules:
        if re.search(pattern, title_lower):
            return subtopic

    return ""


def classify(
    ministry_id: str, title: str, xml_size: int = 0
) -> TopicInfo:
    """Fully classify a statute into skill + subtopic.

    Args:
        ministry_id: Administrative branch ID (e.g., "fi.ministry-of-justice").
        title: Statute title.
        xml_size: File size in bytes.

    Returns:
        TopicInfo with skill folder, subtopic, and display metadata.
    """
    skill = classify_skill(ministry_id, title)
    subtopic = classify_subtopic(skill, title, xml_size)
    meta = SKILL_METADATA.get(skill, ("Muu lainsäädäntö", "Muut lait ja asetukset."))

    return TopicInfo(
        skill=skill,
        subtopic=subtopic,
        skill_title=meta[0],
        skill_description=meta[1],
    )


def should_include(type_statute: str, title: str, xml_size: int) -> bool:
    """Determine if a statute should be included in the output.

    Args:
        type_statute: Statute type (act, decree, decision, etc.).
        title: Statute title.
        xml_size: File size in bytes.

    Returns:
        True if the statute should be included.
    """
    # Always include acts above size threshold
    if type_statute == "act":
        if xml_size < 3000:
            return False
        if is_excluded(title):
            return False
        return True

    # Include substantial decrees
    if type_statute == "decree":
        return xml_size >= 20000

    # Skip everything else
    return False
