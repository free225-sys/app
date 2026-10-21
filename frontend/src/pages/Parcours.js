import { useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useApi, useCatalog } from "@/lib/api";
import { Container, ErrorState, Eyebrow, LINK_ARROW, Loading, PageHeader, SectionTitle, levelRange } from "@/components/common";
import { Picto } from "@/components/Pictos";

const families = (pathways) => [
  { id: "socle", label: "Parcours du socle", text: "Parcours historiques de l'académie, codes P01 et P02, construits sur les cours C01 à C04.", items: pathways.filter((p) => /^P\d+$/.test(p.code)) },
  { id: "catalogue", label: "Parcours du catalogue documentaire", text: "Parcours issus du catalogue importé, codes P-001 et P-002, construits sur les cours CO-001 et CO-002.", items: pathways.filter((p) => !/^P\d+$/.test(p.code)) },
].filter((f) => f.items.length);

const CourseBlock = ({ course, shared }) => (
  <li id={course.id} className="scroll-mt-24 border border-[#e5e9ef] bg-white" data-testid={`course-${course.id}`}>
    <div className="border-b border-[#e5e9ef] p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-mono font-semibold text-[#147c77]">Cours {course.code}</span>
        <span className="font-mono text-[#627086]">{levelRange(course.levels)} · durée pédagogique {course.duration_hours} h</span>
      </div>
      <h4 className="mt-2 text-xl font-semibold"><Link to={`/courses/${course.id}`} className="hover:underline" data-testid={`course-open-link-${course.id}`}>{course.title}</Link></h4>
      <p className="mt-2 text-sm leading-relaxed text-[#505e75]">{course.summary}</p>
    </div>
    <ol className="divide-y divide-[#e5e9ef]">
      {course.modules.map((m, i) => (
        <li key={m.id}>
          <Link to={`/modules/${m.id}`} className="group flex items-baseline gap-3 px-6 py-3 text-sm hover:bg-[#f7f8fa]" data-testid={`course-${course.id}-module-${m.id}`}>
            <span className="w-5 font-mono text-xs text-[#627086]">{i + 1}</span>
            <span className="font-mono text-xs font-semibold text-[#147c77]">{m.code}</span>
            <span className="flex-1 group-hover:underline">{m.title}</span>
            {shared.has(m.id) && <span className="hidden rounded-[10px] bg-[#EDF3F8] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#254a98] sm:inline" data-testid={`shared-module-${course.id}-${m.id}`}>Partagé</span>}
          </Link>
        </li>
      ))}
    </ol>
  </li>
);

export default function Parcours() {
  const catalog = useCatalog();
  const { data: pathways, loading, error } = useApi("/pathways");
  const shared = useMemo(() => {
    const count = {};
    (pathways || []).forEach((p) => p.courses.forEach((c) => c.module_ids.forEach((id) => { count[id] = (count[id] || 0) + 1; })));
    return new Set(Object.keys(count).filter((k) => count[k] > 1));
  }, [pathways]);

  return (
    <div data-testid="parcours-page">
      <PageHeader eyebrow="Parcours" title={pathways && catalog ? `${catalog.profiles.length} entrées, ${pathways.length} parcours, un même socle.` : "Entrées et parcours"}
        lead="Choisissez une entrée selon votre rôle ; vos acquis vous suivent d'un parcours à l'autre."
        more={<p>Chaque parcours assemble des cours, eux-mêmes composés de modules. Un module peut servir plusieurs cours : il est rédigé une fois et mis à jour partout.</p>}>
        <Link to="/diagnostic" className={`${LINK_ARROW} mt-8`} data-testid="parcours-diagnostic-link">Hésitez-vous ? Passez le test de positionnement (8 questions) <ArrowRight size={14} aria-hidden="true" /></Link>
      </PageHeader>
      {error && <ErrorState />}
      {(loading || !catalog) && !error && <Loading />}
      {pathways && catalog && (
        <>
          <section className="py-16 sm:py-20" aria-labelledby="entries-title">
            <Container>
              <SectionTitle id="entries-title" eyebrow="Profils d'entrée" title="Par où commencer ?" />
              <ul className="mt-10 grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
                {catalog.profiles.map((p) => (
                  <li key={p.id} id={p.id} className="scroll-mt-24 flex flex-col rounded-[17px] border border-[#e5e9ef] bg-white p-8" data-testid={`entry-profile-${p.id}`}>
                    <Picto id={p.id} size={22} />
                    <p className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">{p.audience}</p>
                    <h3 className="mt-2 text-2xl font-semibold">{p.name}</h3>
                    <p className="mt-2 flex-1 text-sm leading-relaxed text-[#505e75]">{p.promise}</p>
                    <p className="mt-4 font-mono text-xs text-[#627086]">Niveaux {levelRange(p.levels)}</p>
                    <a href={`#${p.course_ids[0]}`} className={`${LINK_ARROW} mt-3`} data-testid={`entry-profile-course-link-${p.id}`}>
                      Cours de départ {p.course_ids[0]} <ArrowRight size={14} aria-hidden="true" />
                    </a>
                  </li>
                ))}
              </ul>
            </Container>
          </section>
          <section className="border-t border-[#e5e9ef] py-16 sm:py-20" aria-labelledby="pathways-title">
            <Container>
              <SectionTitle id="pathways-title" eyebrow="Parcours" title={`${pathways.length} parcours structurés`}
                lead="Des cours obligatoires et optionnels, des compétences cibles et un certificat." />
              {families(pathways).map((fam) => (
              <div key={fam.id} className="mt-14" data-testid={`pathway-family-${fam.id}`}>
                <h3 className="text-lg">{fam.label} <span className="ml-2 font-mono text-sm text-[#627086]">{fam.items.length} parcours</span></h3>
                <p className="mt-2 max-w-[68ch] text-sm text-[#505e75]">{fam.text}</p>
              <div className="mt-10 space-y-16">
                {fam.items.map((p) => (
                  <article key={p.id} id={p.id} className="scroll-mt-24" data-testid={`pathway-${p.id}`}>
                    <div className="grid gap-4 lg:grid-cols-12">
                      <div className="lg:col-span-4">
                        <Eyebrow>Parcours {p.code}</Eyebrow>
                        <h3 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl"><Link to={`/pathways/${p.id}`} className="hover:underline" data-testid={`pathway-open-link-${p.id}`}>{p.title}</Link></h3>
                        <p className="mt-3 text-sm leading-relaxed text-[#505e75]">{p.summary}</p>
                        <Link to={`/pathways/${p.id}`} className={`${LINK_ARROW} mt-4`} data-testid={`pathway-enroll-link-${p.id}`}>Voir le parcours et s'inscrire <ArrowRight size={14} aria-hidden="true" /></Link>
                        <p className="mt-4 text-xs text-[#627086]">
                          Public : {p.profile_ids.map((id) => catalog.profiles.find((x) => x.id === id)?.name).join(", ")} · Version {p.version}
                        </p>
                      </div>
                      <ul className="grid gap-5 lg:col-span-8 xl:grid-cols-2">
                        {p.courses.map((c) => <CourseBlock key={c.id} course={c} shared={shared} />)}
                      </ul>
                    </div>
                  </article>
                ))}
              </div>
              </div>
              ))}
              <p className="mt-12 text-sm text-[#505e75]">
                Les modules marqués « Partagé » figurent dans plusieurs cours : il s'agit du même module, maintenu en un seul endroit.
              </p>
            </Container>
          </section>
        </>
      )}
    </div>
  );
}
