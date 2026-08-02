import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { FileText, ExternalLink, Send, ScrollText, Sparkles, ArrowUpRight, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { askRegulationAgent, fetchSubsidies, RegulationApiError, type Subsidy } from "@/lib/regulationApi";
import { MarkdownLite } from "@/lib/markdownLite";

export const Route = createFileRoute("/regulation")({
  head: () => ({
    meta: [
      { title: "Conseiller Réglementaire — AgriMent" },
      { name: "description", content: "Chat, aides, PAC et certifications : toutes les règles agricoles expliquées et un dossier généré pour vous." },
      { property: "og:title", content: "Conseiller Réglementaire — AgriMent" },
      { property: "og:description", content: "Toutes les règles agricoles, expliquées." },
    ],
  }),
  component: Page,
});

const suggestions = [
  "Quelles aides PAC pour ma parcelle de blé ?",
  "Comment devenir agriculteur bio en 2 ans ?",
  "Puis-je installer une haie en bord de champ ?",
  "Quels documents pour vendre en circuit court ?",
];

/** "2026-07-31" -> "31/07/2026" (les dates renvoyées par l'API sont des ISO dates simples). */
function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const [year, month, day] = iso.split("-");
  if (!year || !month || !day) return null;
  return `${day}/${month}/${year}`;
}

function subsidyDateRange(s: Subsidy): string | null {
  const start = formatDate(s.start_date);
  const end = formatDate(s.end_date);
  if (start && end) return `Du ${start} au ${end}`;
  if (end) return `Jusqu'au ${end}`;
  if (start) return `À partir du ${start}`;
  return null;
}

function subsidyMeta(s: Subsidy): string {
  return [s.source_name, s.region, subsidyDateRange(s)].filter(Boolean).join(" · ");
}

