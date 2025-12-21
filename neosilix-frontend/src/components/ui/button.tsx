"use client";

import React from "react";
import clsx from "clsx";

type ButtonVariant = "primary" | "outline" | "ghost";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  children: React.ReactNode;
}

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  children,
  className,
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center rounded-md font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";

  const variantStyles = {
    primary:
      "bg-cyan-600 text-white hover:bg-cyan-700 focus:ring-cyan-500",
    outline:
      "border border-cyan-600 text-cyan-600 hover:bg-cyan-600 hover:text-white focus:ring-cyan-500",
    ghost:
      "bg-transparent text-cyan-600 hover:bg-cyan-100 focus:ring-cyan-500",
  };

  return (
    <button
      className={clsx(baseStyles, variantStyles[variant], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin mr-2 h-5 w-5 text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z"
          ></path>
        </svg>
      )}
      {children}
    </button>
  );
}
