"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  // base acessível + tokens shadcn
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 " +
    "ring-offset-background disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        // primário (default)
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        // novo: secundário (cinza)
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        // contornado
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        // fantasma
        ghost: "hover:bg-accent hover:text-accent-foreground",
        // novo: perigoso / destrutivo
        danger:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3 rounded-md",
        lg: "h-11 px-8 rounded-md",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        {...props} // <- mantém title, aria-label, etc.
      />
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };
