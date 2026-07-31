"""
New (not part of the original standalone prototype): persists analysis
results against `database/schema.sql`'s `terrains` / `land_profiles` /
`crop_recommendations` tables, using the same explicit-SQL, no-ORM
style as `backend/auth/app/services/user_service.py`.

`terrains` rows are owned by the Auth service (created at signup or via
`POST /auth/me/terrains` from a hand-drawn polygon) — this service only
reads a terrain's geometry/id and writes the analysis output that
references it by `terrain_id`.
"""

import json
from typing import Optional

from app.db import get_cursor
from app.models.schemas import CropRecommendationOut


def get_terrain(terrain_id: str) -> Optional[dict]:
    """Reads a terrain (any user) by id — this agent has no notion of
    ownership/JWT, that's enforced by whichever caller (frontend, via the
    Auth-issued terrain list) supplied this terrain_id in the first place."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, nom, superficie_ha, region,
                   ST_AsGeoJSON(geometry) AS geojson,
                   ST_Y(ST_Centroid(geometry)) AS centroid_lat,
                   ST_X(ST_Centroid(geometry)) AS centroid_lon
            FROM terrains WHERE id = %s
            """,
            (terrain_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "nom": row["nom"],
            "superficie_ha": float(row["superficie_ha"]),
            "region": row["region"],
            "geometry": json.loads(row["geojson"]),
            "centroid_lat": row["centroid_lat"],
            "centroid_lon": row["centroid_lon"],
        }


def save_land_profile(
    terrain_id: str,
    sol_data: dict,
    satellite_data: dict,
    rpg_historique: Optional[dict],
    cultures_voisines: Optional[dict],
    climat_data: dict,
    elevation_m: Optional[float] = None,
) -> str:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO land_profiles
                (terrain_id, sol_data, satellite_data, rpg_historique, cultures_voisines, climat_data, elevation_m)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                terrain_id,
                json.dumps(sol_data, ensure_ascii=False),
                json.dumps(satellite_data, ensure_ascii=False),
                json.dumps(rpg_historique, ensure_ascii=False) if rpg_historique is not None else None,
                json.dumps(cultures_voisines, ensure_ascii=False) if cultures_voisines is not None else None,
                json.dumps(climat_data, ensure_ascii=False),
                elevation_m,
            ),
        )
        return str(cur.fetchone()["id"])


def save_crop_recommendations(land_profile_id: str, recommendations: list[CropRecommendationOut]) -> None:
    with get_cursor() as cur:
        for rec in recommendations:
            cur.execute(
                """
                INSERT INTO crop_recommendations
                    (land_profile_id, rang, culture, score_compatibilite,
                     besoins_pesticides, besoins_engrais, besoins_irrigation, feature_importance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    land_profile_id,
                    rec.rang,
                    rec.culture,
                    rec.score_compatibilite,
                    json.dumps(rec.besoins_pesticides, ensure_ascii=False),
                    json.dumps(rec.besoins_engrais, ensure_ascii=False),
                    json.dumps(rec.besoins_irrigation, ensure_ascii=False),
                    json.dumps(rec.feature_importance, ensure_ascii=False),
                ),
            )
