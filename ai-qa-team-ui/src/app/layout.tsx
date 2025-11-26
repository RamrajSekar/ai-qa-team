import "./globals.css";
import {AuthProvider} from "@/components/providers/AuthProvider";
import AuthModal from "@/components/auth/AuthModal";

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
          <AuthModal/>
        </AuthProvider>
      </body>
    </html>
  );
}
