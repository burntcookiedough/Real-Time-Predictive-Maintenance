import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "critical" | "warning" | "healthy"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
    const variants = {
        default: "bg-surface-raised text-content-primary border-border-accent",
        critical: "bg-signal-critical-bg text-signal-critical border-signal-critical animate-pulse-slow",
        warning: "bg-signal-warning-bg text-signal-warning border-signal-warning",
        healthy: "bg-signal-healthy-bg text-signal-healthy border-transparent"
    };

    return (
        <div
            className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide uppercase transition-colors",
                variants[variant],
                className
            )}
            {...props}
        />
    )
}

export { Badge }
