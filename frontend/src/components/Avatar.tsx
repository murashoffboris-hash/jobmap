import { type HTMLAttributes } from "react";
import { cn } from "@/utils/cn";
import { getAvatarColor, getInitials } from "@/utils/avatar";

export interface AvatarProps extends HTMLAttributes<HTMLDivElement> {
  name?: string | null;
  email?: string | null;
  size?: "xs" | "sm" | "md" | "lg";
  ring?: boolean;
}

const sizeMap: Record<NonNullable<AvatarProps["size"]>, string> = {
  xs: "h-7 w-7 text-[10px]",
  sm: "h-9 w-9 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-14 w-14 text-base",
};

/**
 * Круглый аватар с градиентом и инициалами. Используется в Header,
 * списке пользователей, профиле. Цвет детерминирован от seed-строки.
 */
export default function Avatar({
  name,
  email,
  size = "md",
  ring = false,
  className,
  ...rest
}: AvatarProps): JSX.Element {
  const seed = name?.trim() || email?.trim() || "?";
  const initials = getInitials(name, email);
  return (
    <div
      {...rest}
      className={cn(
        "inline-flex select-none items-center justify-center rounded-full font-semibold text-white shadow-sm",
        "bg-gradient-to-br",
        getAvatarColor(seed),
        sizeMap[size],
        ring && "ring-2 ring-white dark:ring-ink-900",
        className,
      )}
      aria-hidden="true"
      title={name ?? email ?? ""}
    >
      {initials}
    </div>
  );
}
