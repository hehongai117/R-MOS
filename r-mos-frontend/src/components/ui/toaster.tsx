import { Toaster as Sonner } from 'sonner'

export function Toaster() {
  return (
    <Sonner
      position="top-right"
      richColors
      expand={false}
      toastOptions={{
        classNames: {
          toast: '!border-border-default !bg-bg-overlay !text-text-primary',
          description: '!text-text-secondary',
          actionButton: '!bg-primary !text-text-primary',
          cancelButton: '!bg-bg-surface !text-text-primary',
        },
      }}
    />
  )
}