function Page() {
  const [messages, setMessages] = useState<{ role: "user" | "bot"; text: string }[]>([
    { role: "bot", text: "Bonjour Jean, je suis votre conseiller réglementaire. Posez-moi une question, ou choisissez une suggestion ci-dessous." },
  ]);
  const [input, setInput] = useState("");
  const [progress, setProgress] = useState(0);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  const chatMutation = useMutation({
    mutationFn: askRegulationAgent,
    onSuccess: (data) => {
      setMessages((m) => [...m, { role: "bot", text: data.answer }]);
    },
  });

  const subsidiesQuery = useQuery({
    queryKey: ["subsidies", 4],
    queryFn: () => fetchSubsidies(4),
  });
  const subsidies = subsidiesQuery.data?.subsidies ?? [];

  // Fait défiler vers le dernier message plutôt que de laisser la carte grandir.
  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, chatMutation.isPending]);

  const send = (t: string) => {
    if (!t.trim() || chatMutation.isPending) return;
    setMessages((m) => [...m, { role: "user", text: t }]);
    setInput("");
    chatMutation.mutate({ question: t });
  };

  const errorMessage =
    chatMutation.error instanceof RegulationApiError
      ? chatMutation.error.message
      : chatMutation.isError
        ? "Une erreur inattendue est survenue en contactant l'agent réglementaire."
        : null;

  const generate = () => {
    setProgress(10);
    const id = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) { clearInterval(id); return 100; }
        return p + 12;
      });
    }, 500);
  };

  return (
    <AppShell>
      <div className="flex items-center gap-3 mb-8">
        <div className="h-11 w-11 rounded-2xl bg-sky/25 text-sky-foreground flex items-center justify-center">
          <ScrollText className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold leading-none">Conseiller Réglementaire</h1>
          <p className="text-muted-foreground mt-1">Posez vos questions en langage naturel.</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        {/* Chat */}
        <div className="card-soft flex flex-col overflow-hidden h-140">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "ml-auto max-w-[80%] rounded-2xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-3"
                    : "max-w-[85%] rounded-2xl rounded-tl-sm bg-secondary text-secondary-foreground px-4 py-3"
                }
              >
                {m.role === "bot" ? <MarkdownLite text={m.text} /> : m.text}
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-secondary text-secondary-foreground px-4 py-3 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Recherche en cours...
              </div>
            )}
            {errorMessage && (
              <AlertBanner tone="danger" title="Agent réglementaire indisponible">
                {errorMessage}
              </AlertBanner>
            )}
            <div ref={scrollAnchorRef} />
          </div>
          <div className="border-t border-border p-4">
            {!messages.some((m) => m.role === "user") && (
              <div className="flex gap-2 flex-wrap mb-3">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    disabled={chatMutation.isPending}
                    className="text-xs rounded-full border border-border bg-background px-3 py-1.5 hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50 disabled:pointer-events-none"
                  >
                    <Sparkles className="inline h-3 w-3 mr-1" />
                    {s}
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Écrivez votre question..."
                className="h-12 rounded-xl text-base"
                disabled={chatMutation.isPending}
                onKeyDown={(e) => e.key === "Enter" && send(input)}
              />
              <Button size="lg" className="h-12 rounded-xl" onClick={() => send(input)} disabled={chatMutation.isPending}>
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Aides financières & dossier */}
        <div className="flex flex-col gap-5">
          <div className="card-soft p-5 h-140 overflow-y-auto">
            <div className="font-display text-lg font-semibold">Aides financières</div>

            {subsidiesQuery.isPending && (
              <div className="mt-3 space-y-3">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="flex items-start gap-3 p-3">
                    <Skeleton className="h-9 w-9 rounded-lg shrink-0" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {subsidiesQuery.isError && (
              <div className="mt-3">
                <AlertBanner tone="danger" title="Aides financières indisponibles">
                  {subsidiesQuery.error instanceof RegulationApiError
                    ? subsidiesQuery.error.message
                    : "Une erreur inattendue est survenue."}
                </AlertBanner>
              </div>
            )}

            {!subsidiesQuery.isPending && !subsidiesQuery.isError && subsidies.length === 0 && (
              <div className="mt-3 flex items-start gap-3 rounded-xl p-3 text-sm text-muted-foreground">
                <FileText className="h-5 w-5 shrink-0 mt-0.5" />
                <span>Aucune aide financière disponible pour le moment.</span>
              </div>
            )}

            {!subsidiesQuery.isPending && !subsidiesQuery.isError && subsidies.length > 0 && (
              <div className="mt-3 space-y-2">
                {subsidies.map((s) => (
                  <a
                    key={s.id}
                    href={s.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-start gap-3 rounded-xl p-3 hover:bg-secondary transition-colors"
                  >
                    <div className="h-9 w-9 rounded-lg bg-sky/20 text-sky-foreground flex items-center justify-center shrink-0">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">{s.name}</div>
                      {s.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {s.description}
                        </p>
                      )}
                      <div className="text-xs text-muted-foreground/80 mt-1.5 font-medium">
                        {subsidyMeta(s)}
                      </div>
                    </div>
                    <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" />
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Générer mon dossier — désactivé pour le moment (pas encore d'endpoint backend).
          <div className="card-soft p-5 bg-gradient-warm">
            <div className="font-display text-lg font-semibold">Générer mon dossier</div>
            <p className="text-sm text-muted-foreground mt-1">
              Nous préparons un dossier PAC pré-rempli avec vos parcelles et aides éligibles.
            </p>
            {progress > 0 && (
              <div className="mt-4">
                <Progress value={progress} className="h-2" />
                <div className="text-xs text-muted-foreground mt-1">
                  {progress < 100 ? `Préparation… ${progress}%` : "Dossier prêt !"}
                </div>
              </div>
            )}
            <Button className="mt-4 w-full rounded-xl h-12" onClick={generate}>
              {progress >= 100 ? "Télécharger" : "Générer mon dossier"}
              <ArrowUpRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
          */}
        </div>
      </div>
    </AppShell>
  );
}
