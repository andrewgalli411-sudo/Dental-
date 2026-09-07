import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const base =
    "inline-flex items-center justify-center rounded-sm px-3 py-1.5 text-13 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors";
  const styles =
    variant === "primary"
      ? "bg-accent text-white border border-accent-hover hover:bg-accent-hover"
      : "bg-surface text-ink border border-borderstrong hover:bg-surfacealt";
  return <button className={`${base} ${styles} ${className}`} {...props} />;
}
