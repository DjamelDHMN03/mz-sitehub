import { Copy, ExternalLink } from "lucide-react";
import { StatusBadge } from "@/components/Badge";
import { Button } from "@/components/Button";

interface MapPopupProps {
  code: string;
  name: string | null;
  statusLabel: string;
  statusColor: string;
  latitude: number;
  longitude: number;
}

export function MapPopup({ code, name, statusLabel, statusColor, latitude, longitude }: MapPopupProps) {
  const googleMapsUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
  const coordsText = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;

  function copyCoords() {
    navigator.clipboard.writeText(coordsText).catch(() => {
      /* silencieux : le clic reste sans effet si le presse-papier est indisponible */
    });
  }

  return (
    <div className="min-w-[200px] space-y-2 font-sans">
      <div>
        <p className="text-sm font-semibold text-mz-text">{code}</p>
        {name && <p className="text-xs text-mz-text-muted">{name}</p>}
      </div>

      <StatusBadge label={statusLabel} color={statusColor} />

      <p className="text-xs text-mz-text-muted">{coordsText}</p>

      <div className="flex gap-1.5 pt-1">
        <a href={googleMapsUrl} target="_blank" rel="noreferrer">
          <Button size="sm" variant="secondary" className="text-xs">
            <ExternalLink size={13} /> Google Maps
          </Button>
        </a>
        <Button size="sm" variant="ghost" className="text-xs" onClick={copyCoords}>
          <Copy size={13} /> Copier
        </Button>
      </div>
    </div>
  );
}
