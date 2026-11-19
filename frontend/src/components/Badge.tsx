import { HTMLAttributes } from "react";
import clsx from "clsx";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-mz-surface-2 text-mz-text-muted border-mz-border",
  success: "bg-mz-success/15 text-mz-success border-mz-success/30",
  warning: "bg-mz-warning/15 text-mz-warning border-mz-warning/30",
  danger: "bg-mz-danger/15 text-mz-danger border-mz-danger/30",
  info: "bg-mz-info/15 text-mz-info border-mz-info/30",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}

/**
 * StatusBadge — la couleur vient directement de `site_status.color` (hex),
 * défini en base et personnalisable par l'ADMIN (section 53). On ne fige donc
 * pas des couleurs en dur dans le composant : elles sont injectées en style inline
 * à partir de la donnée réelle, tout en gardant la forme du Design System.
 */
export function StatusBadge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{
        color,
        borderColor: `${color}4D`, // ~30% opacity
        backgroundColor: `${color}26`, // ~15% opacity
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
