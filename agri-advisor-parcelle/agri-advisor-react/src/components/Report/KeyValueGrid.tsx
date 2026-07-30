import { extractKeyValues } from "./reportParser";

export function KeyValueGrid({ body }: { body: string }) {
  const kvs = extractKeyValues(body);
  if (!kvs.length) return null;

  return (
    <div className="kvg">
      {kvs.map((kv, i) => (
        <div className="kvi" key={i}>
          <div className="kvl">{kv.key}</div>
          <div className="kvv">{kv.val}</div>
          {kv.note && <div className="kvs">{kv.note}</div>}
        </div>
      ))}
    </div>
  );
}
