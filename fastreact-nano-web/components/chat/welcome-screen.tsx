"use client"

import { Rocket, Zap, Shield, Sparkles } from "lucide-react"

interface WelcomeScreenProps {
  onSuggestion: (text: string) => void
}

const suggestions = [
  {
    icon: Zap,
    label: "Analyze code",
    prompt: "Analyze this React component for performance issues and suggest improvements",
  },
  {
    icon: Shield,
    label: "Security review",
    prompt: "Perform a security audit on my authentication flow",
  },
  {
    icon: Sparkles,
    label: "Generate ideas",
    prompt: "Brainstorm creative solutions for improving our user onboarding experience",
  },
]

export function WelcomeScreen({ onSuggestion }: WelcomeScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      {/* Hero */}
      <div
        className="animate-float mb-4 flex h-20 w-20 items-center justify-center rounded-2xl"
        style={{
          background: `linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))`,
          boxShadow: `0 0 40px var(--fr-border-glow)`,
        }}
      >
        <Rocket className="h-10 w-10 text-white" />
      </div>

      <h1
        className="mb-2 text-balance text-center font-display text-2xl font-bold tracking-wide sm:text-3xl"
        style={{
          background: `linear-gradient(135deg, var(--fr-gradient-start), var(--fr-gradient-end))`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        FastReAct Nano
      </h1>
      <p
        className="mb-10 max-w-sm text-pretty text-center text-sm leading-relaxed"
        style={{ color: "var(--fr-text-secondary)" }}
      >
        Your advanced AI agent, ready to think, plan, and execute complex tasks with precision.
      </p>

      {/* Suggestion cards */}
      <div className="grid w-full max-w-lg gap-3 sm:grid-cols-3">
        {suggestions.map((s) => (
          <button
            key={s.label}
            onClick={() => onSuggestion(s.prompt)}
            className="glass-panel group flex flex-col items-start gap-2 rounded-xl p-4 text-left transition-all duration-300 hover:-translate-y-1"
            style={{
              borderColor: "var(--fr-border-glow)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = `0 8px 30px var(--fr-border-glow)`
              e.currentTarget.style.borderColor = `var(--fr-accent-primary)`
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = "none"
              e.currentTarget.style.borderColor = `var(--fr-border-glow)`
            }}
          >
            <s.icon className="h-5 w-5" style={{ color: "var(--fr-accent-primary)" }} />
            <span
              className="text-sm font-medium"
              style={{ color: "var(--fr-text-primary)" }}
            >
              {s.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
