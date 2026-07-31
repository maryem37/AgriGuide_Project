import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { EquipementPicker } from "@/components/EquipementPicker";
import { TerrainListEditor, type DraftTerrain } from "@/components/TerrainListEditor";
import { Button } from "@/components/ui/button";
import { Loader2, Save, User } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  addTerrain,
  deleteTerrain,
  fetchMe,
  updateEquipements,
  AuthApiError,
  type EquipementType,
} from "@/lib/authApi";

export const Route = createFileRoute("/profil")({
  head: () => ({
    meta: [
      { title: "Mon profil — AgriMent" },
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
      <div className="flex items-center gap-3 mb-8">
        <div className="h-11 w-11 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
          <User className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold leading-none">
            Mon profil
          </h1>
          <p className="text-muted-foreground mt-1">
            {user.nom} · {user.email}
          </p>
        </div>
      </div>

      <EquipementSection token={token} equipements={user.equipements} onSaved={setUser} />

      <div className="mt-10">
        <h2 className="font-display text-2xl font-semibold mb-2">Mes terrains</h2>
        <p className="text-muted-foreground text-sm mb-5">
          Ajoutez, renommez ou supprimez vos parcelles. Ces informations alimentent vos conseillers.
        </p>
        <TerrainsSection
          key={user.terrains.length}
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
      <p className="text-muted-foreground text-sm mb-5">
        Cochez le matériel que vous possédez (les images seront ajoutées prochainement).
      </p>
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
  terrains: { id: string; nom: string | null; points: [number, number][] }[];
  onSaved: (user: Awaited<ReturnType<typeof fetchMe>>) => void;
}) {
  const initial: DraftTerrain[] = useMemo(
    () => terrains.map((t) => ({ id: t.id, nom: t.nom ?? "Terrain", points: t.points })),
    [terrains],
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const existingIds = useMemo(() => new Set(initial.map((t) => t.id)), [initial]);

  async function handleChange(next: DraftTerrain[]) {
    setError(null);
    const removed = initial.filter((t) => !next.some((n) => n.id === t.id));
    const added = next.filter((t) => !existingIds.has(t.id));

    setPending(true);
    try {
      for (const terrain of removed) {
        await deleteTerrain(token, terrain.id);
      }
      for (const terrain of added) {
        await addTerrain(token, { nom: terrain.nom, points: terrain.points });
      }
      onSaved(await fetchMe(token));
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Une erreur inattendue est survenue.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      {error && (
        <div className="mb-4">
          <AlertBanner tone="danger" title="Impossible de mettre à jour vos terrains">
            {error}
          </AlertBanner>
        </div>
      )}
      <fieldset disabled={pending} className="space-y-4">
        <TerrainListEditor terrains={initial} onChange={(next) => void handleChange(next)} />
      </fieldset>
      {pending && (
        <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Mise à jour...
        </div>
      )}
    </div>
  );
}
