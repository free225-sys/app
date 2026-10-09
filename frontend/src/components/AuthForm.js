import { Container, Eyebrow } from "./common";

export const Field = ({ id, label, hint, ...props }) => (
  <div>
    <label htmlFor={id} className="text-sm font-semibold">{label}</label>
    <input id={id} name={id} className="mt-2 w-full rounded-[10px] border border-[#e5e9ef] bg-white px-3 py-3 text-sm outline-none transition-colors duration-200 focus:border-[#147c77]"
      aria-describedby={hint ? `${id}-hint` : undefined} data-testid={`${id}-input`} {...props} />
    {hint && <p id={`${id}-hint`} className="mt-1.5 text-xs text-[#627086]">{hint}</p>}
  </div>
);

export const FormError = ({ message, testId }) =>
  message ? (
    <p role="alert" className="border-l-2 border-[#A04444] bg-[#FBECEC] px-4 py-3 text-sm text-[#7E2828]" data-testid={testId}>{message}</p>
  ) : null;

export const AuthShell = ({ eyebrow, title, lead, children, aside, testId }) => (
  <Container className="grid gap-14 py-16 sm:py-24 lg:grid-cols-12" data-testid={testId}>
    <div className="lg:col-span-6">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">{title}</h1>
      {lead && <p className="mt-5 max-w-xl text-base leading-relaxed text-[#505e75] md:text-lg">{lead}</p>}
      <div className="mt-10 max-w-md">{children}</div>
    </div>
    {aside && <aside className="self-start border border-[#e5e9ef] bg-white p-7 lg:col-span-5 lg:col-start-8">{aside}</aside>}
  </Container>
);

export const AccountBenefits = () => (
  <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#627086]">Avec un compte</p>
    <ul className="mt-4 space-y-3 text-sm leading-relaxed">
      <li>Suivre les modules ressource par ressource et reprendre là où vous vous êtes arrêté.</li>
      <li>Passer les évaluations notées et faire reconnaître vos compétences, preuves à l'appui.</li>
      <li>Retrouver votre progression de la démonstration et votre test de positionnement.</li>
    </ul>
  </>
);
