import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useMutation } from "@tanstack/react-query";
import { Bot, MessageCircle, Send, User, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { WaitingMascot } from "@/components/chat/WaitingMascot";
import { TypewriterMarkdown } from "@/components/chat/TypewriterMarkdown";
import { MarkdownLite } from "@/lib/markdownLite";
import { cn } from "@/lib/utils";
import {
  sendChatMessage,
  AgricultureApiError,
  type ChatMessage as ApiChatMessage,
  type ChatParcelContext,
  type ChatSource,
} from "@/lib/agricultureApi";

type UiMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources?: ChatSource[];
  /** Réponse assistant encore en train d'être tapée mot à mot */
  animate?: boolean;
};

const WELCOME =
  "Bonjour ! Posez-moi une question sur l'agriculture en général, ou sur la parcelle actuellement sélectionnée si vous en avez analysé une.";

/**
 * Widget flottant, ouvert depuis une icône en bas à droite. Répond aux
 * questions générales (RAG sur le corpus documentaire) et, si
 * `parcelContext` est fourni (parcelle déjà analysée sur la page
 * courante), aux questions portant sur cette parcelle précise —
 * `app/services/chatbot_service.py` décide lequel des deux contextes
 * utiliser selon la question posée.
 */
export function AgricultureChatWidget({
  parcelContext = null,
}: {
  parcelContext?: ChatParcelContext | null;
}) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [messages, setMessages] = useState<UiMessage[]>([
    { id: "welcome", role: "assistant", text: WELCOME, animate: false },
  ]);
  const [input, setInput] = useState("");
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  // Portail sur document.body : `<main class="page-enter">` (AppShell)
  // porte une animation `transform`, ce qui en fait le containing block de
  // tout `position: fixed` descendant — le widget resterait alors ancré à
  // la page (et disparaîtrait au scroll) plutôt qu'à l'écran. Même fix que
  // components/motion/ScrollMoreHint.tsx pour la même raison.
  useEffect(() => {
    setMounted(true);
  }, []);

  const chatMutation = useMutation({
    mutationFn: (question: string) => {
      const history: ApiChatMessage[] = messages
        .filter((m) => m.id !== "welcome")
        .map((m) => ({ role: m.role, content: m.text }));
      return sendChatMessage({ question, history, parcel_context: parcelContext });
    },
    onSuccess: (data) => {
      setMessages((m) => [
        ...m,
        { id: `assistant-${Date.now()}`, role: "assistant", text: data.answer, sources: data.sources, animate: true },
      ]);
    },
  });

  useEffect(() => {
    if (open) scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, chatMutation.isPending, open]);

  const send = (text: string) => {
    if (!text.trim() || chatMutation.isPending) return;
    setMessages((m) => [...m, { id: `user-${Date.now()}`, role: "user", text: text.trim() }]);
    setInput("");
    chatMutation.mutate(text.trim());
  };

  const errorMessage =
    chatMutation.error instanceof AgricultureApiError
      ? chatMutation.error.message
      : chatMutation.isError
        ? "Une erreur inattendue est survenue en contactant l'assistant."
        : null;

  if (!mounted) return null;

  return createPortal(
    <>
      {/* Icône flottante */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Fermer l'assistant" : "Ouvrir l'assistant agricole"}
        className={cn(
          "fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-[0_12px_32px_-12px_rgba(28,43,28,0.55)] transition-transform duration-200 hover:scale-105",
          "bg-primary text-primary-foreground ring-1 ring-primary/30",
        )}
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>

      {/* Panneau de chat */}
      {open && (
        <div
          className="fixed bottom-24 right-5 z-50 flex h-[min(32rem,calc(100dvh-8rem))] w-[min(24rem,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-border/80 bg-card shadow-[0_24px_64px_-24px_rgba(28,43,28,0.55)] ring-1 ring-black/[0.02]"
          role="dialog"
          aria-label="Assistant agricole"
        >
          <header className="flex items-center gap-3 border-b border-border/70 bg-gradient-to-r from-primary/10 via-card to-card px-4 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/20">
              <Bot className="h-4.5 w-4.5" />
            </span>
            <div className="min-w-0">
              <div className="font-display text-sm font-semibold tracking-tight">Assistant agricole</div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    chatMutation.isPending ? "bg-waste animate-pulse" : "bg-harvest",
                  )}
                />
                {chatMutation.isPending
                  ? "En train de répondre…"
                  : parcelContext
                    ? "Parcelle sélectionnée en contexte"
                    : "En ligne"}
              </div>
            </div>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
            {messages.map((m) => (
              <div key={m.id} className={cn("flex gap-2", m.role === "user" ? "justify-end" : "justify-start")}>
                {m.role === "assistant" && (
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary text-primary ring-1 ring-border/70">
                    <Bot className="h-3.5 w-3.5" />
                  </span>
                )}
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3 py-2 shadow-sm",
                    m.role === "user"
                      ? "rounded-tr-md bg-primary text-primary-foreground"
                      : "rounded-tl-md border border-border/60 bg-background/90 text-foreground",
                  )}
                >
                  {m.role === "assistant" ? (
                    m.animate ? (
                      <TypewriterMarkdown
                        key={`type-${m.id}`}
                        text={m.text}
                        wordsPerTick={3}
                        tickMs={18}
                        onProgress={() => scrollAnchorRef.current?.scrollIntoView({ behavior: "auto", block: "end" })}
                        onDone={() =>
                          setMessages((prev) => prev.map((msg) => (msg.id === m.id ? { ...msg, animate: false } : msg)))
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
                  {m.role === "assistant" && !m.animate && m.sources && m.sources.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5 border-t border-border/50 pt-2">
                      {m.sources.map((s) => (
                        <a
                          key={s.url}
                          href={s.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-muted-foreground underline underline-offset-2 hover:text-primary"
                        >
                          {s.title}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
                {m.role === "user" && (
                  <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary ring-1 ring-primary/20">
                    <User className="h-3.5 w-3.5" />
                  </span>
                )}
              </div>
            ))}

            {chatMutation.isPending && (
              <div className="flex gap-2">
                <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary text-primary ring-1 ring-border/70">
                  <Bot className="h-3.5 w-3.5" />
                </span>
                <WaitingMascot label="Réflexion en cours…" />
              </div>
            )}

            {errorMessage && <p className="text-xs text-destructive">{errorMessage}</p>}
            <div ref={scrollAnchorRef} />
          </div>

          <footer className="border-t border-border/70 bg-card/95 p-2.5">
            <div className="flex items-end gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(input);
                  }
                }}
                placeholder="Posez votre question…"
                disabled={chatMutation.isPending}
                className="text-sm"
              />
              <Button
                type="button"
                size="icon"
                onClick={() => send(input)}
                disabled={chatMutation.isPending || !input.trim()}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </footer>
        </div>
      )}
    </>,
    document.body,
  );
}
