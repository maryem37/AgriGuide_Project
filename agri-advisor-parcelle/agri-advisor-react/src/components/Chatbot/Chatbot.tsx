import { useEffect, useRef, useState } from "react";
import type { NeighborCropContext, ParcelResolution } from "../../types/api";
import { answerQuestion, getSuggestions, type ChatContext } from "./chatKnowledge";
import "./Chatbot.css";

interface ChatMessage {
  id: number;
  role: "bot" | "user";
  text: string;
}

interface ChatbotProps {
  parcel: ParcelResolution | null;
  neighbors: NeighborCropContext | null;
  reportMarkdown: string | null;
  ndviAvailable: boolean;
}

const GREETING =
  "Bonjour, je suis Marc, votre conseiller de terrain 👨‍🌾 Posez-moi une question sur votre parcelle, ou choisissez une suggestion ci-dessous.";

export function Chatbot({ parcel, neighbors, reportMarkdown, ndviAvailable }: ChatbotProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([{ id: 0, role: "bot", text: GREETING }]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const nextId = useRef(1);
  const scrollRef = useRef<HTMLDivElement>(null);

  const ctx: ChatContext = { parcel, neighbors, reportMarkdown, ndviAvailable };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, typing]);

  function send(text: string) {
    const question = text.trim();
    if (!question) return;

    const userMsg: ChatMessage = { id: nextId.current++, role: "user", text: question };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setTyping(true);

    // Small delay so the reply reads like a real exchange rather than an instant lookup.
    window.setTimeout(() => {
      const answer = answerQuestion(question, ctx);
      setMessages((m) => [...m, { id: nextId.current++, role: "bot", text: answer }]);
      setTyping(false);
    }, 450);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(input);
  }

  const suggestions = getSuggestions(ctx);

  return (
    <>
      <button
        className="chat-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Fermer le conseiller" : "Ouvrir le conseiller"}
      >
        {open ? "✕" : "👨‍🌾"}
      </button>

      {open && (
        <div className="chat-panel" role="dialog" aria-label="Conseiller agricole">
          <div className="chat-head">
            <div className="chat-avatar">👨‍🌾</div>
            <div>
              <div className="chat-name">Marc</div>
              <div className="chat-role">Conseiller de terrain</div>
            </div>
          </div>

          <div className="chat-body" ref={scrollRef}>
            {messages.map((m) => (
              <div className={`chat-msg ${m.role}`} key={m.id}>
                {m.text}
              </div>
            ))}
            {typing && (
              <div className="chat-msg bot chat-typing">
                <span />
                <span />
                <span />
              </div>
            )}
          </div>

          {suggestions.length > 0 && (
            <div className="chat-chips">
              {suggestions.map((s) => (
                <button key={s} className="chat-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}

          <form className="chat-input-row" onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Posez votre question…"
              aria-label="Votre question"
            />
            <button type="submit" disabled={!input.trim()} aria-label="Envoyer">
              ➤
            </button>
          </form>
        </div>
      )}
    </>
  );
}
