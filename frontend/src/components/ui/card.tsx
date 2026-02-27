import * as React from "react"
import { cn } from "@/lib/utils"

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
        <div
            ref={ref}
            className={cn("rounded-md border border-border-subtle bg-surface text-content-primary shadow-industrial", className)}
            {...props}
        />
    )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
        <div
            ref={ref}
            className={cn("flex flex-row items-center justify-between space-y-0 pb-4 pt-5 px-6 font-semibold uppercase tracking-wide text-sm text-content-secondary border-b border-border-subtle", className)}
            {...props}
        />
    )
)
CardHeader.displayName = "CardHeader"

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
        <div ref={ref} className={cn("p-6 pt-0 mt-4", className)} {...props} />
    )
)
CardContent.displayName = "CardContent"

export { Card, CardHeader, CardContent }
