import React from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
}

export function Button({ variant = "primary", className, children, ...props }: ButtonProps) {
  const baseStyles = "inline-flex items-center justify-center rounded-none border border-transparent text-sm font-bold uppercase tracking-wider transition-all duration-100 focus:outline-none disabled:opacity-50 disabled:pointer-events-none active:scale-95";
  
  const variants = {
    primary: "bg-[#ffb000] text-black hover:bg-[#ffc840] shadow-none",
    secondary: "bg-[#00e5ff] text-black hover:bg-[#50eeff] shadow-none",
    outline: "border-[#ffb000] text-[#ffb000] bg-warm-bg hover:bg-[#ffb000] hover:text-black",
    ghost: "bg-transparent hover:bg-warm-surface text-warm-text hover:text-warm-text",
  };

  return (
    <button 
      className={cn(baseStyles, variants[variant], "px-5 py-2.5", className)} 
      {...props}
    >
      {children}
    </button>
  );
}
