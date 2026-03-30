"use client";

import { type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { AuthProvider, useAuth } from "@/lib/auth";
import Sidebar from "@/components/Sidebar";

const PUBLIC_PATHS = ["/login", "/signup"];

function AuthGate({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const isPublic = PUBLIC_PATHS.includes(pathname);

    if (!isAuthenticated && !isPublic) {
      router.replace("/login");
    } else if (isAuthenticated && isPublic) {
      // Already logged in, redirect away from auth pages
      if (user && !user.onboarding_completed) {
        router.replace("/onboarding");
      } else {
        router.replace("/");
      }
    } else if (isAuthenticated && user && !user.onboarding_completed && pathname !== "/onboarding") {
      router.replace("/onboarding");
    }
  }, [isAuthenticated, isLoading, user, pathname, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-gray-400 animate-pulse">Loading...</div>
      </div>
    );
  }

  const isPublic = PUBLIC_PATHS.includes(pathname);
  const isOnboarding = pathname === "/onboarding";

  // Public pages (login/signup) — no sidebar
  if (isPublic || isOnboarding) {
    return <>{children}</>;
  }

  // Authenticated pages — with sidebar
  if (!isAuthenticated) return null;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">{children}</main>
    </div>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <AuthGate>{children}</AuthGate>
    </AuthProvider>
  );
}
