export type Metric = {
  key: string;
  value: number;
  last_delta: number;
};

export type GameHeader = {
  year_label: string;
  month_label: string;
  turn: number;
  phase: string;
  ended: number;
  ending: string;
};

export type SiegeState = {
  city_defense: number;
  defender_will: number;
  gate_risk: number;
  fire_risk: number;
  peace_pressure: number;
  jin_pressure: number;
  qinwang_response: number;
  grain_price: number;
};

export type DiplomacyState = {
  demand_severity: number;
  trust: number;
  impatience: number;
  internal_tension: number;
  leverage: number;
  current_demand: string;
  status: string;
};

export type DiplomacyOption = {
  action: string;
  title: string;
  intent: string;
  cost: string;
  benefit: string;
  risk: string;
  effects: string[];
  available: boolean;
  disabled_reason: string;
};

export type EventItem = {
  id: string;
  title: string;
  kind: string;
  summary: string;
  urgency: number;
  severity: number;
  credibility: number;
  interests: string[];
  audiences: string[];
  actions: string[];
  status: string;
  read: number;
  focus: number;
};

export type Issue = {
  id: string;
  title: string;
  value: number;
  assignee: string;
  status: string;
  summary: string;
};

export type Minister = {
  id: string;
  name: string;
  office: string;
  group_name: string;
  stance: string;
  loyalty: number;
  ability: number;
  integrity: number;
  courage: number;
  prestige: number;
  status: string;
  summary: string;
  skill: string;
  portrait: string;
};

export type Faction = {
  id: string;
  name: string;
  influence: number;
  affinity: number;
  damage: number;
  backlash: number;
  fear: number;
  summary: string;
};

export type FactionClock = {
  id: string;
  title: string;
  faction_id: string;
  value: number;
  stage: number;
  trigger: string;
  effect: string;
  mitigation: string;
  status: string;
  last_delta: number;
};

export type Region = {
  id: string;
  name: string;
  kind: string;
  control: number;
  public_support: number;
  unrest: number;
  tax_capacity: number;
  remittance_rate: number;
  grain_stock: number;
  military_pressure: number;
  route_risk: number;
  gentry_resistance: number;
  x: number;
  y: number;
};

export type Army = {
  id: string;
  name: string;
  commander: string;
  location: string;
  manpower: number;
  morale: number;
  training: number;
  equipment: number;
  supply: number;
  arrears: number;
  loyalty: number;
  mobility: number;
  stance: string;
};

export type Gate = {
  id: string;
  name: string;
  condition: number;
  garrison: number;
  commander: string;
  risk: number;
  equipment: number;
  x: number;
  y: number;
  status: string;
};

export type LogisticsRoute = {
  id: string;
  name: string;
  origin: string;
  destination: string;
  capacity: number;
  risk: number;
  delay: number;
  controller: string;
  corruption: number;
  escort: number;
  status: string;
  eta: number;
  current_load: number;
  nodes: RouteNode[];
  merchant_credit: number;
  blocked_nodes: number;
};

export type RouteNode = {
  id: string;
  route_id: string;
  name: string;
  kind: string;
  stage: string;
  risk: number;
  progress: number;
  controller: string;
  status: string;
  effect: string;
  action_hint: string;
  x: number;
  y: number;
  last_delta: number;
};

export type Directive = {
  id: number;
  title: string;
  text: string;
  form: string;
  domain: string;
  target: string;
  assignee: string;
  resources: string;
  deadline: string;
  risk: string;
  status: string;
  created_turn: number;
  result_summary: string;
};

export type SecretOrder = {
  id: number;
  title: string;
  assignee: string;
  content: string;
  tags: string[];
  due_turn: number;
  secrecy: number;
  risk: number;
  progress: number;
  status: string;
  result: string;
  created_turn: number;
};

export type Evidence = {
  id: string;
  title: string;
  kind: string;
  strength: number;
  reliability: number;
  source: string;
  implicated: string[];
  usable_in_court: boolean;
  risk_if_revealed: string;
  status: string;
  created_turn: number;
};

export type CourtCase = {
  id: string;
  title: string;
  suspects: string[];
  evidence_ids: string[];
  stakes: string;
  public_pressure: number;
  risk: number;
  status: string;
  result: string;
  created_turn: number;
};

export type TurnReport = {
  id: number;
  turn: number;
  title: string;
  summary: string;
  narrative: string;
  metrics_delta: Record<string, number>;
  timeline: string[];
  directives: Array<{ title: string; result: string }>;
  warnings: string[];
  created_at: string;
};

export type BattleReport = {
  id: number;
  turn: number;
  title: string;
  summary: string;
  outcome: string;
  reasons: string[];
  losses: Record<string, string>;
  changes: Record<string, number>;
  created_at: string;
};

export type CourtDebate = {
  id: number;
  turn: number;
  topic: string;
  summary: string;
  options: Array<{ title: string; benefit: string; cost: string }>;
  speakers: Array<{ name: string; stance: string; line: string }>;
  status: string;
  created_at: string;
};

export type Ledger = {
  id: number;
  turn: number;
  account: string;
  delta: number;
  balance_after: number;
  category: string;
  reason: string;
  source: string;
  visibility: string;
};

export type Memory = {
  id: number;
  subject_type: string;
  subject_id: string;
  turn: number;
  title: string;
  cause: string;
  process: string;
  outcome: string;
  sentiment: string;
  importance: number;
  tags: string;
};

export type GuidanceTip = {
  title: string;
  body: string;
  action: string;
  target: string;
};

export type Guidance = {
  stage: string;
  priority: string;
  tips: GuidanceTip[];
  risk_flags: string[];
};

export type Postmortem = {
  status: string;
  ending?: string;
  reasons: string[];
  recommendations: string[];
};

export type GameState = {
  game: GameHeader;
  metrics: Metric[];
  siege: SiegeState;
  diplomacy: DiplomacyState;
  diplomacy_options: DiplomacyOption[];
  events: EventItem[];
  issues: Issue[];
  ministers: Minister[];
  factions: Faction[];
  faction_clocks: FactionClock[];
  regions: Region[];
  armies: Army[];
  gates: Gate[];
  logistics_routes: LogisticsRoute[];
  directives: Directive[];
  secret_orders: SecretOrder[];
  evidence: Evidence[];
  court_cases: CourtCase[];
  reports: TurnReport[];
  battle_reports: BattleReport[];
  court_debates: CourtDebate[];
  ledger: Ledger[];
  memories: Memory[];
  llm_configured: boolean;
  guidance: Guidance;
  postmortem: Postmortem;
};
