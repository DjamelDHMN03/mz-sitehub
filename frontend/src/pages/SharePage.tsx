import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

interface ShareInfo {
  is_valid: boolean;
  reason: string | null;
  filenames: string[];
  site_code: string | null;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function SharePage() {
  const { token } = useParams<{ token: string }>();
  const [info, setInfo] = useState<ShareInfo | null>(null);

  useEffect(() => {
    axios.get<ShareInfo>(`${API_BASE}/shares/${token}/info`).then(({ data }) => setInfo(data));
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-mz-background px-4">
      <div className="w-full max-w-md rounded-mz-lg border border-mz-border bg-mz-card p-6 text-center">
        <img src="/logo-mz-building.png" alt="MZ Building" className="mx-auto mb-4 h-12 w-auto" />

        {!info && <p className="text-sm text-mz-text-muted">Vérification du lien...</p>}

        {info && !info.is_valid && (
          <p className="text-sm text-mz-danger">{info.reason ?? "Ce lien n'est plus valide."}</p>
        )}

        {info && info.is_valid && (
          <>
            <p className="mb-1 text-sm text-mz-text-muted">
              Documents partagés{info.site_code ? ` — site ${info.site_code}` : ""}
            </p>
            <ul className="mb-4 space-y-1 text-sm text-mz-text">
              {info.filenames.map((f) => <li key={f}>{f}</li>)}
            </ul>
            <a
              href={`${API_BASE}/shares/${token}/download`}
              className="inline-block rounded-mz-md bg-mz-primary px-4 py-2 text-sm font-medium text-white hover:bg-mz-primary-hover"
            >
              Télécharger {info.filenames.length > 1 ? "(ZIP)" : ""}
            </a>
          </>
        )}
      </div>
    </div>
  );
}
