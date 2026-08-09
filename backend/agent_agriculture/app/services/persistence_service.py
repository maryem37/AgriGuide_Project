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
from uuid import UUID

from app.db import get_cursor
from app.models.schemas import CropRecommendationOut


def get_terrain(terrain_id: str) -> Optional[dict]:
    """Reads a terrain (any user) by id — this agent has no notion of
    ownership/JWT, that's enforced by whichever caller (frontend, via the
    Auth-issued terrain list) supplied this terrain_id in the first place."""
    try:
        terrain_uuid = UUID(terrain_id)
    except (TypeError, ValueError):
        # Avoid leaking a psycopg2 InvalidTextRepresentation as a 500 when a
        # caller supplies a placeholder or otherwise malformed terrain id.
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, nom, superficie_ha, region,
                   ST_AsGeoJSON(geometry) AS geojson,
                   ST_Y(ST_Centroid(geometry)) AS centroid_lat,
                   ST_X(ST_Centroid(geometry)) AS centroid_lon
            FROM terrains WHERE id = %s
            """,
            (str(terrain_uuid),),
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
                    (land_profile_id, rang, culture, score_compatibilite, cycle_jours,
                     besoins_pesticides, besoins_engrais, besoins_irrigation, feature_importance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    land_profile_id,
                    rec.rang,
                    rec.culture,
                    rec.score_compatibilite,
                    rec.cycle_jours,
                    json.dumps(rec.besoins_pesticides, ensure_ascii=False),
                    json.dumps(rec.besoins_engrais, ensure_ascii=False),
                    json.dumps(rec.besoins_irrigation, ensure_ascii=False),
                    json.dumps(rec.feature_importance, ensure_ascii=False),
                ),
            )


def get_user_chat_profile(user_id: str) -> Optional[dict]:
    """Compact account snapshot for the chat widget — no password, no GeoJSON.

    Includes terrains owned by the user and, when present, the latest land
    profile's top crop recommendations (already persisted from /analyze).
    """
    try:
        user_uuid = UUID(user_id)
    except (TypeError, ValueError):
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, email, nom, telephone, role
            FROM users WHERE id = %s
            """,
            (str(user_uuid),),
        )
        user = cur.fetchone()
        if not user:
            return None

        cur.execute(
            """
            SELECT type_equipement
            FROM farmer_equipements
            WHERE user_id = %s
            ORDER BY type_equipement
            """,
            (str(user_uuid),),
        )
        equipements = [row["type_equipement"] for row in cur.fetchall()]

        cur.execute(
            """
            SELECT id, nom, superficie_ha, region
            FROM terrains
            WHERE user_id = %s
            ORDER BY created_at
            """,
            (str(user_uuid),),
        )
        terrain_rows = cur.fetchall()

        terrains: list[dict] = []
        for t in terrain_rows:
            terrain_id = str(t["id"])
            cur.execute(
                """
                SELECT id, date_generation
                FROM land_profiles
                WHERE terrain_id = %s
                ORDER BY date_generation DESC NULLS LAST, id DESC
                LIMIT 1
                """,
                (terrain_id,),
            )
            profile = cur.fetchone()
            top_crops: list[dict] = []
            last_analysis_at = None
            if profile:
                last_analysis_at = (
                    profile["date_generation"].isoformat()
                    if profile.get("date_generation") is not None
                    else None
                )
                cur.execute(
                    """
                    SELECT rang, culture, score_compatibilite
                    FROM crop_recommendations
                    WHERE land_profile_id = %s
                    ORDER BY rang
                    LIMIT 5
                    """,
                    (str(profile["id"]),),
                )
                top_crops = [
                    {
                        "rang": row["rang"],
                        "culture": row["culture"],
                        "score_compatibilite": float(row["score_compatibilite"])
                        if row["score_compatibilite"] is not None
                        else None,
                    }
                    for row in cur.fetchall()
                ]

            terrains.append(
                {
                    "id": terrain_id,
                    "nom": t["nom"],
                    "superficie_ha": float(t["superficie_ha"]) if t["superficie_ha"] is not None else None,
                    "region": t["region"],
                    "derniere_analyse_at": last_analysis_at,
                    "cultures_recommandees": top_crops,
                }
            )

    return {
        "id": str(user["id"]),
        "email": user["email"],
        "nom": user["nom"],
        "telephone": user["telephone"],
        "role": user["role"],
        "equipements": equipements,
        "terrains": terrains,
    }
