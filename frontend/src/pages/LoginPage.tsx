import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

function EyeIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Email ou mot de passe incorrect.");
    } finally {
      setIsSubmitting(false);
    }
  }

return (
    <main className="min-h-screen bg-mz-background text-mz-text">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl items-center px-4 py-8 sm:px-8 lg:px-12">
        <div className="grid w-full overflow-hidden rounded-2xl border border-mz-border bg-mz-card shadow-2xl lg:min-h-[620px] lg:grid-cols-2">
          <section className="relative hidden flex-col justify-between overflow-hidden bg-mz-surface p-10 lg:flex xl:p-14">
            <div
              aria-hidden="true"
              className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full border border-mz-border"
            />
            <div
              aria-hidden="true"
              className="pointer-events-none absolute -right-12 -top-12 h-56 w-56 rounded-full border border-mz-border"
            />

<div className="relative z-10 flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-mz-border bg-mz-card p-2">
                <img
                  src="/logo-mz-building.png"
                  alt="Logo MZ Building"
                  className="max-h-full max-w-full object-contain"
                />
              </div>
              <div>
                <p className="text-sm font-semibold tracking-[0.16em] text-mz-text">
                  MZ BUILDING
                </p>
                <p className="mt-1 text-xs text-mz-text-muted">MZ-SITEHUB</p>
              </div>
            </div>

<div className="relative z-10 max-w-lg py-12">
              <p className="mb-5 text-xs font-semibold uppercase tracking-[0.22em] text-mz-accent">
                Plateforme de pilotage
              </p>
              <h1 className="text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
                Vos sites,
                <br />
                votre suivi,
                <br />
                <span className="text-mz-accent">en un seul endroit.</span>
              </h1>
              <p className="mt-6 max-w-md text-sm leading-7 text-mz-text-muted">
                Retrouvez vos projets, vos étapes d’acquisition et vos informations
                opérationnelles dans un espace de travail centralisé.
              </p>
              <div className="mt-9 h-1 w-16 rounded-full bg-mz-primary" />
            </div>

<p className="relative z-10 text-xs text-mz-text-disabled">
              Un espace de travail réservé aux collaborateurs MZ Building.
            </p>
          </section>

<section className="flex items-center justify-center p-6 sm:p-10 lg:p-12">
            <div className="w-full max-w-md">
              <div className="mb-9 flex flex-col items-center text-center lg:items-start lg:text-left">
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-mz-border bg-mz-surface p-2.5 lg:hidden">
                  <img
                    src="/logo-mz-building.png"
                    alt="Logo MZ Building"
                    className="max-h-full max-w-full object-contain"
                  />
                </div>

<p className="text-xs font-semibold uppercase tracking-[0.2em] text-mz-accent">
                  MZ-SITEHUB
                </p>
                <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">
                  Bon retour
                </h2>
                <p className="mt-2 text-sm text-mz-text-muted">
                  Connectez-vous à votre espace de travail.
                </p>
              </div>

<form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label
                    htmlFor="email"
                    className="mb-2 block text-sm font-medium text-mz-text"
                  >
                    Adresse e-mail
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    placeholder="nom@entreprise.com"
                    className="w-full rounded-mz-md border border-mz-border bg-mz-input px-4 py-3 text-sm text-mz-text placeholder:text-mz-text-disabled outline-none transition focus:border-mz-primary focus:ring-2 focus:ring-mz-primary/20"
                  />
                </div>

<div>
                  <label
                    htmlFor="password"
                    className="mb-2 block text-sm font-medium text-mz-text"
                  >
                    Mot de passe
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="current-password"
                      placeholder="Saisissez votre mot de passe"
                      className="w-full rounded-mz-md border border-mz-border bg-mz-input py-3 pl-4 pr-12 text-sm text-mz-text placeholder:text-mz-text-disabled outline-none transition focus:border-mz-primary focus:ring-2 focus:ring-mz-primary/20"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      aria-label={
                        showPassword
                          ? "Masquer le mot de passe"
                          : "Afficher le mot de passe"
                      }
                      aria-pressed={showPassword}
                      className="absolute inset-y-0 right-0 flex items-center rounded-mz-md px-4 text-mz-text-muted transition hover:text-mz-text focus:outline-none focus-visible:ring-2 focus-visible:ring-mz-primary"
                    >
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>

{error && (
                  <p
                    role="alert"
                    className="rounded-mz-md border border-mz-danger/30 bg-mz-danger/10 px-4 py-3 text-sm text-mz-danger"
                  >
                    {error}
                  </p>
                )}

<button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex w-full items-center justify-center rounded-mz-md bg-mz-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-mz-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-mz-primary focus-visible:ring-offset-2 focus-visible:ring-offset-mz-card disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Connexion..." : "Se connecter"}
                </button>
              </form>

<p className="mt-8 border-t border-mz-border pt-5 text-center text-xs text-mz-text-disabled lg:text-left">
                MZ Building · Acquisition &amp; Project Management
              </p>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}