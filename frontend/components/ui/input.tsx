import React from "react";
import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, helperText, className, ...props }, ref) => {
    return (
      <div className="flex flex-col space-y-1">
        {label && <label className="text-xs font-bold uppercase tracking-wider text-orange-500">{label}</label>}
        <input
          ref={ref}
          className={cn(
            "rounded-none border border-warm-border bg-warm-bg px-3 py-2 text-warm-text font-sans transition-all duration-100 focus:outline-none focus:border-warm-primary focus:ring-1 focus:ring-terminal-cyan disabled:opacity-50",
            className
          )}
          {...props}
        />
        {helperText && <p className="text-xs font-sans text-warm-muted">{helperText}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
