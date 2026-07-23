import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from "react";
import { cn } from "@/utils/cn";

export type ButtonVariant = "primary" | "outline" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
}

const variantMap: Record<ButtonVariant, string> = {
  primary: "btn-primary",
  outline: "btn-outline",
  ghost: "btn-ghost",
};

const sizeMap: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "",
  lg: "px-5 py-3 text-base",
};

/**
 * Универсальная кнопка. Тонкая обёртка над .btn-* из global.css,
 * чтобы варианты были и через проп variant, и через className.
 */
const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    leftIcon,
    rightIcon,
    fullWidth = false,
    disabled,
    className,
    children,
    type,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      // Если type не передан — считаем "button", чтобы случайный Enter в форме не сабмитил.
      type={type ?? "button"}
      disabled={disabled || loading}
      className={cn(
        variantMap[variant],
        sizeMap[size],
        fullWidth && "w-full",
        className,
      )}
      {...rest}
    >
      {loading ? (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!loading && rightIcon}
    </button>
  );
});

export default Button;
