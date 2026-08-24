import { Slot } from "@radix-ui/react-slot";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "./utils";

type ButtonVariant = "default" | "primary";
type ButtonSize = "default" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
};

export function buttonVariants({
  className,
  size = "default",
  variant = "default",
}: {
  className?: string;
  size?: ButtonSize;
  variant?: ButtonVariant;
} = {}): string {
  return cn("ui-button", `ui-button-${variant}`, `ui-button-${size}`, className);
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { asChild = false, children, className, disabled, size, type = "button", variant, ...props },
  ref,
) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      ref={ref}
      className={buttonVariants({ className, size, variant })}
      data-disabled={disabled ? "true" : undefined}
      data-slot="button"
      disabled={asChild ? undefined : disabled}
      type={asChild ? undefined : type}
      {...props}
    >
      {children}
    </Component>
  );
});
