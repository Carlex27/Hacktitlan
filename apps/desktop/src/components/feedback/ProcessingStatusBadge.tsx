import { Badge } from "@/components/ui/badge";
import { es } from "@/lib/i18n";
import type { ProcessingStatus } from "@/types";

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

const VARIANTS: Record<ProcessingStatus, BadgeVariant> = {
  loading: "secondary",
  empty: "outline",
  success: "default",
  needs_review: "outline",
  error: "destructive",
};

export interface ProcessingStatusBadgeProps {
  status: ProcessingStatus;
  className?: string;
}

export function ProcessingStatusBadge({ status, className }: ProcessingStatusBadgeProps) {
  return (
    <Badge variant={VARIANTS[status]} data-status={status} className={className}>
      {es.processingStatus[status]}
    </Badge>
  );
}
