import { cn } from "cn";

type Intensity = "restrained" | "soft" | "atmospheric" | "expressive" | "strong";

const layers: Record<Intensity, { dots: string; washes: string; folds: string }> = {
  // Workspace: the most restrained — texture only at the page margins.
  restrained: { dots: "opacity-40", washes: "opacity-60", folds: "opacity-30" },
  // Auth: quiet version of the landing field.
  soft: { dots: "opacity-60", washes: "opacity-80", folds: "opacity-40" },
  // Workspaces index: calm atmosphere behind the list.
  atmospheric: { dots: "opacity-80", washes: "opacity-90", folds: "opacity-50" },
  // 404: the most expressive brand moment outside the landing.
  expressive: { dots: "opacity-100", washes: "opacity-100", folds: "opacity-70" },
  // Landing: strongest treatment.
  strong: { dots: "opacity-100", washes: "opacity-100", folds: "opacity-60" },
};

export function FieldBackdrop({
  intensity = "strong",
  className,
}: {
  intensity?: Intensity;
  className?: string;
}) {
  const l = layers[intensity];
  return (
    <div
      aria-hidden="true"
      className={cn("pointer-events-none fixed inset-0 -z-10 overflow-hidden", className)}
    >
      <div className={cn("field-washes absolute inset-0", l.washes)} />
      <div className={cn("field-folds absolute inset-0", l.folds)} />
      <div className={cn("field-dots absolute -inset-24", l.dots)} />
      <div className="field-grain absolute inset-0" />
    </div>
  );
}
