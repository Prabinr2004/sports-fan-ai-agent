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
  photo_url?: string | null;
  shirt_number?: number | null;
};

export type Fixture = {
  id: string;
  utc_date?: string | null;
  status?: string | null;
  competition?: string | null;
  home_team: TeamSummary;
  away_team: TeamSummary;
};

export type TeamStanding = {
  competition_id: string;
  competition?: string | null;
  type?: string | null;
  stage?: string | null;
  group?: string | null;
  position?: number | null;
  played?: number | null;
  won?: number | null;
  drawn?: number | null;
  lost?: number | null;
  points?: number | null;
  goals_for?: number | null;
  goals_against?: number | null;
  goal_difference?: number | null;
};

export type TeamScorer = {
  player_id: string;
  player_name?: string | null;
  goals: number;
  assists?: number | null;
  penalties?: number | null;
  played_matches?: number | null;
  competitions?: string[];
};

export type TeamHubData = {
  team: TeamSummary;
  squad: Player[];
  fixtures: Fixture[];
  recent_results?: (Fixture & {score?: {home?: number | null; away?: number | null}})[];
  standings: TeamStanding[];
  scorers: TeamScorer[];
  notices?: {
    squad?: string;
    fixtures?: string;
    recent_results?: string;
    standings?: string;
    scorers?: string;
  };
  provider_connected: boolean;
};
