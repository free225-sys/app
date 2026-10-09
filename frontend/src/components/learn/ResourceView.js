import { CheckCircle2, Clock, PlayCircle } from "lucide-react";
import { BTN_PRIMARY, BTN_SECONDARY } from "@/components/common";
import { API } from "@/lib/api";
import { Markdown } from "@/components/Markdown";

const VideoPlaceholder = ({ title }) => (
  <figure className="mt-8" data-testid="video-placeholder">
    <div className="relative flex aspect-video w-full flex-col items-center justify-center gap-3 border border-[#14243c]/20 bg-[#14243c] text-[#f7f8fa]" role="img" aria-label={`Emplacement vidéo : ${title}`}>
      <PlayCircle size={48} strokeWidth={1.25} aria-hidden="true" />
      <p className="px-6 text-center text-sm">Vidéo illustrative — contenu à venir</p>
      <span className="absolute left-3 top-3 rounded-[10px] bg-[#f7f8fa] px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-[#14243c]">Emplacement réservé</span>
    </div>
    <figcaption className="mt-2 text-xs text-[#627086]">La vidéo définitive sera intégrée ici. La transcription ci-dessous en reprend le contenu.</figcaption>
  </figure>
);

export const ResourceView = ({ resource, index, total, completed, onComplete, onNext, nextLabel, busy }) => (
  <article aria-labelledby="resource-title" data-testid={`resource-view-${resource.id}`}>
    <div className="flex flex-wrap items-center gap-3 text-xs text-[#627086]">
      <span className="font-mono">Ressource {index + 1}/{total}</span>
      <span className="font-semibold text-[#14243c]">{resource.type}</span>
      <span className="inline-flex items-center gap-1"><Clock size={12} aria-hidden="true" />{resource.duration_min} min</span>
    </div>
    <h2 id="resource-title" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">{resource.title}</h2>
    {resource.type === "Vidéo" && (resource.video_url ? (
      <div className="mt-8 aspect-video w-full border border-[#e5e9ef] bg-[#14243c]" data-testid="video-embed">
        <iframe src={resource.video_url} title={resource.title} className="h-full w-full" allowFullScreen />
      </div>
    ) : <VideoPlaceholder title={resource.title} />)}
    {resource.file && (
      <p className="mt-6">
        <a href={`${API}/resources/${resource.id}/file`} className="text-sm font-semibold text-[#147c77] underline underline-offset-4" data-testid="resource-file-link">
          Télécharger le document joint ({resource.file.original_filename})
        </a>
      </p>
    )}
    <div className="mt-10 max-w-[68ch] space-y-12">
      {(resource.sections || []).map((s) => (
        <section key={s.heading}>
          <h3 className="text-xl font-semibold">{s.heading}</h3>
          <Markdown text={s.body} className="mt-3 text-base leading-[1.8]" />
        </section>
      ))}
    </div>
    <div className="mt-14 flex flex-col gap-3 border-t border-[#e5e9ef] pt-6 sm:flex-row sm:items-center sm:justify-between">
      {completed ? (
        <p className="inline-flex items-center gap-2 text-sm font-semibold text-[#147c77]" data-testid="resource-completed-label">
          <CheckCircle2 size={18} aria-hidden="true" /> Ressource terminée
        </p>
      ) : (
        <button type="button" className={BTN_PRIMARY} onClick={onComplete} disabled={busy} data-testid="resource-complete-button">
          J'ai terminé cette ressource
        </button>
      )}
      {onNext && <button type="button" className={BTN_SECONDARY} onClick={onNext} data-testid="resource-next-button">{nextLabel}</button>}
    </div>
  </article>
);
