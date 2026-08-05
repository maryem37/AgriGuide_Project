"""
Read-only projection of the waste knowledge base for the AgriGuide platform.

Does not trigger live research or load the vector store — only
canonical_knowledge.json via StorageService — so the agriculture / business
UX stays fast and key-free.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from api.crop_mapping import KB_CROP_LABEL_FR, culture_to_kb_name
from api.i18n_fr import label_fr
from api.schemas import (
    ApplicationOut,
    CropWasteProfile,
    MarketplaceSuggestionsResponse,
    TransformationOut,
    WasteOut,
)
from models import Crop, KnowledgeBase, Waste
from services.storage_service import get_storage_service

# Cap wastes shown in UI so the farmer isn't overwhelmed
_MAX_WASTES_PER_CROP = 5
_MAX_TRANSFORMATIONS = 3
_MAX_APPLICATIONS = 4


@lru_cache(maxsize=1)
def _load_kb() -> KnowledgeBase:
    return get_storage_service().load()


def reload_kb() -> KnowledgeBase:
    _load_kb.cache_clear()
    return _load_kb()


def _find_crop(kb: KnowledgeBase, kb_name: str) -> Optional[Crop]:
    crop = kb.find_crop(kb_name)
    if crop:
        return crop
    # Soft match on canonical / name
    norm = kb_name.strip().lower()
    for c in kb.crops:
        if c.canonical_name.lower() == norm or c.name.lower() == norm:
            return c
        if any(a.lower() == norm for a in c.aliases):
            return c
    return None


def _composition_summary(waste: Waste, limit: int = 3) -> list[str]:
    out: list[str] = []
    for c in waste.composition[:limit]:
        unit = f" {c.unit}" if c.unit else ""
        out.append(f"{label_fr(c.component)} : {c.value}{unit}".strip())
    return out


def _applications(waste: Waste) -> list[ApplicationOut]:
    raw = (
        list(waste.industrial_applications)
        + list(waste.agricultural_applications)
        + list(waste.environmental_applications)
    )
    # Prefer higher confidence
    raw.sort(key=lambda a: a.confidence, reverse=True)
    apps: list[ApplicationOut] = []
    seen: set[str] = set()
    for a in raw:
        key = a.name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        apps.append(
            ApplicationOut(
                name=a.name,
                name_label=label_fr(a.name),
                category=a.category,
                description=a.description,
                environmental_benefit=a.environmental_benefit,
            )
        )
        if len(apps) >= _MAX_APPLICATIONS:
            break
    return apps


def _marketplace_utility(waste: Waste, apps: list[ApplicationOut], products: list[str]) -> str:
    bits: list[str] = []
    for t in waste.transformations[:2]:
        bits.append(
            f"{label_fr(t.process)} → {label_fr(t.output_product)}"
        )
    for p in products[:3]:
        label = label_fr(p)
        if label and label not in bits:
            bits.append(label)
    for a in apps[:3]:
        if a.name_label and a.name_label not in bits:
            bits.append(a.name_label)
    if not bits:
        return "Sous-produit agricole valorisable (compostage, méthanisation, paillage ou usage industriel)."
    return "Peut être valorisé en : " + " · ".join(bits) + "."


def _marketplace_description(crop_fr: str, waste: Waste, utility: str) -> str:
    base = waste.description.strip() or f"Résidu de culture issu de {crop_fr}."
    return (
        f"{base} Après récolte de {crop_fr.lower()}, ce sous-produit peut être déposé "
        f"sur la marketplace AgriMent. {utility}"
    )


def waste_to_out(waste: Waste, crop_fr: str) -> WasteOut:
    name = waste.canonical_name or waste.name
    name_label = label_fr(name)
    products = list(waste.final_products)[:5]
    product_labels = [label_fr(p) for p in products]
    transforms = [
        TransformationOut(
            process=t.process,
            process_label=label_fr(t.process),
            output_product=t.output_product,
            output_label=label_fr(t.output_product),
            description=t.description,
        )
        for t in waste.transformations[:_MAX_TRANSFORMATIONS]
    ]
    apps = _applications(waste)
    utility = _marketplace_utility(waste, apps, products)
    title = f"{name_label} ({crop_fr})"
    return WasteOut(
        id=waste.id,
        name=name,
        name_label=name_label,
        category=waste.category or "",
        plant_part=waste.plant_part or "",
        description=waste.description or "",
        composition_summary=_composition_summary(waste),
        transformations=transforms,
        final_products=products,
        final_products_labels=product_labels,
        applications=apps,
        advantages=list(waste.advantages)[:4],
        confidence=float(waste.confidence or 0.0),
        marketplace_title=title,
        marketplace_utility=utility,
        marketplace_description=_marketplace_description(crop_fr, waste, utility),
    )


def _rank_wastes(wastes: list[Waste]) -> list[Waste]:
    def score(w: Waste) -> tuple:
        n_t = len(w.transformations)
        n_p = len(w.final_products)
        n_a = (
            len(w.industrial_applications)
            + len(w.agricultural_applications)
            + len(w.environmental_applications)
        )
        return (n_t + n_p + n_a, w.confidence, len(w.composition))

    return sorted(wastes, key=score, reverse=True)


def build_crop_profile(culture: str) -> CropWasteProfile:
    kb_name = culture_to_kb_name(culture)
    crop_fr_fallback = culture.replace("_", " ").strip().capitalize()

    if not kb_name:
        return CropWasteProfile(
            culture=culture,
            kb_crop_name=None,
            crop_label_fr=crop_fr_fallback,
            found=False,
            message="Culture non reconnue pour la base déchets.",
        )

    crop_fr = KB_CROP_LABEL_FR.get(kb_name, kb_name)
    kb = _load_kb()
    crop = _find_crop(kb, kb_name)
    if not crop or not crop.wastes:
        return CropWasteProfile(
            culture=culture,
            kb_crop_name=kb_name,
            crop_label_fr=crop_fr,
            found=False,
            message=f"Aucun déchet documenté pour {crop_fr} dans la base locale.",
        )

    ranked = _rank_wastes(crop.wastes)
    wastes_out: list[WasteOut] = []
    seen_labels: set[str] = set()
    for w in ranked:
        out = waste_to_out(w, crop_fr)
        key = out.name_label.strip().lower()
        if key in seen_labels:
            continue
        seen_labels.add(key)
        wastes_out.append(out)
        if len(wastes_out) >= _MAX_WASTES_PER_CROP:
            break

    return CropWasteProfile(
        culture=culture,
        kb_crop_name=crop.canonical_name or kb_name,
        crop_label_fr=crop_fr,
        found=True,
        scientific_name=crop.scientific_name or "",
        wastes=wastes_out,
        message="",
    )


def profiles_for_cultures(cultures: list[str]) -> list[CropWasteProfile]:
    # Preserve order, dedupe
    seen: set[str] = set()
    ordered: list[str] = []
    for c in cultures:
        key = c.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(c.strip())
    return [build_crop_profile(c) for c in ordered]


def marketplace_suggestions(culture: str, limit: int = 4) -> MarketplaceSuggestionsResponse:
    profile = build_crop_profile(culture)
    if not profile.found:
        return MarketplaceSuggestionsResponse(
            culture=culture,
            crop_label_fr=profile.crop_label_fr,
            found=False,
            harvest_hint="",
            suggestions=[],
            message=profile.message or "Aucune suggestion marketplace.",
        )

    # Prefer wastes that have a clear valorization story
    suggestions = [
        w
        for w in profile.wastes
        if w.transformations or w.final_products or w.applications
    ][:limit]
    if not suggestions:
        suggestions = profile.wastes[:limit]

    hint = (
        f"Après la récolte de {profile.crop_label_fr.lower()}, ces sous-produits "
        f"peuvent être proposés sur la marketplace (don ou vente)."
    )
    return MarketplaceSuggestionsResponse(
        culture=culture,
        crop_label_fr=profile.crop_label_fr,
        found=True,
        harvest_hint=hint,
        suggestions=suggestions,
        message="",
    )
