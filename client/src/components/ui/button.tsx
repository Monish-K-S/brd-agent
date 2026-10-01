import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-full border border-transparent bg-clip-padding font-sans text-base font-medium whitespace-nowrap outline-none select-none focus-visible:ring-3 focus-visible:ring-ink/25 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-error aria-invalid:ring-3 aria-invalid:ring-error/20 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "press bg-primary px-6 py-[11px] text-sm font-semibold text-surface hover:bg-primary-deep active:bg-primary-deep",
        brand:
          "press bg-primary px-6 py-[11px] text-sm font-semibold text-surface hover:bg-primary-deep active:bg-primary-deep",
        ink:
          "press bg-primary px-6 py-[11px] text-sm font-semibold text-surface hover:bg-primary-deep active:bg-primary-deep",
        outline:
          "press border-edge/60 bg-transparent px-6 py-[11px] text-sm font-semibold text-ink hover:border-edge hover:bg-soft aria-expanded:bg-soft",
        utility:
          "press rounded-lg border border-hairline bg-surface px-3.5 py-1 text-sm font-medium text-ink hover:border-edge/60 hover:bg-soft aria-expanded:bg-soft",
        accent:
          "press bg-signal px-6 py-[11px] text-sm font-semibold text-ink hover:bg-signal-deep active:bg-signal-deep disabled:bg-hairline disabled:text-faint",
        secondary:
          "press border-hairline bg-soft px-6 py-[11px] text-sm font-semibold text-ink hover:bg-soft-deep aria-expanded:bg-soft-deep",
        subtle:
          "press bg-soft px-6 py-[11px] text-sm font-semibold text-ink hover:bg-soft-deep aria-expanded:bg-soft-deep",
        ghost:
          "press text-ink hover:bg-soft aria-expanded:bg-soft",
        destructive:
          "press border-hairline bg-surface px-6 py-[11px] text-sm font-semibold text-error hover:border-error/40 hover:bg-error/5",
        link: "text-ink underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-11 gap-1.5 px-6 has-data-[icon=inline-end]:pr-5 has-data-[icon=inline-start]:pl-5",
        xs: "h-9 gap-1 rounded-full px-4 text-sm in-data-[slot=button-group]:rounded-full has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-9 gap-1 rounded-full px-4 text-sm in-data-[slot=button-group]:rounded-full has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-14 gap-1.5 rounded-full px-6 text-lg has-data-[icon=inline-end]:pr-5 has-data-[icon=inline-start]:pl-5",
        icon: "size-11 rounded-full",
        "icon-xs":
          "size-9 rounded-full in-data-[slot=button-group]:rounded-full [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-9 rounded-full max-md:size-11 in-data-[slot=button-group]:rounded-full",
        "icon-lg": "size-14 rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button }
