import { type ReactNode, useState } from "react";

type Props = {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
};

export default function CollapsibleSection({ title, children, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="fc-section">
      <button type="button" className="fc-section-title" onClick={() => setOpen((value) => !value)}>
        <span>{title}</span>
        <span>{open ? "Hide" : "Show"}</span>
      </button>
      {open && <div className="fc-section-body">{children}</div>}
    </section>
  );
}
