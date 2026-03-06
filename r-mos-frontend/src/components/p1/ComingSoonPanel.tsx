import { Hammer } from 'lucide-react'

interface ComingSoonPanelProps {
  title: string
  description: string
}

export function ComingSoonPanel({ title, description }: ComingSoonPanelProps) {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
      <div className="glass-card surface-grid max-w-xl rounded-xl p-8">
        <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl border border-primary/30 bg-primary-muted text-primary">
          <Hammer className="h-5 w-5" />
        </div>
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.3em] text-text-secondary">
          P1 Placeholder
        </p>
        <h1 className="mb-3 text-2xl font-semibold text-text-primary">{title}</h1>
        <p className="text-sm leading-7 text-text-secondary">{description}</p>
        <p className="mt-6 text-sm text-text-muted">页面建设中，将在 P2 完成。</p>
      </div>
    </div>
  )
}
