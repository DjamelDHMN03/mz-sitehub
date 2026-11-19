export interface SiteListItem {
  id: string;
  code: string;
  name: string | null;
  wilaya_id: number | null;
  status_id: number;
  priority: number;
  latitude: number | null;
  longitude: number | null;
  is_favorite: boolean;
}

export interface SiteListResponse {
  items: SiteListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserPublic {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role_code: "ADMIN" | "MANAGER" | "ACQUISITION" | "LECTURE";
  is_active: boolean;
}
