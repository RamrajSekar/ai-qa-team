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
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{title}</h2>
      {description && <p className="text-gray-600">{description}</p>}

      <div>{children}</div>
    </div>
  );
}
