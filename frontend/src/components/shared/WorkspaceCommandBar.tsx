import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { clsx } from "../ui/clsx";

export function WorkspaceCommandBar({
  children,
  actions,
  className,
}: {
  children?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  const [slot, setSlot] = useState<Element | null>(null);

  useEffect(() => {
    setSlot(document.getElementById("wcb-slot"));
  }, []);

  if (!slot) return null;

  return createPortal(
    <div className={clsx("flex h-full min-w-0 flex-1 items-center justify-between gap-3 px-4", className)}>
      <div className="flex min-w-0 flex-1 items-center gap-3">{children}</div>
      {actions != null && (
        <div className="flex shrink-0 items-center gap-3">{actions}</div>
      )}
    </div>,
    slot,
  );
}
