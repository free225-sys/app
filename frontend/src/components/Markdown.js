const inline = (text) =>
  text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part.startsWith("*") && part.endsWith("*") && part.length > 2 ? <em key={i}>{part.slice(1, -1)}</em> : part);

export const Markdown = ({ text = "", className = "" }) => {
  const blocks = [];
  text.split("\n").forEach((raw) => {
    const line = raw.trimEnd();
    const last = blocks[blocks.length - 1];
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (!line.trim()) blocks.push({ type: "gap" });
    else if (h) blocks.push({ type: `h${h[1].length}`, text: h[2] });
    else if (ul || ol) {
      const type = ul ? "ul" : "ol";
      if (last?.type === type) last.items.push((ul || ol)[1]);
      else blocks.push({ type, items: [(ul || ol)[1]] });
    } else if (last?.type === "p") last.text += ` ${line}`;
    else blocks.push({ type: "p", text: line });
  });
  return (
    <div className={`space-y-3 ${className}`} data-testid="markdown">
      {blocks.map((b, i) => {
        if (b.type === "ul") return <ul key={i} className="list-disc space-y-1 pl-6">{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ul>;
        if (b.type === "ol") return <ol key={i} className="list-decimal space-y-1 pl-6">{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ol>;
        if (b.type === "h1" || b.type === "h2") return <h3 key={i} className="pt-2 text-xl">{inline(b.text)}</h3>;
        if (b.type === "h3") return <h4 key={i} className="pt-1 font-semibold">{inline(b.text)}</h4>;
        if (b.type === "p") return <p key={i}>{inline(b.text)}</p>;
        return null;
      })}
    </div>
  );
};
