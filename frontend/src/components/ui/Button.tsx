import { cloneElement, forwardRef, isValidElement, type ButtonHTMLAttributes, type ReactElement } from "react";
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
  { asChild = false, children, className, size, type = "button", variant, ...props },
  ref,
) {
  if (asChild && isValidElement(children)) {
    const child = children as ReactElement<{ className?: string }>;
    return cloneElement(child, {
      className: buttonVariants({ className: cn(child.props.className, className), size, variant }),
    });
  }

  return (
    <button ref={ref} className={buttonVariants({ className, size, variant })} data-slot="button" type={type} {...props}>
      {children}
    </button>
  );
});
