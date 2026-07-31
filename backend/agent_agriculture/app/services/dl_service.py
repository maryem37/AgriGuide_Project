"""
Phase B — DL crop-cover classifier service (optional).

Wraps the fine-tuned BreizhCrops TempCNN checkpoint (see
`scripts/finetune_dl_service.py`) into the same parcel-geometry-in,
structured-result-out shape as the other services (soil_service.py,
weather_service.py, satellite_service.py).

Same "descriptive, not scored" principle as NDVI: this reports what the
DL model currently sees growing on a parcel. It is NOT fed into
ml_service.py's crop-suitability scoring, and is NOT part of the RAG /
synthesis grounding chain — it's a standalone observation, same
treatment as mean_ndvi.

Architecture: constructs TempCNN directly from breizhcrops' own model
class with the fixed hyperparameters the pretrained checkpoints were
trained with (input_dim=13, sequencelength=45), then loads YOUR
fine-tuned local checkpoint file — this deliberately does NOT call
breizhcrops.models.pretrained(), which would re-download the original
weights from S3 on every cold start. That network dependency (and the
S3 domain) has no place in a running FastAPI service.

Ported as-is from the standalone `agri-advisor-parcelle` prototype.
Without a checkpoint at `DL_CHECKPOINT_PATH`, this degrades gracefully
(returns `source="unavailable"`) rather than crashing the pipeline.
"""
import numpy as np
import torch
from breizhcrops.models.TempCNN import TempCNN

from app.config import settings
from app.models.schemas import DLCropObservation
from app.services import satellite_service

# BreizhCrops' 9 native classes, English -> French for the French-language report.
# Order doesn't matter here (looked up by name, not index) — the model's own
# checkpoint carries the index -> classname mapping.
_CLASSNAME_FR = {
    "barley": "orge",
    "wheat": "blé",
    "rapeseed": "colza",
    "corn": "maïs",
    "sunflower": "tournesol",
    "orchards": "vergers",
    "nuts": "fruits à coque",
    "permanent meadows": "prairie permanente",
    "temporary meadows": "prairie temporaire",
}

_INPUT_DIM = 13  # fixed by the pretrained architecture — do not change without retraining

_model_cache = {"model": None, "classnames": None, "load_error": None, "attempted": False}


def _load_model():
    """Lazy-load once per process. Cheap to call repeatedly after the first success."""
    if _model_cache["attempted"]:
        return
    _model_cache["attempted"] = True

    import os
    if not os.path.exists(settings.dl_checkpoint_path):
        _model_cache["load_error"] = (
            f"No checkpoint found at {settings.dl_checkpoint_path}. Run "
            f"scripts/finetune_dl_service.py and place the resulting .pth file there "
            f"(or set DL_CHECKPOINT_PATH in .env)."
        )
        return

    try:
        checkpoint = torch.load(settings.dl_checkpoint_path, map_location=torch.device("cpu"))
        classnames = checkpoint["classnames"]
        model = TempCNN(
            input_dim=_INPUT_DIM,
            num_classes=len(classnames),
            sequencelength=settings.dl_sequence_length,
        )
        model.load_state_dict(checkpoint["model_state"])
        model.eval()
        _model_cache["model"] = model
        _model_cache["classnames"] = classnames
    except Exception as e:  # noqa: BLE001 — genuinely want to catch anything here and degrade gracefully, same pattern as satellite_service's credential/auth failures
        _model_cache["load_error"] = f"Failed to load DL checkpoint: {e}"


def _resample_to_fixed_length(bands: list[list[float]], target_length: int) -> np.ndarray:
    """
    Deterministic resample to a fixed number of timesteps — upsamples (repeats
    nearest available timestep) or downsamples (drops timesteps) as needed.

    Deliberately deterministic, unlike BreizhCrops' own training-time
    get_default_transform(), which randomly subsamples. Random subsampling is
    fine for training (data augmentation) but wrong for inference: the same
    parcel queried twice should not get a different prediction because of
    random chance.
    """
    x = np.array(bands, dtype=np.float32)  # [T, 13]
    t = x.shape[0]
    if t == target_length:
        return x
    idxs = np.linspace(0, t - 1, target_length)
    idxs = np.round(idxs).astype(int)
    return x[idxs]


