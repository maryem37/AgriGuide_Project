"""
Validator agent.

Applies deterministic, code-level (non-LLM) validation and normalization
on top of what the extraction prompt already enforces. This is a second,
independent line of defense: even if the LLM slips and mislabels a plant
part as a crop, or leaves an obvious duplicate, this module catches it in
plain Python before anything is written to the knowledge base.
"""
from __future__ import annotations

import re

from config.logging_config import get_logger
from config.settings import settings
from models import Crop, ExtractionResult, ExtractionStatus, Waste
from services.tracing_service import log_metadata, traced
from text_utils import singularize

logger = get_logger(__name__)

# Plant parts / residues that must never be treated as a crop name.
# Mirrors the CROP vs WASTE VALIDATION section of the extraction prompt.
NON_CROP_TERMS = {
    "leaves", "leaf", "stem", "stalk", "branches", "branch", "roots", "root",
    "husk", "shell", "cob", "bagasse", "straw", "peel", "rind", "pomace",
    "pseudostem", "rejected fruits", "fruit residues", "bran", "hull",
    "chaff", "stover", "pulp", "pod", "seed coat", "hulls",
}

# Head nouns identifying a *derived product* -- something obtained by
# transforming a waste -- rather than the waste residue itself. These
# belong in a waste's final_products/transformations, not as standalone
# waste entries (e.g. "Rice Husk Ash" is what you get after burning rice
# husk; the waste is the husk).
#
# Matched against the LAST word of the name only, deliberately: a name
# like "Palm oil mill effluent" is a genuine waste whose head noun is
# "effluent", and must not be rejected just because "oil" appears
# somewhere inside it.
DERIVED_PRODUCT_HEAD_TERMS = {
    "ash", "biochar", "charcoal", "char", "oil", "extract",
    "pellet", "pellets", "briquette", "briquettes", "compost",
    "silica", "cellulose", "ethanol", "bioethanol", "biogas", "biodiesel",
    "fertilizer", "fertiliser", "adsorbent", "concentrate", "isolate",
    "syrup", "vinegar", "enzyme", "protein", "starch", "pectin",
}

# Head nouns naming a FORM the material was milled/cut/processed into,
# rather than which part of the plant it came from -- as opposed to
# DERIVED_PRODUCT_HEAD_TERMS above, which name a genuinely different
# transformation OUTPUT and are rejected unconditionally. A form factor is
# not itself a different substance: "Bran powder" is still bran, just
# milled fine, so it's rejected only when NO other word in the name
# identifies a real plant part -- a bare "Powders" gives no way to tell
# which residue it actually is.
FORM_FACTOR_HEAD_TERMS = {
    "powder", "flour", "dust", "fine", "particle",
    "trimming", "cutting", "offcut", "clipping", "discard", "reject",
}

# Crop-level synonym groups (crop names and multi-word waste names that
# don't decompose into a generic plant part). Plant parts are NOT listed
# here -- they're handled by the crop-prefixing mechanism below, so that
# "Leaves" under Banana becomes "Banana Leaf" rather than a bare "Leaves"
# that can never merge with "Banana leaves" from another source.
SYNONYM_CANONICAL_MAP = {
    "corn": "Maize",
    "maize": "Maize",
    "groundnut": "Groundnut",
    "peanut": "Groundnut",
    "cassava": "Cassava",
    "manioc": "Cassava",
    "corn stover": "Maize Stover",
    "maize stover": "Maize Stover",
}

# Generic, non-specific waste labels that carry no information. The
# extraction prompt already forbids these ("Biomass", "Crop residue",
# "Agricultural waste"), but the LLM still emits them occasionally --
# especially catch-all buckets like "Other by-products" from sources that
# summarise a mass balance. Compared against the singularized core name.
GENERIC_WASTE_TERMS = {
    "waste", "wastes", "residue", "other", "other residue", "other waste",
    "by-product", "byproduct", "other by-product", "other byproduct",
    "biomass", "crop residue", "agricultural waste", "agricultural residue",
    "agro-industrial waste", "agroindustrial waste", "organic waste",
    "solid waste", "plant waste", "biowaste", "green waste", "food waste",
    "processing waste", "processing residue", "plant residue",
}

