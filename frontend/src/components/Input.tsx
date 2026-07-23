import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/utils/cn";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
  hint?: string;
  leftIcon?: ReactNode;
  rightSlot?: ReactNode;
}

/**
 * Поле ввода с лейблом, иконкой и валидационным сообщением.
 * Пересылает ref к input — удобно для автофокуса и тестов.
 */
const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, leftIcon, rightSlot, className, id, ...rest },
  ref,
) {
  const inputId = id ?? rest.name ?? undefined;
  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="label">
          {label}
        </label>
      )}
      <div className="relative">
        {leftIcon && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400">
            {leftIcon}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            "input",
            leftIcon && "pl-10",
            rightSlot && "pr-10",
            error &&
              "border-red-400 focus:border-red-500 focus:ring-red-400/30 dark:border-red-500/70",
            className,
          )}
          aria-invalid={error ? true : undefined}
          {...rest}
        />
        {rightSlot && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400">
            {rightSlot}
          </span>
        )}
      </div>
      {(error || hint) && (
        <p
          className={cn(
            "mt-1.5 text-xs",
            error ? "text-red-600 dark:text-red-400" : "muted",
          )}
        >
          {error ?? hint}
        </p>
      )}
    </div>
  );
});

export default Input;
