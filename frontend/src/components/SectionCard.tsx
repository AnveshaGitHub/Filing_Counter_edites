import type { PropsWithChildren, ReactNode } from "react";

type Props = PropsWithChildren<{
  title: string;
  actions?: ReactNode;
}>;

export default function SectionCard({ title, actions, children }: Props) {
  return (
    <section className="section-card">
      <div className="section-card__header">
        <h2>{title}</h2>
        <div>{actions}</div>
      </div>
      <div className="section-card__body">{children}</div>
    </section>
  );
}
