"""
Accès aux données (users, farmer_equipements, terrains) — requêtes SQL
explicites sur `database/schema.sql`.
"""

import json
from typing import Optional

from app.db import get_cursor


def _points_to_wkt(points: list[tuple[float, float]]) -> str:
    """Convertit une liste de points (lat, lng) en WKT POLYGON (PostGIS attend lng puis lat,
    et un anneau fermé — premier point répété en dernier)."""
    coords = [f"{lng} {lat}" for lat, lng in points]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return f"POLYGON(({', '.join(coords)}))"


def _geojson_to_points(geojson_str: str) -> list[tuple[float, float]]:
    """Reconstruit la liste de points (lat, lng) à partir du GeoJSON PostGIS (ST_AsGeoJSON),
    en retirant le point de fermeture du polygone."""
    geojson = json.loads(geojson_str)
    ring = geojson["coordinates"][0]
    points = [(lat, lng) for lng, lat in ring]
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    return points


def polygon_area_ha(points: list[tuple[float, float]]) -> float:
    """Calcule la superficie approximative (ha) d'un polygone GPS — formule de l'excès sphérique,
    identique à `frontend/src/lib/terrain.ts::polygonAreaM2`, utilisée en secours si le frontend
    n'envoie pas déjà `superficie_ha`."""
    import math

    if len(points) < 3:
        return 0.0
    r = 6378137.0  # rayon terrestre en mètres
    total = 0.0
    n = len(points)
    for i in range(n):
        lat1, lon1 = points[i]
        lat2, lon2 = points[(i + 1) % n]
        total += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    area_m2 = abs(total * r * r / 2)
    return round(area_m2 / 10000, 4)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user_by_email(email: str) -> Optional[dict]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, nom, telephone, role FROM users WHERE email = %s",
            (email,),
        )
        return cur.fetchone()


def get_user_by_id(user_id: str) -> Optional[dict]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, nom, telephone, role FROM users WHERE id = %s",
            (user_id,),
        )
        return cur.fetchone()


def create_user(email: str, password_hash: str, nom: str, telephone: Optional[str], role: str) -> str:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, nom, telephone, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (email, password_hash, nom, telephone, role),
        )
        return str(cur.fetchone()["id"])


# ---------------------------------------------------------------------------
# Matériel agricole (farmer uniquement)
# ---------------------------------------------------------------------------

def get_farmer_equipements(user_id: str) -> list[str]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT type_equipement FROM farmer_equipements WHERE user_id = %s ORDER BY type_equipement",
            (user_id,),
        )
        return [row["type_equipement"] for row in cur.fetchall()]


def set_farmer_equipements(user_id: str, equipements: list[str]) -> None:
    """Remplace intégralement la liste de matériel déclaré par le farmer."""
    with get_cursor() as cur:
        cur.execute("DELETE FROM farmer_equipements WHERE user_id = %s", (user_id,))
        for type_equipement in equipements:
            cur.execute(
                "INSERT INTO farmer_equipements (user_id, type_equipement) VALUES (%s, %s)",
                (user_id, type_equipement),
            )


# ---------------------------------------------------------------------------
# Terrains (farmer uniquement)
# ---------------------------------------------------------------------------

def create_terrain(
    user_id: str,
    nom: str,
    points: list[tuple[float, float]],
    superficie_ha: Optional[float],
    region: Optional[str],
) -> dict:
    wkt = _points_to_wkt(points)
    superficie = superficie_ha if superficie_ha and superficie_ha > 0 else polygon_area_ha(points)
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO terrains (user_id, nom, geometry, superficie_ha, region)
            VALUES (%s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326), %s, %s)
            RETURNING id, nom, superficie_ha, region, ST_AsGeoJSON(geometry) AS geojson
            """,
            (user_id, nom, wkt, superficie, region),
        )
        row = cur.fetchone()
        return _terrain_row_to_out(row)


def get_user_terrains(user_id: str) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, nom, superficie_ha, region, ST_AsGeoJSON(geometry) AS geojson
            FROM terrains WHERE user_id = %s ORDER BY created_at
            """,
            (user_id,),
        )
        return [_terrain_row_to_out(row) for row in cur.fetchall()]


def update_terrain(
    terrain_id: str,
    user_id: str,
    nom: Optional[str],
    points: Optional[list[tuple[float, float]]],
    superficie_ha: Optional[float],
    region: Optional[str],
) -> Optional[dict]:
    fields: list[str] = []
    values: list[object] = []

    if nom is not None:
        fields.append("nom = %s")
        values.append(nom)
    if points is not None:
        fields.append("geometry = ST_SetSRID(ST_GeomFromText(%s), 4326)")
        values.append(_points_to_wkt(points))
        if not superficie_ha:
            superficie_ha = polygon_area_ha(points)
    if superficie_ha is not None:
        fields.append("superficie_ha = %s")
        values.append(superficie_ha)
    if region is not None:
        fields.append("region = %s")
        values.append(region)

    if not fields:
        return get_terrain(terrain_id, user_id)

    values.extend([terrain_id, user_id])
    with get_cursor() as cur:
        cur.execute(
            f"""
            UPDATE terrains SET {", ".join(fields)}
            WHERE id = %s AND user_id = %s
            RETURNING id, nom, superficie_ha, region, ST_AsGeoJSON(geometry) AS geojson
            """,
            values,
        )
        row = cur.fetchone()
        return _terrain_row_to_out(row) if row else None


def get_terrain(terrain_id: str, user_id: str) -> Optional[dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, nom, superficie_ha, region, ST_AsGeoJSON(geometry) AS geojson
            FROM terrains WHERE id = %s AND user_id = %s
            """,
            (terrain_id, user_id),
        )
        row = cur.fetchone()
        return _terrain_row_to_out(row) if row else None


def delete_terrain(terrain_id: str, user_id: str) -> bool:
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM terrains WHERE id = %s AND user_id = %s RETURNING id",
            (terrain_id, user_id),
        )
        return cur.fetchone() is not None


def _terrain_row_to_out(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "nom": row["nom"],
        "superficie_ha": float(row["superficie_ha"]),
        "region": row["region"],
        "points": _geojson_to_points(row["geojson"]),
    }


# ---------------------------------------------------------------------------
# Assemblage complet d'un utilisateur (pour les réponses API)
# ---------------------------------------------------------------------------

def build_user_out(user_id: str) -> Optional[dict]:
    user = get_user_by_id(user_id)
    if not user:
        return None

    equipements: list[str] = []
    terrains: list[dict] = []
    if user["role"] == "farmer":
        equipements = get_farmer_equipements(user_id)
        terrains = get_user_terrains(user_id)

    return {
        "id": str(user["id"]),
        "email": user["email"],
        "nom": user["nom"],
        "telephone": user["telephone"],
        "role": user["role"],
        "equipements": equipements,
        "terrains": terrains,
    }
