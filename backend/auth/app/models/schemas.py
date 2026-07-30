"""
Modèles Pydantic du service Auth.

`role`, `farmer_equipements` et `terrains` sont alignés champ à champ sur
`database/schema.sql` (tables `users`, `farmer_equipements`, `terrains`).
"""

from __future__ import annotations
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class RoleEnum(str, Enum):
    farmer = "farmer"
    acheteur = "acheteur"


class EquipementType(str, Enum):
    tracteur = "tracteur"
    cultivateur = "cultivateur"
    fraise_rotative = "fraise_rotative"
    planteuse = "planteuse"
    moissonneuse_batteuse = "moissonneuse_batteuse"
    remorque_agricole = "remorque_agricole"
    pulverisateur = "pulverisateur"
    tunnel_plastique = "tunnel_plastique"


# ---------------------------------------------------------------------------
# Terrains
# ---------------------------------------------------------------------------

class TerrainInput(BaseModel):
    """Un terrain déclaré par le farmer : nom de la zone + contour tracé sur la carte."""
    nom: str = Field(min_length=1, max_length=150)
    points: list[tuple[float, float]] = Field(min_length=3)  # [(lat, lng), ...]
    superficie_ha: Optional[float] = Field(default=None, gt=0)
    region: Optional[str] = None


class TerrainUpdate(BaseModel):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=150)
    points: Optional[list[tuple[float, float]]] = Field(default=None, min_length=3)
    superficie_ha: Optional[float] = Field(default=None, gt=0)
    region: Optional[str] = None


class TerrainOut(BaseModel):
    id: str
    nom: Optional[str]
    superficie_ha: float
    region: Optional[str]
    points: list[tuple[float, float]]


# ---------------------------------------------------------------------------
# Comptes
# ---------------------------------------------------------------------------

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    nom: str = Field(min_length=1, max_length=150)
    telephone: Optional[str] = None
    role: RoleEnum
    equipements: list[EquipementType] = []
    terrains: list[TerrainInput] = []

    @model_validator(mode="after")
    def _valider_champs_farmer(self) -> "SignUpRequest":
        if self.role == RoleEnum.farmer and len(self.terrains) == 0:
            raise ValueError(
                "Un farmer doit déclarer au moins un terrain (tracé sur la carte) à l'inscription."
            )
        if self.role == RoleEnum.acheteur:
            # Un acheteur n'a ni matériel ni terrain — on ignore silencieusement
            # plutôt que de rejeter, au cas où le frontend enverrait des valeurs par défaut.
            self.equipements = []
            self.terrains = []
        return self


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    nom: str
    telephone: Optional[str]
    role: RoleEnum
    equipements: list[EquipementType] = []
    terrains: list[TerrainOut] = []


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class EquipementsUpdateRequest(BaseModel):
    equipements: list[EquipementType]
