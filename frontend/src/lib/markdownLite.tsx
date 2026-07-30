import type { ReactNode } from "react";

/**
 * Rendu minimal du markdown renvoyé par les agents LLM (titres #/##/###, gras
 * **texte**, listes à puces -, liens [texte](url)) — pas de dépendance externe.
 */

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const regex = /\*\*(.+?)\*\*|\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    if (match[1] !== undefined) {
      parts.push(<strong key={`${keyPrefix}-b-${i}`}>{match[1]}</strong>);
    } else if (match[2] !== undefined) {
      parts.push(
        <a
          key={`${keyPrefix}-a-${i}`}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-2"
        >
          {match[2]}
        </a>,
      );
    }
    lastIndex = regex.lastIndex;
    i++;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

export function MarkdownLite({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = (key: string) => {
    if (listItems.length === 0) return;
    blocks.push(
      <ul key={key} className="list-disc pl-5 space-y-0.5">
        {listItems.map((item, idx) => (
          <li key={`${key}-${idx}`}>{renderInline(item, `${key}-${idx}`)}</li>
        ))}
      </ul>,
    );
    listItems = [];
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    const headerMatch = /^(#{1,3})\s+(.*)$/.exec(trimmed);
    const bulletMatch = /^[-*]\s+(.*)$/.exec(trimmed);

    if (headerMatch) {
      flushList(`list-${idx}`);
      const level = headerMatch[1].length;
      const sizeClass =
        level === 1 ? "text-base font-semibold" : level === 2 ? "text-sm font-semibold" : "text-sm font-medium";
      blocks.push(
        <div key={`h-${idx}`} className={`${sizeClass} mt-2 first:mt-0`}>
          {renderInline(headerMatch[2], `h-${idx}`)}
        </div>,
      );
    } else if (bulletMatch) {
      listItems.push(bulletMatch[1]);
    } else if (trimmed === "") {
      flushList(`list-${idx}`);
    } else {
      flushList(`list-${idx}`);
      blocks.push(
        <p key={`p-${idx}`} className="mt-1 first:mt-0">
          {renderInline(line, `p-${idx}`)}
        </p>,
      );
    }
  });
  flushList("list-end");

  return <div className="space-y-0.5">{blocks}</div>;
}
