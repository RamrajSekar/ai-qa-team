"use client";

export default function StepLayout({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="onboarding-step-content">
      <h2>{title}</h2>
      {description && <p>{description}</p>}

      <div>{children}</div>
    </div>
  );
}
