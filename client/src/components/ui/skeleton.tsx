import { cn } from "cn";

type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      data-slot="skeleton"
      className={cn("rounded-lg bg-black/8", className)}
    />
  );
}
