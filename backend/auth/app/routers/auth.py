from fastapi import APIRouter, Depends, Header, HTTPException

from app.models.schemas import (
    AuthResponse,
    EquipementsUpdateRequest,
    SignInRequest,
    SignUpRequest,
    TerrainOut,
    TerrainInput,
    TerrainUpdate,
    UserOut,
)
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentification requise.")
    token = authorization.split(" ", 1)[1]
    try:
        return decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Session invalide, reconnectez-vous.")


def _require_farmer(user: dict) -> None:
    if user["role"] != "farmer":
        raise HTTPException(status_code=403, detail="Réservé aux comptes farmer.")


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(request: SignUpRequest) -> AuthResponse:
    if user_service.get_user_by_email(request.email):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email.")

    user_id = user_service.create_user(
        email=request.email,
        password_hash=hash_password(request.password),
        nom=request.nom,
        telephone=request.telephone,
        role=request.role.value,
    )

    if request.role.value == "farmer":
        user_service.set_farmer_equipements(user_id, list(request.equipements))
        for terrain in request.terrains:
            user_service.create_terrain(
                user_id, terrain.nom, terrain.points, terrain.superficie_ha, terrain.region
            )

    user_out = user_service.build_user_out(user_id)
    token = create_access_token(user_id)
    return AuthResponse(access_token=token, user=UserOut(**user_out))


@router.post("/signin", response_model=AuthResponse)
def signin(request: SignInRequest) -> AuthResponse:
    row = user_service.get_user_by_email(request.email)
    if not row or not verify_password(request.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    user_out = user_service.build_user_out(str(row["id"]))
    token = create_access_token(str(row["id"]))
    return AuthResponse(access_token=token, user=UserOut(**user_out))


@router.get("/me", response_model=UserOut)
def me(user_id: str = Depends(get_current_user_id)) -> UserOut:
    user_out = user_service.build_user_out(user_id)
    if not user_out:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    return UserOut(**user_out)


@router.put("/me/equipements", response_model=UserOut)
def update_equipements(
    payload: EquipementsUpdateRequest, user_id: str = Depends(get_current_user_id)
) -> UserOut:
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    _require_farmer(user)

    user_service.set_farmer_equipements(user_id, list(payload.equipements))
    return UserOut(**user_service.build_user_out(user_id))


@router.post("/me/terrains", response_model=TerrainOut, status_code=201)
def add_terrain(payload: TerrainInput, user_id: str = Depends(get_current_user_id)) -> TerrainOut:
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    _require_farmer(user)

    terrain = user_service.create_terrain(
        user_id, payload.nom, payload.points, payload.superficie_ha, payload.region
    )
    return TerrainOut(**terrain)


@router.put("/me/terrains/{terrain_id}", response_model=TerrainOut)
def edit_terrain(
    terrain_id: str, payload: TerrainUpdate, user_id: str = Depends(get_current_user_id)
) -> TerrainOut:
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    _require_farmer(user)

    terrain = user_service.update_terrain(
        terrain_id, user_id, payload.nom, payload.points, payload.superficie_ha, payload.region
    )
    if not terrain:
        raise HTTPException(status_code=404, detail="Terrain introuvable.")
    return TerrainOut(**terrain)


@router.delete("/me/terrains/{terrain_id}", status_code=204)
def remove_terrain(terrain_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    _require_farmer(user)

    if not user_service.delete_terrain(terrain_id, user_id):
        raise HTTPException(status_code=404, detail="Terrain introuvable.")
