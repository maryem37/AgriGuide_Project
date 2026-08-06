import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/AppShell";
import { AlertBanner } from "@/components/AlertBanner";
import { PageHeader } from "@/components/PageHeader";
import { Reveal } from "@/components/motion/Reveal";
import { WaitingMascot } from "@/components/chat/WaitingMascot";
import { TypewriterMarkdown } from "@/components/chat/TypewriterMarkdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  FileText,
  ExternalLink,
  Send,
  ScrollText,
  Sparkles,
  ShieldCheck,
  Bot,
  User,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { askRegulationAgent, fetchSubsidies, RegulationApiError, type Subsidy } from "@/lib/regulationApi";
import { MarkdownLite } from "@/lib/markdownLite";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/regulation")({
  head: () => ({
    meta: [
      { title: "Conseiller Réglementaire - AgriMent" },
      {
        name: "description",
        content:
          "Chat, aides, PAC et certifications : toutes les règles agricoles expliquées.",
      },
      { property: "og:title", content: "Conseiller Réglementaire - AgriMent" },
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

type ChatMessage = {
  id: string;
  role: "user" | "bot";
  text: string;
  /** Réponse bot encore en train d'être tapée mot à mot */
  animate?: boolean;
};

function Page() {
  const { user } = useAuth();
  const firstName = user?.nom?.split(" ")[0] ?? "agriculteur";
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "bot",
      text: `Bonjour ${firstName}, je suis votre conseiller réglementaire. Posez-moi une question sur la PAC, les aides ou les normes, ou choisissez une suggestion.`,
      animate: false,
    },
  ]);
  const [input, setInput] = useState("");
  const scrollAnchorRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const chatMutation = useMutation({
    mutationFn: askRegulationAgent,
    onSuccess: (data) => {
      setMessages((m) => [
        ...m,
        {
          id: `bot-${Date.now()}`,
          role: "bot",
          text: data.answer,
          animate: true,
        },
      ]);
    },
  });

  const subsidiesQuery = useQuery({
    queryKey: ["subsidies", 4],
    queryFn: () => fetchSubsidies(4),
  });
  const subsidies = subsidiesQuery.data?.subsidies ?? [];

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, chatMutation.isPending]);

  const send = (t: string) => {
    if (!t.trim() || chatMutation.isPending) return;
    setMessages((m) => [
      ...m,
      { id: `user-${Date.now()}`, role: "user", text: t.trim() },
    ]);
    setInput("");
    chatMutation.mutate({ question: t.trim() });
  };

  const errorMessage =
    chatMutation.error instanceof RegulationApiError
      ? chatMutation.error.message
      : chatMutation.isError
        ? "Une erreur inattendue est survenue en contactant l'agent réglementaire."
        : null;

  const showSuggestions = !messages.some((m) => m.role === "user");

  return (
    <AppShell>
      <PageHeader
        icon={ScrollText}
        tone="sky"
        title="Conseiller Réglementaire"
        subtitle="Questions en langage naturel, réponses sourcées sur le corpus réglementaire."
        className="mb-2"
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px] xl:grid-cols-[minmax(0,1fr)_320px] xl:gap-5">
        {/* Chat panel */}
        <Reveal from="left">
          <section className="flex h-[calc(100dvh-9.5rem)] min-h-[28rem] max-h-[920px] flex-col overflow-hidden rounded-2xl border border-border/80 bg-card shadow-[0_16px_48px_-28px_rgba(28,43,28,0.45)] ring-1 ring-black/[0.02] md:h-[calc(100dvh-8.25rem)]">
            <header className="flex items-center justify-between gap-3 border-b border-border/70 bg-gradient-to-r from-sky/25 via-card to-card px-4 py-3 md:px-5">
              <div className="flex items-center gap-3 min-w-0">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky/40 text-sky-foreground ring-1 ring-sky/30">
                  <Bot className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <div className="font-display text-base font-semibold tracking-tight">
                    Assistant réglementaire
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        chatMutation.isPending ? "bg-waste animate-pulse" : "bg-harvest",
                      )}
                    />
                    {chatMutation.isPending ? "En train de répondre…" : "En ligne"}
                  </div>
                </div>
              </div>
              <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                Réponses sourcées
              </span>
            </header>

            <div
              ref={listRef}
              className="flex-1 space-y-4 overflow-y-auto bg-[radial-gradient(ellipse_at_top,oklch(0.97_0.02_145)_0%,transparent_55%)] px-3 py-4 sm:px-5"
            >
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "page-enter flex gap-2.5",
                    m.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  {m.role === "bot" && (
                    <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-primary ring-1 ring-border/70">
                      <Bot className="h-4 w-4" />
                    </span>
                  )}
                  <div
                    className={cn(
                      "max-w-[min(100%,42rem)] rounded-2xl px-3.5 py-2.5 shadow-sm",
                      m.role === "user"
                        ? "rounded-tr-md bg-primary text-primary-foreground"
                        : "rounded-tl-md border border-border/60 bg-background/90 text-foreground backdrop-blur-sm",
                    )}
                  >
                    {m.role === "bot" ? (
                      m.animate ? (
                        <TypewriterMarkdown
                          key={`type-${m.id}`}
                          text={m.text}
                          wordsPerTick={3}
                          tickMs={18}
                          onProgress={() =>
                            scrollAnchorRef.current?.scrollIntoView({
                              behavior: "auto",
                              block: "end",
                            })
                          }
                          onDone={() =>
                            setMessages((prev) =>
                              prev.map((msg) =>
                                msg.id === m.id ? { ...msg, animate: false } : msg,
                              ),
                            )
                          }
                        />
                      ) : (
                        <div className="text-sm leading-relaxed">
                          <MarkdownLite text={m.text} />
                        </div>
                      )
                    ) : (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.text}</p>
                    )}
                  </div>
                  {m.role === "user" && (
                    <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary ring-1 ring-primary/20">
                      <User className="h-4 w-4" />
                    </span>
                  )}
                </div>
              ))}

              {chatMutation.isPending && (
                <div className="page-enter flex gap-2.5">
                  <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-primary ring-1 ring-border/70">
                    <Bot className="h-4 w-4" />
                  </span>
                  <WaitingMascot label="Analyse de votre question…" />
                </div>
              )}

              {errorMessage && (
                <AlertBanner tone="danger" title="Agent réglementaire indisponible">
                  {errorMessage}
                </AlertBanner>
              )}
              <div ref={scrollAnchorRef} />
            </div>

            <footer className="border-t border-border/70 bg-card/95 p-3 sm:p-4 backdrop-blur-sm">
              {showSuggestions && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {suggestions.map((s, i) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => send(s)}
                      disabled={chatMutation.isPending}
                      style={{ animationDelay: `${0.08 + i * 0.06}s` }}
                      className="page-enter press inline-flex items-center gap-1 rounded-full border border-border/80 bg-background px-3 py-1.5 text-xs text-muted-foreground transition-all duration-300 hover:border-primary/40 hover:bg-secondary hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
                    >
                      <Sparkles className="h-3 w-3 text-primary" />
                      {s}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex items-end gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Écrivez votre question réglementaire…"
                  className="h-12 flex-1 rounded-xl border-border/80 bg-background text-base shadow-none focus-visible:shadow-[0_0_0_3px_var(--color-secondary)]"
                  disabled={chatMutation.isPending}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send(input);
                    }
                  }}
                />
                <Button
                  size="lg"
                  className="press h-12 shrink-0 rounded-xl px-4 transition-transform hover:-translate-y-0.5"
                  onClick={() => send(input)}
                  disabled={chatMutation.isPending || !input.trim()}
                  aria-label="Envoyer"
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Vérifiez toujours auprès de votre chambre d&apos;agriculture avant une
                démarche officielle.
              </p>
            </footer>
          </section>
        </Reveal>

        {/* Aides */}
        <Reveal from="right" delay={100}>
          <aside className="flex h-[calc(100dvh-9.5rem)] min-h-[28rem] max-h-[920px] flex-col overflow-hidden rounded-2xl border border-border/80 bg-card shadow-[0_16px_48px_-28px_rgba(28,43,28,0.4)] md:h-[calc(100dvh-8.25rem)]">
            <div className="border-b border-border/70 px-4 py-3.5 md:px-5">
              <div className="font-display text-lg font-semibold tracking-tight">
                Aides financières
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Échéances proches — sources officielles
              </p>
            </div>
            <div className="flex-1 space-y-1 overflow-y-auto p-2.5 sm:p-3">
              {subsidiesQuery.isPending && (
                <div className="space-y-3 p-1">
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
                <div className="p-1">
                  <AlertBanner tone="danger" title="Aides financières indisponibles">
                    {subsidiesQuery.error instanceof RegulationApiError
                      ? subsidiesQuery.error.message
                      : "Une erreur inattendue est survenue."}
                  </AlertBanner>
                </div>
              )}

              {!subsidiesQuery.isPending && !subsidiesQuery.isError && subsidies.length === 0 && (
                <div className="flex items-start gap-3 rounded-xl p-3 text-sm text-muted-foreground">
                  <FileText className="h-5 w-5 shrink-0 mt-0.5" />
                  <span>Aucune aide financière disponible pour le moment.</span>
                </div>
              )}

              {!subsidiesQuery.isPending &&
                !subsidiesQuery.isError &&
                subsidies.map((s, i) => (
                  <a
                    key={s.id}
                    href={s.source_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ animationDelay: `${0.1 + i * 0.07}s` }}
                    className="page-enter group flex items-start gap-3 rounded-xl p-3 transition-colors hover:bg-secondary/80"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sky/20 text-sky-foreground transition-transform duration-400 group-hover:scale-105 group-hover:rotate-2">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium leading-snug">{s.name}</div>
                      {s.description && (
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          {s.description}
                        </p>
                      )}
                      <div className="mt-1.5 text-[11px] font-semibold text-primary/80">
                        {subsidyMeta(s)}
                      </div>
                    </div>
                    <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-foreground" />
                  </a>
                ))}
            </div>
          </aside>
        </Reveal>
      </div>
    </AppShell>
  );
}
