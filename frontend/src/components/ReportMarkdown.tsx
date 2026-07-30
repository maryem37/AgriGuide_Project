import type { ReactNode } from "react";

/**
 * Rendu minimal du markdown généré par `agent_agriculture` (stage 2 du
 * pipeline LLM, voir `backend/agent_agriculture/app/services/synthesis_service.py`).
 * Le prompt contraint volontairement la sortie à un sous-ensemble simple
 * (titres `##`/`###`, listes `- `, gras `**...**`) donc un vrai moteur
 * markdown (remark/marked) serait disproportionné ici.
 */
export function ReportMarkdown({ markdown }: { markdown: string }) {
  const lines = markdown.split("\n");
  const blocks: ReactNode[] = [];
  let listBuffer: string[] = [];
  let key = 0;

  function flushList() {
    if (listBuffer.length === 0) return;
    blocks.push(
      <ul key={`ul-${key++}`} className="list-disc pl-5 space-y-1 my-2 text-sm leading-relaxed">
        {listBuffer.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>,
    );
    listBuffer = [];
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (line.startsWith("## ")) {
      flushList();
      blocks.push(
        <h2 key={key++} className="font-display text-2xl font-semibold mt-6 mb-2 first:mt-0">
          {line.slice(3)}
        </h2>,
      );
    } else if (line.startsWith("### ")) {
      flushList();
      blocks.push(
        <h3 key={key++} className="font-display text-lg font-semibold mt-4 mb-1">
          {line.slice(4)}
        </h3>,
      );
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      listBuffer.push(line.slice(2));
    } else if (line.trim() === "") {
      flushList();
    } else {
      flushList();
      blocks.push(
        <p key={key++} className="text-sm leading-relaxed my-1.5 text-foreground/90">
          {renderInline(line)}
        </p>,
      );
    }
  }
  flushList();

  return <div>{blocks}</div>;
}

function renderInline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}