# Generic plant-part terms, in SINGULAR canonical form. A waste whose core
# term (after stripping any crop prefix and singularizing) matches one of
# these is rewritten as "<Crop> <Part>", so that "Pseudostem",
# "Banana pseudostem" and "Banana pseudostems" all collapse to a single
# "Banana Pseudostem" entity instead of three separate wastes.
GENERIC_PLANT_PART_TERMS = {
    "husk", "bran", "straw", "peel", "shell", "cob", "bagasse", "pomace",
    "hull", "chaff", "pulp", "stalk", "stem", "leaf", "root", "pseudostem",
    "inflorescence", "rhizome", "sucker", "frond", "trunk", "crown", "seed",
    "stover", "fruit stalk", "floral stalk", "rachis", "pod", "seed coat",
    "bunch", "fibre", "fiber", "core", "top", "vine", "haulm", "shoot",
    "head", "meal", "kernel", "cake", "marc", "press cake",
    "branch", "twig", "pruning", "bark", "wood", "fruit", "germ", "grain",
}

# Plant-part synonyms resolved to a single canonical part term, applied
# after singularization. E.g. banana "skin" and "peel" are the same waste,
# and in agronomy "hull" and "husk" name the same seed covering (rice hull
# = rice husk, sunflower hull = sunflower husk).
#
# Deliberately NOT mapped: "shell" stays distinct from "husk". For coconut
# and tree nuts the husk (fibrous outer layer) and shell (hard inner layer)
# are genuinely different residues with different valorization routes.
PART_SYNONYM_MAP = {
    "skin": "peel",
    "rind": "peel",
    "hull": "husk",
    "seed coat": "husk",
    "rachis": "fruit stalk",
    "floral stalk": "fruit stalk",
    "fibre": "fiber",
    "haulm": "stalk",
    "oilcake": "meal",
    "oil cake": "meal",
    "presscake": "meal",
    "press cake": "meal",
    "cake": "meal",
    "marc": "pomace",
}

# Vocabulary checked against every word but the head noun, to decide
# whether a FORM_FACTOR_HEAD_TERMS name ("X Powder") still identifies a
# real plant part (kept) or names nothing at all (rejected). Built from the
# plant-part sets already used elsewhere so the two stay in sync.
_KNOWN_PLANT_PART_WORDS = NON_CROP_TERMS | GENERIC_PLANT_PART_TERMS | set(PART_SYNONYM_MAP.keys())

# Known crop names, used to catch cross-crop contamination: a waste name
# that references a *different* crop than the one currently being
# processed (e.g. a generic review paper on "agricultural waste" bleeding
# "Olive waste" into a Tomato research pass).
KNOWN_CROP_NAMES = {
    "tomato", "banana", "rice", "wheat", "maize", "corn", "potato", "cassava",
    "coffee", "cocoa", "sugarcane", "olive", "date palm", "coconut", "palm oil",
    "oil palm", "groundnut", "peanut", "soybean", "barley", "sorghum", "millet",
    "cotton", "grape", "citrus", "orange", "apple", "mango", "pineapple",
    "avocado", "onion", "garlic", "carrot", "cabbage", "lettuce", "pepper",
    "chili", "eggplant", "cucumber", "pea", "bean", "lentil", "chickpea",
    "sunflower", "rapeseed", "canola", "sesame", "flax", "hemp", "jute",
    "tea", "tobacco", "sugar beet", "yam", "sweet potato", "taro", "papaya",
    "watermelon", "melon", "strawberry", "raspberry", "blueberry", "fig",
    "pomegranate", "walnut", "almond", "cashew", "pistachio", "hazelnut",
    "pecan", "olive tree", "sisal", "rubber tree", "quinoa", "oat", "rye",
}

# Terms describing a *state* of the harvested/processed product itself,
# not an agricultural waste/byproduct/plant-part. A source discussing
# post-harvest losses may list these alongside real wastes (husk, straw,
# etc.), but they describe what happened to the crop's main product, not
# a distinct residue stream with its own valorization pathway.
PRODUCT_STATE_TERMS = {
    "processed", "cooked", "expired", "rotten", "spoiled", "damaged",
    "low-quality", "low quality", "dead", "half fill", "half-fill",
    "non-harvested", "unharvested", "raw", "fresh", "stale", "moldy",
    "contaminated", "overripe", "underripe", "unripe", "surplus",
}


class ValidationError(Exception):
    """Raised when an ExtractionResult is fundamentally invalid and must be discarded."""


