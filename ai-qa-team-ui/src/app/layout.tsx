import "./globals.css";
import AuthProvider from "@/components/providers/AuthProvider";

export const metadata = {
  title: "QA Squad",
  description: "AI-powered test automation companion",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
