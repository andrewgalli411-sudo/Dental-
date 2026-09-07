// Status icons — shape-distinct so status reads without color (colorblind / B&W).

type P = { className?: string };
const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function CheckIcon({ className }: P) {
  return (
    <svg {...base} strokeWidth={3} className={className}>
      <path d="M4 12l6 6L20 6" />
    </svg>
  );
}

export function SlashCircleIcon({ className }: P) {
  return (
    <svg {...base} strokeWidth={2.5} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M7 7l10 10" />
    </svg>
  );
}

export function WarnTriangleIcon({ className }: P) {
  return (
    <svg {...base} strokeWidth={2.4} className={className}>
      <path d="M12 3l9 16H3z" />
      <path d="M12 10v4" />
      <path d="M12 17.5v.5" />
    </svg>
  );
}

export function DashCircleIcon({ className }: P) {
  return (
    <svg {...base} strokeWidth={2.4} className={className}>
      <circle cx="12" cy="12" r="9" strokeDasharray="3 3" />
    </svg>
  );
}