async def predict_crop(geometry: dict, days_back: int = 120, interval_days: int = 5) -> DLCropObservation:
    """
    Returns a DLCropObservation:
      - source: "dl-tempcnn-breizhcrops" | "unavailable"
      - predicted_class_fr / predicted_class_en: str | None
      - confidence: float | None (softmax probability of the predicted class, 0-1)
      - observation_timesteps: int (real cloud-free acquisitions found, before resampling — low
        values here mean a thinner basis for the prediction, same caveat as satellite_service's
        valid_pixel_count for NDVI)
      - warning: str | None
    """
    _load_model()
    if _model_cache["model"] is None:
        return DLCropObservation(source="unavailable", warning=_model_cache["load_error"])

    series = await satellite_service.get_band_timeseries(geometry, days_back=days_back, interval_days=interval_days)
    if series["warning"] or not series["bands"]:
        return DLCropObservation(
            source="unavailable",
            warning=series["warning"] or "No usable satellite time series for this parcel.",
        )

    real_timesteps = len(series["bands"])
    x = _resample_to_fixed_length(series["bands"], settings.dl_sequence_length)
    tensor = torch.from_numpy(x).unsqueeze(0)  # [1, T, 13]

    def _infer():
        model = _model_cache["model"]
        with torch.no_grad():
            # TempCNN's own final layer is nn.LogSoftmax (see breizhcrops/models/TempCNN.py) —
            # output here is already log-probabilities, NOT raw logits. exp() recovers real
            # probabilities; applying softmax() again on top would be double-normalizing and
            # would silently produce wrong confidence values.
            log_probs = model(tensor)
            probs = torch.exp(log_probs)[0]
        pred_idx = int(torch.argmax(probs).item())
        return pred_idx, float(probs[pred_idx].item())

    import asyncio
    pred_idx, confidence = await asyncio.to_thread(_infer)

    # Defense in depth: even with the upstream NaN-rejection fix in
    # satellite_service.py's get_band_timeseries(), a NaN slipping through
    # here (a new data-quality issue, a different edge case) must never be
    # returned as a confident-looking prediction — that's exactly the kind
    # of silently-wrong output this project's grounding discipline exists
    # to prevent. A real live response already demonstrated this failure
    # mode once (Sentinel Hub returning the string "NaN" for a bin).
    import math
    if math.isnan(confidence):
        return DLCropObservation(
            source="unavailable",
            warning="Model produced a NaN confidence — input data for this parcel was likely corrupted "
                    "(e.g. an invalid value in the satellite time series). Prediction rejected rather "
                    "than shown.",
        )

    classname_en = _model_cache["classnames"][pred_idx]
    classname_fr = _CLASSNAME_FR.get(classname_en, classname_en)

    warning = None
    if real_timesteps < 5:
        warning = (
            f"Only {real_timesteps} cloud-free satellite acquisitions found in the last "
            f"{days_back} days — prediction is based on sparse data and may be unreliable."
        )

    return DLCropObservation(
        source="dl-tempcnn-breizhcrops",
        predicted_class_fr=classname_fr,
        predicted_class_en=classname_en,
        confidence=round(confidence, 4),
        observation_timesteps=real_timesteps,
        warning=warning,
    )


def crops_roughly_match(declared: str | None, predicted_fr: str | None) -> bool | None:
    """
    Compares the RPG-declared crop (a taxonomy.py display name, e.g. "Blé
    tendre") against the DL model's predicted class (e.g. "blé"). Crude
    but deliberately so: a strict match would false-positive on every
    "Blé tendre" vs "blé" pairing. Returns None (not a mismatch) when
    either side is missing — an absent declaration or an unavailable
    prediction isn't evidence of disagreement.
    """
    if not declared or not predicted_fr:
        return None
    import unicodedata

    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return s.lower().strip()

    d, p = _norm(declared), _norm(predicted_fr)
    d_first_word = d.split()[0] if d else ""
    p_first_word = p.split()[0] if p else ""
    return d_first_word in p or p_first_word in d
