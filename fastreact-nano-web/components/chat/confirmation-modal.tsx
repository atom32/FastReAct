"use client"

import { AlertTriangle, Check, X } from "lucide-react"

interface ConfirmationModalProps {
  isOpen: boolean
  title: string
  description: string
  toolName?: string
  requestId?: string
  paramsSummary?: string
  onApprove: () => void
  onDeny: () => void
}

export function ConfirmationModal({
  isOpen,
  title,
  description,
  toolName,
  requestId,
  paramsSummary,
  onApprove,
  onDeny,
}: ConfirmationModalProps) {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      style={{
        background: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(8px)",
      }}
    >
      <div
        className="w-full max-w-md animate-modal-in"
        style={{
          background: `linear-gradient(135deg, var(--fr-bg-secondary), var(--fr-bg-primary))`,
          backdropFilter: "blur(20px)",
          border: `2px solid var(--fr-warning)`,
          borderRadius: "24px",
          padding: "32px",
          boxShadow: `0 20px 60px rgba(0,0,0,0.5), 0 0 30px rgba(251, 191, 36, 0.15)`,
        }}
      >
        {/* Icon */}
        <div className="mb-4 flex justify-center">
          <div
            className="flex h-14 w-14 items-center justify-center rounded-full"
            style={{
              background: `rgba(251, 191, 36, 0.15)`,
              border: `2px solid var(--fr-warning)`,
            }}
          >
            <AlertTriangle className="h-7 w-7" style={{ color: "var(--fr-warning)" }} />
          </div>
        </div>

        {/* Content */}
        <h3
          className="mb-2 text-center text-lg font-bold"
          style={{ color: "var(--fr-text-primary)" }}
        >
          {title}
        </h3>
        <p
          className="mb-4 text-center text-sm leading-relaxed"
          style={{ color: "var(--fr-text-secondary)" }}
        >
          {description}
        </p>

        <div
          className="mb-6 space-y-2 rounded-lg border p-3 text-xs"
          style={{
            borderColor: "rgba(255,255,255,0.12)",
            color: "var(--fr-text-secondary)",
          }}
        >
          <div className="flex justify-between gap-3">
            <span>Tool</span>
            <span className="min-w-0 truncate font-mono" style={{ color: "var(--fr-text-primary)" }}>
              {toolName || "-"}
            </span>
          </div>
          <div className="flex justify-between gap-3">
            <span>Request</span>
            <span className="min-w-0 truncate font-mono" style={{ color: "var(--fr-text-primary)" }}>
              {requestId || "-"}
            </span>
          </div>
          {paramsSummary && (
            <pre
              className="max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-md p-2 font-mono text-[11px]"
              style={{ background: "rgba(0,0,0,0.24)" }}
            >
              {paramsSummary}
            </pre>
          )}
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onDeny}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            style={{
              background: `rgba(239, 68, 68, 0.15)`,
              border: `2px solid var(--fr-error)`,
              color: "var(--fr-error)",
            }}
          >
            <X className="h-4 w-4" />
            Deny
          </button>
          <button
            onClick={onApprove}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            style={{
              background: `linear-gradient(135deg, #059669, #10b981)`,
              boxShadow: `0 4px 15px rgba(16, 185, 129, 0.3)`,
            }}
          >
            <Check className="h-4 w-4" />
            Approve
          </button>
        </div>
      </div>
    </div>
  )
}
