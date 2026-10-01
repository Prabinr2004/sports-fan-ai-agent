export type TeamSummary = {
  id: string;
  name: string;
  short_name?: string | null;
  tla?: string | null;
  country?: string | null;
  league_name?: string | null;
  crest_url?: string | null;
  venue?: string | null;
  founded?: number | null;
  club_colors?: string | null;
  website?: string | null;
};

export type Player = {
  id: string;
  name: string;
  position?: string | null;
  date_of_birth?: string | null;
  nationality?: string | null;
};

export type Fixture = {
  id: string;
  utc_date?: string | null;
  status?: string | null;
  competition?: string | null;
  home_team: TeamSummary;
  away_team: TeamSummary;
};

export type TeamHubData = {
  team: TeamSummary;
  squad: Player[];
  fixtures: Fixture[];
  provider_connected: boolean;
};
