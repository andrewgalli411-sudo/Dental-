import { CheckIcon, DashCircleIcon, SlashCircleIcon, WarnTriangleIcon } from "./icons";

// Maps any backend status string to an icon + label + color. Everything not
// active/inactive reads as "needs attention" for v1.
const MAP: Record<
  string,
  { label: string; cls: string; Icon: (p: { className?: string }) => JSX.Element }
> = {
  active: { label: "Active", cls: "text-ok-ink bg-ok-bg border-ok-bd", Icon: CheckIcon },
  inactive: { label: "Inactive", cls: "text-bad-ink bg-bad-bg border-bad-bd", Icon: SlashCircleIcon },
  pending: { label: "Pending", cls: "text-warn-ink bg-warn-bg border-warn-bd", Icon: WarnTriangleIcon },
  needs_info: { label: "Needs info", cls: "text-warn-ink bg-warn-bg border-warn-bd", Icon: WarnTriangleIcon },
  error: { label: "Error", cls: "text-warn-ink bg-warn-bg border-warn-bd", Icon: WarnTriangleIcon },
  not_verified: { label: "Not verified", cls: "text-ink2 bg-surfacealt border-border", Icon: DashCircleIcon },
};

export function StatusBadge({ status }: { status: string | null }) {
  const key = status ?? "not_verified";
  const v = MAP[key] ?? {
    label: key.replace(/_/g, " "),
    cls: "text-ink2 bg-surfacealt border-border",
    Icon: DashCircleIcon,
  };
  const { label, cls, Icon } = v;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-[3px] text-12 font-medium leading-none ${cls}`}
    >
      <Icon className="h-3 w-3 shrink-0" />
      {label}
    </span>
  );
}
