import { Link } from "react-router-dom";
import { Container, LAYER_STYLE, SectionTitle } from "@/components/common";

export const ArchitectureBands = ({ layers, stages, steps }) => (
  <section className="py-20 sm:py-28" aria-labelledby="archi-title" data-testid="home-architecture">
    <Container>
      <SectionTitle id="archi-title" eyebrow="Architecture" title="Six couches qui traversent toutes les étapes."
        lead="Les couches ne se succèdent pas : elles sont mobilisées, à des degrés divers, tout au long du traitement. Les repères indiquent les étapes où chaque couche est principalement active dans la démonstration." />
      <div className="mt-14">
        <div className="hidden grid-cols-[16rem_1fr] gap-6 pb-3 md:grid" aria-hidden="true">
          <span />
          <div className="grid grid-cols-7">
            {stages.map((s) => (
              <span key={s.id} className="text-center font-mono text-xs text-[#627086]">
                {s.code} <span className="hidden lg:inline">{s.name}</span>
              </span>
            ))}
          </div>
        </div>
        <ul className="space-y-2">
          {layers.map((l) => {
            const st = LAYER_STYLE[l.id] || {};
            const active = steps.filter((s) => s.active_layer_ids.includes(l.id)).map((s) => s.number);
            return (
              <li key={l.id} className="grid gap-3 border-l-[3px] py-4 pl-5 md:grid-cols-[16rem_1fr] md:items-center md:gap-6"
                style={{ borderColor: l.color, background: st.soft }} data-testid={`architecture-band-${l.id}`}>
                <div>
                  <p className="text-base font-semibold" style={{ color: st.text }}>{l.name}</p>
                  <p className="text-xs text-[#505e75]">{l.short}</p>
                </div>
                <div className="relative grid grid-cols-7 pr-4" aria-label={`Active aux étapes ${active.join(", ")}`} role="img">
                  <span className="absolute left-0 right-4 top-1/2 h-px" style={{ background: `${l.color}55` }} aria-hidden="true" />
                  {stages.map((s) => (
                    <span key={s.id} className="relative flex justify-center" aria-hidden="true">
                      <span className={`h-3 w-3 rounded-full border-2 ${active.includes(s.order) ? "" : "bg-[#f7f8fa]"}`}
                        style={{ borderColor: l.color, background: active.includes(s.order) ? l.color : undefined }} />
                    </span>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
        <p className="mt-6 text-sm text-[#505e75]">
          Chaque couche est détaillée, avec ses modules, dans la{" "}
          <Link to="/demo" className="font-semibold text-[#147c77] underline underline-offset-4" data-testid="architecture-demo-link">démonstration</Link> et dans les{" "}
          <Link to="/ressources" className="font-semibold text-[#147c77] underline underline-offset-4" data-testid="architecture-resources-link">ressources</Link>.
        </p>
      </div>
    </Container>
  </section>
);
