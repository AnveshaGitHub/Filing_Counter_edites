import type { PropsWithChildren } from "react";

type Props = PropsWithChildren<{
  title: string;
}>;

export default function FilingSection({ title, children }: Props) {
  return (
    <section className="form-section field--wide">
      <h3 className="form-section__title">{title}</h3>
      <div className="form-subgrid">{children}</div>
    </section>
  );
}
