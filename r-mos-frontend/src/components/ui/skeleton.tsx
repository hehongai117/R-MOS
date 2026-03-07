import { cn } from '@/lib/utils'

function Skeleton({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn(
                'animate-pulse rounded-md bg-bg-elevated/60',
                className
            )}
            {...props}
        />
    )
}

/** Page-level skeleton with header + content cards */
function PageSkeleton() {
    return (
        <div className="space-y-6 animate-fade-in">
            {/* header skeleton */}
            <div className="space-y-2">
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-7 w-48" />
                <Skeleton className="h-4 w-64" />
            </div>
            {/* data cards row */}
            <div className="grid gap-4 xl:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-24 rounded-xl" />
                ))}
            </div>
            {/* content area */}
            <Skeleton className="h-64 rounded-xl" />
            <Skeleton className="h-40 rounded-xl" />
        </div>
    )
}

/** Single card skeleton */
function CardSkeleton({ className }: { className?: string }) {
    return (
        <div className={cn('glass-card rounded-xl p-5 space-y-4', className)}>
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
        </div>
    )
}

export { Skeleton, PageSkeleton, CardSkeleton }
