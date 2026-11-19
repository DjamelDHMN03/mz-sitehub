import { useAuth } from "@/lib/auth";
import { Button } from "@/components/Button";
import { LogOut } from "lucide-react";

export function Navbar({ title }: { title: string }) {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-mz-border bg-mz-surface px-6">
      <h1 className="text-base font-semibold text-mz-text">{title}</h1>
      <div className="flex items-center gap-4">
        {user && (
          <div className="text-right leading-tight">
            <p className="text-sm text-mz-text">
              {user.first_name ?? user.email} {user.last_name ?? ""}
            </p>
            <p className="text-xs text-mz-text-muted">{user.role_code}</p>
          </div>
        )}
        <Button variant="ghost" size="sm" onClick={logout} title="Se déconnecter">
          <LogOut size={16} />
        </Button>
      </div>
    </header>
  );
}
