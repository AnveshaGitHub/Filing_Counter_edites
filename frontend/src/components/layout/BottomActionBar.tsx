import type { PropsWithChildren } from "react";

type Props = PropsWithChildren;

export default function BottomActionBar({ children }: Props) {
  return <div className="bottom-action-bar">{children}</div>;
}
