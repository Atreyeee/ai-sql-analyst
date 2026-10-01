import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full resize-none bg-transparent text-ivory placeholder:text-ivory-dim/60 focus-visible:outline-none",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
