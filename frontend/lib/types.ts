// Mirrors the FastAPI response shapes (app/api/*).

export type VerificationStatus =
  | "pending" | "needs_info" | "active" | "inactive" | "error";

export interface BatchSummary {
  id: string;
  practice_name: string;
  status: string;
  appointments: number;
  needing_review: number;
}

export interface AppointmentOut {
  id: string;
  appt_time: string | null;
  patient_name: string | null;
  dob: string | null;
  payer_name: string | null;
  subscriber_id: string | null;
  payer_id: string | null;
  needs_review: boolean;
  has_required_identity: boolean;
  verification_status: string | null;
  verification_id: string | null;
}

export interface BatchDetail {
  id: string;
  status: string;
  appointments: AppointmentOut[];
}

export interface UploadResponse {
  batch_id: string;
  rows_parsed: number;
  rows_needing_review: number;
}
