"use client";

import { useAuth } from "@/components/providers/AuthProvider";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function Topbar() {
  const { user, setAuth } = useAuth();

  const handleLogout = () => {
    // Remove cookies
    document.cookie = "access_token=; Max-Age=0; path=/";
    document.cookie = "refresh_token=; Max-Age=0; path=/";
    setAuth(null);
    window.location.href = "/";
  };

  return (
    <header className="h-16 border-b bg-white flex items-center justify-end px-6">
      <DropdownMenu>
        <DropdownMenuTrigger>
          <Avatar className="cursor-pointer">
            <AvatarFallback>
              {user?.name?.[0] ?? "U"}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>

        <DropdownMenuContent className="w-48 mr-2">
          <div className="px-3 py-2 text-sm">
            <p className="font-medium">{user?.name}</p>
            <p className="text-neutral-500">{user?.email}</p>
          </div>

          <DropdownMenuItem onClick={() => window.location.href = "/settings"}>
            Settings
          </DropdownMenuItem>

          <DropdownMenuItem onClick={handleLogout} className="text-red-600">
            Logout
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
