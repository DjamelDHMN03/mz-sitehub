import { Copy, ExternalLink, Pencil } from "lucide-react";
import { Link } from "react-router-dom";
import { StatusBadge } from "@/components/Badge";
import { Button } from "@/components/Button";

interface MapPopupProps {
  siteId?: string;
  code: string;
  name: string | null;
  statusLabel: string;
  statusColor: string;
  latitude: number;
  longitude: number;
  onEdit?: (siteId: string) => void;
}

export function MapPopup({
  siteId,
  code,
  name,
  statusLabel,
  statusColor,
  latitude,
  longitude,
  onEdit,
}: MapPopupProps) {
  const googleMapsUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
  const coordsText = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;

  function copyCoords() {
    navigator.clipboard.writeText(coordsText).catch(() => {
      /* silencieux : presse-papier indisponible */
    });
  }

  return (
    <div className="min-w-[210px] space-y-2 font-sans">
      <div>
        <p className="text-sm font-semibold text-mz-text">{code}</p>
        {name && <p className="text-xs text-mz-text-muted">{name}</p>}
      </div>

      <StatusBadge label={statusLabel} color={statusColor} />

      <p className="text-xs text-mz-text-muted">{coordsText}</p>
      <div className="flex flex-wrap gap-1.5 pt-1">
        {onEdit && siteId && (
          <Button size="sm" className="text-xs" onClick={() => onEdit(siteId)}>
            <Pencil size={13} /> Modifier
          </Button>
        )}
        <a href={googleMapsUrl} target="_blank" rel="noreferrer">
          <Button size="sm" variant="secondary" className="text-xs">
            <ExternalLink size={13} /> Google Maps
          </Button>
        </a>
        <Button size="sm" variant="ghost" className="text-xs" onClick={copyCoords}>
          <Copy size={13} /> Copier
        </Button>
      </div>

      {siteId && (
        <Link to={`/sites/${siteId}`} className="block text-xs text-mz-primary hover:underline">
          Ouvrir la fiche du site
        </Link>
      )}
    </div>
  );
}