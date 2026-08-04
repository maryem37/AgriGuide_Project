import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { PageHeader } from "@/components/PageHeader";
import { EquipementPicker } from "@/components/EquipementPicker";
import { Button } from "@/components/ui/button";
import { Loader2, MapPin, Ruler, Save, Sprout, Trash2, User } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  deleteTerrain,
  fetchMe,
  updateEquipements,
  AuthApiError,
  type EquipementType,
} from "@/lib/authApi";
import { areaHectares } from "@/lib/terrain";

export const Route = createFileRoute("/profil")({
  head: () => ({
    meta: [
      { title: "Mon profil - AgriMent" },
      {
        name: "description",
        content: "Modifiez votre matériel agricole et vos terrains déclarés.",
      },
    ],
  }),
  component: Page,
});

function Page() {
  return (
    <AppShell allowRoles={["farmer"]}>
      <ProfileContent />
    </AppShell>
  );
}

function ProfileContent() {
  const { user, token, setUser } = useAuth();

  if (!user || !token) return null;

  return (
    <div className="max-w-3xl">
      <PageHeader
        icon={User}
        title="Mon profil"
        subtitle={`${user.nom} · ${user.email}`}
        className="mb-8"
      />

      <EquipementSection token={token} equipements={user.equipements} onSaved={setUser} />

      <div className="mt-10">
        <h2 className="font-display text-2xl font-semibold mb-2">Mes terrains</h2>
        <p className="text-muted-foreground text-sm mb-5">
          Pour ajouter un terrain, cliquez une parcelle sur la carte dans Agriculture. Vous pouvez
          supprimer vos parcelles ici.
        </p>
        <TerrainsSection
          key={user.terrains.map((t) => t.id).join(",")}
          token={token}
          terrains={user.terrains}
          onSaved={setUser}
        />
      </div>
    </div>
  );
}

function EquipementSection({
  token,
  equipements,
  onSaved,
}: {
  token: string;
  equipements: EquipementType[];
  onSaved: (user: Awaited<ReturnType<typeof updateEquipements>>) => void;
}) {
  const [selected, setSelected] = useState<EquipementType[]>(equipements);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const dirty = useMemo(
    () => JSON.stringify([...selected].sort()) !== JSON.stringify([...equipements].sort()),
    [selected, equipements],
  );

  async function save() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateEquipements(token, selected);
      onSaved(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Une erreur inattendue est survenue.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-2">Mon matériel agricole</h2>
      <p className="text-muted-foreground text-sm mb-5">Cochez le matériel que vous possédez.</p>
      <EquipementPicker selected={selected} onChange={setSelected} />

      {error && (
        <div className="mt-4">
          <AlertBanner tone="danger" title="Impossible d'enregistrer">
            {error}
          </AlertBanner>
        </div>
      )}

      <div className="mt-4 flex items-center gap-3">
        <Button onClick={save} disabled={!dirty || saving} className="rounded-xl">
          {saving ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Enregistrer
        </Button>
        {saved && !dirty && <span className="text-sm text-harvest font-medium">Enregistré ✓</span>}
      </div>
    </div>
  );
}

function TerrainsSection({
  token,
  terrains,
  onSaved,
}: {
  token: string;
  terrains: { id: string; nom: string | null; points: [number, number][]; superficie_ha: number }[];
  onSaved: (user: Awaited<ReturnType<typeof fetchMe>>) => void;
}) {
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function remove(terrainId: string) {
    setError(null);
    setPendingId(terrainId);
    try {
      await deleteTerrain(token, terrainId);
      onSaved(await fetchMe(token));
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Une erreur inattendue est survenue.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div className="space-y-4">
      {error && (
        <AlertBanner tone="danger" title="Impossible de mettre à jour vos terrains">
          {error}
        </AlertBanner>
      )}

      {terrains.length === 0 ? (
        <div className="card-soft p-6 text-center space-y-3">
          <p className="text-sm text-muted-foreground">Aucun terrain enregistré pour le moment.</p>
          <Button asChild className="rounded-xl">
            <Link to="/agriculture">
              <Sprout className="h-4 w-4 mr-2" /> Ajouter depuis Agriculture
            </Link>
          </Button>
        </div>
      ) : (
        terrains.map((t) => (
          <div key={t.id} className="card-soft p-4 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-semibold flex items-center gap-2">
                <MapPin className="h-4 w-4 text-primary shrink-0" /> {t.nom ?? "Terrain"}
              </div>
              <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                <Ruler className="h-3 w-3" />{" "}
                {(t.superficie_ha || areaHectares(t.points)).toLocaleString("fr-FR", {
                  maximumFractionDigits: 2,
                })}{" "}
                ha
              </div>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="shrink-0 text-muted-foreground hover:text-destructive"
              disabled={pendingId === t.id}
              onClick={() => void remove(t.id)}
            >
              {pendingId === t.id ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        ))
      )}

      {terrains.length > 0 && (
        <Button asChild variant="outline" className="rounded-xl w-full h-11">
          <Link to="/agriculture">
            <Sprout className="h-4 w-4 mr-2" /> Ajouter un terrain sur la carte
          </Link>
        </Button>
      )}
    </div>
  );
}