class ValidatorAgent:
    """Validates and normalizes ExtractionResult objects before they reach the knowledge base."""

    @traced(name="validate_and_normalize")
    def validate_and_normalize(self, result: ExtractionResult) -> ExtractionResult:
        """
        Returns a cleaned copy of `result`. Never raises for recoverable
        issues (bad entries are dropped, not fatal); raises ValidationError
        only when the crop itself is invalid and nothing can be salvaged.
        """
        if result.status != ExtractionStatus.SUCCESS or not result.crop:
            return result

        # Singularized so that a crop named in the plural by one source
        # ("Tomatoes") converges with the singular used by another
        # ("Tomato") -- otherwise the wastes split across two crop
        # entries and the UI never finds either one complete.
        crop_name = singularize(result.crop.strip())
        if crop_name.lower() in NON_CROP_TERMS:
            logger.warning(
                "Validator rejected extraction: '%s' is a plant part/residue, not a valid crop.", crop_name
            )
            raise ValidationError(f"'{crop_name}' is a plant part/residue, not a valid crop.")

        valid_wastes: list[Waste] = []
        for waste in result.wastes:
            cleaned = self._validate_waste(waste, crop_name)
            if cleaned is not None:
                valid_wastes.append(cleaned)

        valid_wastes = self._deduplicate(valid_wastes)

        log_metadata(
            validator_crop=crop_name,
            wastes_in=len(result.wastes),
            wastes_out=len(valid_wastes),
            wastes_rejected=len(result.wastes) - len(valid_wastes),
        )

        cleaned_result = result.model_copy(deep=True)
        cleaned_result.wastes = valid_wastes
        cleaned_result.crop = _title_case_preserve(crop_name)
        return cleaned_result

    def _validate_waste(self, waste: Waste, crop_name: str) -> Waste | None:
        name_lower = waste.name.strip().lower()
        crop_lower = crop_name.strip().lower()

        if not name_lower:
            return None

        # A waste name must not itself be a recognized crop name (basic heuristic:
        # if it equals the crop name being processed, or is empty, reject it).
        if name_lower == crop_lower:
            logger.debug("Rejected waste '%s': identical to crop name '%s'.", waste.name, crop_name)
            return None

        # Cross-crop contamination check: reject a waste that names a *different*
        # known crop than the one currently being processed. Synonyms of the
        # current crop (e.g. "corn" for "maize") are excluded so legitimate
        # wastes aren't rejected.
        current_crop_synonyms = {crop_lower} | {
            syn for syn, canonical in SYNONYM_CANONICAL_MAP.items() if canonical.lower() == crop_lower
        }
        for other_crop in KNOWN_CROP_NAMES:
            if other_crop in current_crop_synonyms:
                continue
            if re.search(rf"\b{re.escape(other_crop)}\b", name_lower):
                logger.warning(
                    "Rejected waste '%s' under crop '%s': name references a different crop ('%s').",
                    waste.name, crop_name, other_crop,
                )
                return None



        # Product-state check: reject entries describing a state of the
        # harvested product (processed, cooked, expired, rotten, low-quality,
        # non-harvested, etc.) rather than a distinct waste/byproduct stream.
        # These commonly appear in post-harvest-loss sources alongside real
        # wastes but aren't valorizable residues in the same sense. Uses
        # word-boundary matching to avoid false positives like "raw" matching
        # inside "straw".
        for state_term in PRODUCT_STATE_TERMS:
            pattern = r"\b" + re.escape(state_term) + r"\b"
            if re.search(pattern, name_lower):
                logger.warning(
                    "Rejected waste '%s' under crop '%s': describes a product state ('%s'), not a distinct waste stream.",
                    waste.name, crop_name, state_term,
                )
                return None

        # Generic-label check: reject catch-all names that identify no
        # specific residue ("Other by-products", "Biomass", "Crop residue").
        # The extraction prompt forbids these, but the LLM still emits them
        # when a source presents an aggregated mass balance.
        generic_core = name_lower
        if crop_lower and generic_core.startswith(crop_lower + " "):
            generic_core = generic_core[len(crop_lower) + 1 :].strip()
        if singularize(generic_core) in GENERIC_WASTE_TERMS:
            logger.warning(
                "Rejected waste '%s' under crop '%s': generic catch-all label, not a specific residue.",
                waste.name,
                crop_name,
            )
            return None

        # Derived-product check: reject entries that name a transformation
        # OUTPUT rather than the residue itself (e.g. "Rice Husk Ash" is
        # produced by burning rice husk -- the waste is the husk). Such
        # entries belong in a waste's final_products, not as standalone
        # wastes. Only the head noun (last word) is checked, so genuine
        # wastes like "Palm oil mill effluent" are not caught. Singularized
        # before matching so a plural like "Extracts" is still caught.
        words = name_lower.split()
        head_noun = singularize(words[-1]) if words else ""
        if head_noun in DERIVED_PRODUCT_HEAD_TERMS:
            logger.warning(
                "Rejected waste '%s' under crop '%s': '%s' names a derived product, not a waste residue.",
                waste.name,
                crop_name,
                head_noun,
            )
            return None

        # Form-factor check: a name like "Powders" describes HOW the
        # material was milled, not which part of the plant it is, and
        # carries no information on its own. Unlike the derived-product
        # check above, this is only rejected when no OTHER word in the name
        # identifies a real plant part -- "Bran powder" is still bran, just
        # milled fine, and survives.
        if head_noun in FORM_FACTOR_HEAD_TERMS:
            other_words = {singularize(w) for w in words[:-1]}
            if not (other_words & _KNOWN_PLANT_PART_WORDS):
                logger.warning(
                    "Rejected waste '%s' under crop '%s': '%s' names how the material was processed, "
                    "not which plant part it is.",
                    waste.name,
                    crop_name,
                    head_noun,
                )
                return None

        # Low-content check: a waste entry whose description is empty, or is
        # just the waste's own name repeated back with no real detail, and
        # that has no composition/transformation/application data, adds
        # nothing useful. This is a common symptom of the LLM extracting a
        # bare name from an enumerated list without real supporting detail
        # (e.g. description="husk" for a waste named "Husk").
        description_clean = waste.description.strip().lower()
        description_is_trivial = (
            not description_clean
            or description_clean == name_lower
            or len(description_clean) < 15
        )
        has_rich_content = bool(
            waste.composition
            or waste.transformations
            or waste.final_products
            or waste.industrial_applications
            or waste.agricultural_applications
            or waste.environmental_applications
            or waste.advantages
            or waste.limitations
        )
        if description_is_trivial and not has_rich_content:
            logger.warning(
                "Rejected waste '%s' under crop '%s': trivial/empty description and no supporting data (name-only entry).",
                waste.name, crop_name,
            )
            return None

        # Confidence floor check (mirrors prompt-level rule, enforced again in code)
        if waste.confidence < settings.min_confidence_document and waste.evidence_source.value == "DOCUMENT":
            logger.debug(
                "Rejected waste '%s': confidence %.2f below floor %.2f for DOCUMENT evidence.",
                waste.name,
                waste.confidence,
                settings.min_confidence_document,
            )
            return None

        cleaned = waste.model_copy(deep=True)
        cleaned.canonical_name = self._canonicalize(waste.canonical_name or waste.name, crop_name)
        return cleaned

    def _canonicalize(self, name: str, crop_name: str = "") -> str:
        """
        Reduce a waste name to a stable canonical form so that variants
        extracted from different sources merge into one entity.

        Pipeline: strip any crop prefix -> singularize -> resolve plant-part
        synonyms (skin->peel, rachis->fruit stalk) -> re-attach the crop
        prefix if the core is a generic plant part. This makes
        "Pseudostem", "Banana pseudostem" and "Banana pseudostems" all
        resolve to "Banana Pseudostem".
        """
        raw = name.strip()
        if not raw:
            return raw

        key = raw.lower()
        if key in SYNONYM_CANONICAL_MAP:
            return SYNONYM_CANONICAL_MAP[key]

        crop_lower = crop_name.strip().lower()
        core = key
        if crop_lower and core.startswith(crop_lower + " "):
            core = core[len(crop_lower) + 1 :].strip()

        core = singularize(core)
        core = PART_SYNONYM_MAP.get(core, core)

        if core in GENERIC_PLANT_PART_TERMS and crop_name:
            return f"{crop_name.strip().title()} {core.title()}"

        # Multi-word core whose head noun is itself a generic plant part
        # (e.g. "seed hull" -> "hull" -> "husk"). Checked only AFTER the
        # full-core lookup above, so genuinely distinct multi-word parts
        # like "fruit stalk" aren't flattened to "stalk".
        if " " in core and crop_name:
            head = PART_SYNONYM_MAP.get(core.rsplit(" ", 1)[-1], core.rsplit(" ", 1)[-1])
            if head in GENERIC_PLANT_PART_TERMS:
                return f"{crop_name.strip().title()} {head.title()}"

        return raw

    def _deduplicate(self, wastes: list[Waste]) -> list[Waste]:
        merged: dict[str, Waste] = {}
        for waste in wastes:
            key = waste.canonical_name.lower()
            if key in merged:
                merged[key] = merged[key].merge_with(waste)
            else:
                merged[key] = waste
        return list(merged.values())

    def validate_crop_for_knowledge_base(self, crop: Crop) -> bool:
        """
        Final gate before a Crop is upserted into the knowledge base.
        Returns False if the crop itself is actually a plant part/residue.
        """
        name_lower = (crop.canonical_name or crop.name).strip().lower()
        if name_lower in NON_CROP_TERMS:
            logger.warning("Refusing to store '%s' as a crop: it is a plant part/residue.", crop.name)
            return False
        return True


def _title_case_preserve(name: str) -> str:
    """Title-case a crop name while preserving already-capitalized acronyms."""
    words = name.split()
    return " ".join(w if w.isupper() and len(w) <= 4 else w.capitalize() for w in words)
