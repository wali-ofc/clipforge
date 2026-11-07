import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

export function LogoMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <rect width="40" height="40" rx="11" fill="#F58A3B" />
      <rect
        x="1"
        y="1"
        width="38"
        height="38"
        rx="10"
        stroke="white"
        strokeOpacity="0.18"
        strokeWidth="1.5"
      />
      <path d="M16.2 12.6 29 19.4c.9.5.9 1.7 0 2.2l-12.8 6.8c-.9.5-2-.2-2-1.2V13.8c0-1 1.1-1.7 2-1.2Z" fill="#1A0E05" />
      <path
        d="M11.5 10.5h3.2M11.5 15.2h2.4"
        stroke="#1A0E05"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity=".55"
      />
    </svg>
  );
}

export function UploadCloudIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M7.5 18.5a4.5 4.5 0 0 1-.6-8.96 6 6 0 0 1 11.67-1.3A4 4 0 0 1 17.5 18.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M12 16.5V9.75m0 0L9.4 12.35M12 9.75l2.6 2.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function FileVideoIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M14 3.75H7.5A2.25 2.25 0 0 0 5.25 6v12A2.25 2.25 0 0 0 7.5 20.25h9A2.25 2.25 0 0 0 18.75 18V8.5L14 3.75Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M13.75 4v4.5h4.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="m10.4 11.1 4.1 2.2c.5.3.5 1 0 1.3l-4.1 2.2c-.5.3-1.1-.1-1.1-.65v-4.4c0-.55.6-.95 1.1-.65Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function ArrowRightIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M5 12h14m0 0-5.25-5.25M19 12l-5.25 5.25"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="m5 12.5 4.2 4.2L19 7"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AlertIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M12 8.5v4.25m0 3.25v.01M10.2 4.7 3.6 16.1a2 2 0 0 0 1.73 3h13.34a2 2 0 0 0 1.73-3L13.8 4.7a2.05 2.05 0 0 0-3.6 0Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function XIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="m6.5 6.5 11 11m0-11-11 11"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CopyIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <rect
        x="8.5"
        y="8.5"
        width="10.5"
        height="10.5"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M15.5 8.5V6.75A1.75 1.75 0 0 0 13.75 5h-7A1.75 1.75 0 0 0 5 6.75v7a1.75 1.75 0 0 0 1.75 1.75H8.5"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </svg>
  );
}

export function SpinnerIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M20 12a8 8 0 1 1-2.34-5.66"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function ShieldIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path
        d="M12 3.75 5.25 6.5v5.13c0 4.13 2.7 7.03 6.75 8.62 4.05-1.59 6.75-4.49 6.75-8.62V6.5L12 3.75Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="m9.2 11.9 1.9 1.9 3.7-3.7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CpuIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <rect
        x="6.5"
        y="6.5"
        width="11"
        height="11"
        rx="2.2"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M9.5 3.75v2.5m5-2.5v2.5m-5 13.5v2.5m5-2.5v2.5M3.75 9.5h2.5m-2.5 5h2.5m13.5-5h2.5m-2.5 5h2.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <rect x="9.6" y="9.6" width="4.8" height="4.8" rx="1" fill="currentColor" opacity=".45" />
    </svg>
  );
}
