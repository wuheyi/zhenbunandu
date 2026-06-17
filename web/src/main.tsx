import React from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpen,
  BrainCircuit,
  Eye,
  FilePenLine,
  Flag,
  Landmark,
  MapPinned,
  MessageSquareText,
  Scale,
  ScrollText,
  Shield,
  Stamp,
  Swords,
  WalletCards
} from "lucide-react";
import { api, issueDecreeStream, loadState } from "./api";
import type { CourtCase, Directive, EventItem, GameState, Gate, LogisticsRoute, Minister, Region } from "./types";
import "./styles.css";

type ModalName = "none" | "audience" | "secret" | "decree" | "report" | "court" | "history" | "debate" | "llm";
type MapMode = "north" | "city" | "logistics" | "diplomacy";

const portraitIndex: Record<string, number> = {
  li_gang: 0,
  finance_minister: 1,
  "imperial_city司": 2,
  kaifeng_prefect: 3,
  peace_chancellor: 4,
  transport_judge: 5,
  guard_representative: 0,
  jin_envoy: 4
};

function App() {
  const [state, setState] = React.useState<GameState | null>(null);
  const [modal, setModal] = React.useState<ModalName>("none");
  const [busy, setBusy] = React.useState("");
  const [error, setError] = React.useState("");
  const [selectedMinisterId, setSelectedMinisterId] = React.useState("li_gang");
  const [selectedEventId, setSelectedEventId] = React.useState("");
  const [selectedNode, setSelectedNode] = React.useState<string>("bianjing");
  const [mapMode, setMapMode] = React.useState<MapMode>("north");
  const [chatAnswer, setChatAnswer] = React.useState("");
  const [settleLog, setSettleLog] = React.useState<string[]>([]);

  const refresh = React.useCallback(async () => {
    const data = await loadState();
    setState(data);
    setSelectedEventId((current) => current || data.events.find((item) => item.status === "active")?.id || "");
  }, []);

  React.useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, [refresh]);

  const newGame = async () => {
    setBusy("重开靖康元年...");
    setError("");
    try {
      const data = await api<GameState>("/api/menu/new_game", { method: "POST" });
      setState(data);
      setModal("none");
      setChatAnswer("");
      setSettleLog([]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  };

  const selectedMinister = state?.ministers.find((minister) => minister.id === selectedMinisterId) || state?.ministers[0] || null;
  const selectedEvent = state?.events.find((item) => item.id === selectedEventId) || state?.events[0] || null;

  const openAudience = (ministerId: string) => {
    setSelectedMinisterId(ministerId);
    setChatAnswer("");
    setModal("audience");
  };

  if (!state) {
    return (
      <div className="loading-screen">
        <div className="seal-loader" />
        <div>御案铺开中...</div>
        {error && <button onClick={newGame}>建立新局</button>}
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopBar state={state} onNewGame={newGame} onLLM={() => setModal("llm")} busy={busy} />
      {error && <div className="error-banner">{error}</div>}
      <main className="war-desk">
        <aside className="left-scroll">
          <DoomClock state={state} />
          <section className="paper-panel memorial-stack">
            <PanelTitle icon={<ScrollText size={18} />} title="本月急奏" />
            {state.events.filter((event) => event.status === "active").map((event) => (
              <MemorialCard
                key={event.id}
                event={event}
                active={event.id === selectedEvent?.id}
                onClick={() => setSelectedEventId(event.id)}
                onAudience={openAudience}
              />
            ))}
          </section>
          <section className="paper-panel issue-panel">
            <PanelTitle icon={<Swords size={18} />} title="局势进度" />
            {state.issues.map((issue) => (
              <div className="issue-row" key={issue.id} title={issue.summary}>
                <div className="issue-head">
                  <span>{issue.title}</span>
                  <b>{issue.value}</b>
                </div>
                <Progress value={(issue.value + 100) / 2} tone={issue.value < -35 ? "danger" : issue.value > 10 ? "good" : "warn"} />
              </div>
            ))}
          </section>
        </aside>

        <section className="map-column">
          <div className="map-tabs" role="tablist" aria-label="地图模式">
            <button className={mapMode === "north" ? "active" : ""} onClick={() => setMapMode("north")}>
              <MapPinned size={16} /> 北方局势
            </button>
            <button className={mapMode === "city" ? "active" : ""} onClick={() => setMapMode("city")}>
              <Shield size={16} /> 汴京城防
            </button>
            <button className={mapMode === "logistics" ? "active" : ""} onClick={() => setMapMode("logistics")}>
              <WalletCards size={16} /> 粮运财税
            </button>
            <button className={mapMode === "diplomacy" ? "active" : ""} onClick={() => setMapMode("diplomacy")}>
              <Flag size={16} /> 外交勤王
            </button>
          </div>
          <MapBoard
            state={state}
            mode={mapMode}
            selectedNode={selectedNode}
            onSelect={setSelectedNode}
            selectedEvent={selectedEvent}
          />
        </section>

        <aside className="right-court">
          <section className="paper-panel selected-brief">
            <PanelTitle icon={<Eye size={18} />} title="御前摘要" />
            {selectedEvent ? (
              <div>
                <div className="brief-kind">{selectedEvent.kind}</div>
                <h2>{selectedEvent.title}</h2>
                <p>{selectedEvent.summary}</p>
                <div className="tag-line">
                  {selectedEvent.interests.map((tag) => <span key={tag}>{tag}</span>)}
                </div>
              </div>
            ) : null}
          </section>
          <section className="paper-panel court-roster">
            <PanelTitle icon={<Landmark size={18} />} title="朝臣席" />
            {state.ministers.filter((m) => m.status === "active").slice(0, 7).map((minister) => (
              <button
                key={minister.id}
                className={`minister-row ${minister.id === selectedMinisterId ? "active" : ""}`}
                onClick={() => openAudience(minister.id)}
              >
                <Portrait id={minister.id} />
                <span>
                  <b>{minister.name}</b>
                  <small>{minister.office} · {minister.stance}</small>
                </span>
              </button>
            ))}
          </section>
          <section className="paper-panel evidence-panel">
            <PanelTitle icon={<Scale size={18} />} title="证据与案件" />
            {state.evidence.length ? state.evidence.map((evidence) => (
              <div className="evidence-slip" key={evidence.id}>
                <b>{evidence.title}</b>
                <small>{evidence.kind} · 强度 {evidence.strength}</small>
              </div>
            )) : <p className="muted">尚无可公开证据。可命皇城司密查账册。</p>}
            {state.court_cases.some((item) => item.status === "ready") && (
              <button className="cinnabar small-wide" onClick={() => setModal("court")}>开殿前对质</button>
            )}
          </section>
          <WarPulsePanel state={state} />
        </aside>
      </main>

      <CommandDock
        state={state}
        onAudience={() => openAudience(selectedMinister?.id || "li_gang")}
        onDebate={() => setModal("debate")}
        onSecret={() => setModal("secret")}
        onDecree={() => setModal("decree")}
        onCourt={() => setModal("court")}
        onReport={() => setModal("report")}
        onHistory={() => setModal("history")}
      />

      {modal === "audience" && selectedMinister && (
        <AudienceModal
          minister={selectedMinister}
          answer={chatAnswer}
          busy={busy}
          onClose={() => setModal("none")}
          onAsk={async (message) => {
            setBusy("召见中...");
            setError("");
            try {
              const data = await api<any>(`/api/ministers/${encodeURIComponent(selectedMinister.id)}/chat`, {
                method: "POST",
                body: JSON.stringify({ message })
              });
              setChatAnswer(data.answer);
              setState(data.state);
            } catch (err: any) {
              setError(err.message);
            } finally {
              setBusy("");
            }
          }}
        />
      )}

      {modal === "secret" && (
        <SecretModal
          state={state}
          onClose={() => setModal("none")}
          onCreated={(next) => setState(next)}
        />
      )}

      {modal === "debate" && (
        <DebateModal
          state={state}
          onClose={() => setModal("none")}
          onState={setState}
        />
      )}

      {modal === "decree" && (
        <DecreeModal
          state={state}
          busy={busy}
          settleLog={settleLog}
          onClose={() => setModal("none")}
          onState={setState}
          onIssue={async () => {
            setBusy("月末结算");
            setSettleLog([]);
            try {
              await issueDecreeStream((event) => {
                if (event.type === "stage" || event.type === "narrative") {
                  setSettleLog((current) => [...current, event.message]);
                }
                if (event.type === "done") {
                  setState(event.payload.state);
                  setModal("report");
                }
              });
            } catch (err: any) {
              setError(err.message);
            } finally {
              setBusy("");
            }
          }}
        />
      )}

      {modal === "court" && (
        <CourtModal
          state={state}
          onClose={() => setModal("none")}
          onState={setState}
        />
      )}

      {modal === "report" && (
        <ReportModal state={state} onClose={() => setModal("none")} />
      )}

      {modal === "history" && (
        <HistoryModal state={state} onClose={() => setModal("none")} />
      )}

      {modal === "llm" && (
        <LLMModal onClose={() => setModal("none")} onRefresh={refresh} />
      )}
    </div>
  );
}

function TopBar({ state, onNewGame, onLLM, busy }: { state: GameState; onNewGame: () => void; onLLM: () => void; busy: string }) {
  return (
    <header className="top-bar">
      <div className="era-block">
        <img src="/assets/seal.svg" alt="" />
        <strong>{state.game.year_label} {state.game.month_label}</strong>
        <span>{state.game.ended ? "结局" : state.game.phase}</span>
      </div>
      <div className="metric-strip">
        {state.metrics.map((metric) => (
          <div className="metric-pill" key={metric.key}>
            <span>{metric.key}</span>
            <b>{metric.value}</b>
            {metric.last_delta !== 0 && (
              <em className={metric.last_delta > 0 ? "up" : "down"}>{metric.last_delta > 0 ? "+" : ""}{metric.last_delta}</em>
            )}
          </div>
        ))}
      </div>
      <div className="top-actions">
        <button className={`llm-btn ${state.llm_configured ? "ready" : ""}`} onClick={onLLM}>
          <BrainCircuit size={16} />
          <span>{state.llm_configured ? "模型已配" : "规则结算"}</span>
        </button>
        <button className="wood-btn" onClick={onNewGame} disabled={!!busy}>{busy || "新局"}</button>
      </div>
    </header>
  );
}

function DoomClock({ state }: { state: GameState }) {
  return (
    <section className="paper-panel doom-card">
      <PanelTitle icon={<Shield size={18} />} title="亡国倒计时" />
      <div className="doom-line"><span>金军南下</span><b>逼近黄河</b></div>
      <Progress value={state.siege.jin_pressure} tone="danger" />
      <div className="doom-grid">
        <Situation label="汴京守备" value={state.siege.city_defense} />
        <Situation label="勤王响应" value={state.siege.qinwang_response} />
        <Situation label="主和压力" value={state.siege.peace_pressure} danger />
        <Situation label="城中战意" value={state.siege.defender_will} />
      </div>
    </section>
  );
}

function Situation({ label, value, danger }: { label: string; value: number; danger?: boolean }) {
  return (
    <div className="situation">
      <span>{label}</span>
      <b className={danger && value > 50 ? "danger-text" : ""}>{value}</b>
    </div>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <span>{title}</span>
    </div>
  );
}

function MemorialCard({ event, active, onClick, onAudience }: { event: EventItem; active: boolean; onClick: () => void; onAudience: (id: string) => void }) {
  const primaryAudience = event.audiences[0] || "";
  const ministerMap: Record<string, string> = {
    "李纲": "li_gang",
    "户部尚书": "finance_minister",
    "皇城司使": "imperial_city司",
    "开封府尹": "kaifeng_prefect",
    "主和宰执": "peace_chancellor"
  };
  return (
    <article className={`memorial-card ${active ? "active" : ""}`} onClick={onClick}>
      <div className="memorial-head">
        <span>{event.kind}</span>
        <strong>{event.title}</strong>
      </div>
      <p>{event.summary}</p>
      <div className="cred-row">
        <small>急迫 {event.urgency}</small>
        <small>可信 {event.credibility}</small>
      </div>
      <div className="action-row">
        <button onClick={(e) => { e.stopPropagation(); onAudience(ministerMap[primaryAudience] || "li_gang"); }}>
          召见相关人
        </button>
      </div>
    </article>
  );
}

function MapBoard({ state, mode, selectedNode, onSelect, selectedEvent }: { state: GameState; mode: MapMode; selectedNode: string; onSelect: (id: string) => void; selectedEvent: EventItem | null }) {
  const background = mode === "city" ? "/assets/city-defense.svg" : "/assets/strategy-map.svg";
  const nodes = mode === "city" ? state.gates : state.regions;
  const selected = nodes.find((node: any) => node.id === selectedNode) || nodes[0];
  return (
    <div className="map-board">
      <img src={background} className="map-bg" alt={mode === "city" ? "汴京城防图" : "北方舆图"} />
      <svg className="route-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
        {mode === "city" ? (
          <>
            <path d="M68 18 C76 28 79 39 77 50" className="enemy-line" />
            <path d="M40 62 C48 55 55 54 64 59" className="relief-line" />
          </>
        ) : mode === "logistics" ? (
          <>
            <path d="M61 77 C61 70 60 65 58 60" className="grain-line strong" />
            <path d="M55 55 C57 58 58 60 58 60" className="grain-line" />
            <path d="M33 53 C42 55 50 58 58 60" className="relief-line muted-line" />
          </>
        ) : (
          <>
            <path d="M66 19 C62 30 58 40 55 54" className="enemy-line" />
            <path d="M72 16 C68 28 63 38 58 51" className="enemy-line thin" />
            <path d="M28 61 C39 58 48 58 58 60" className="relief-line" />
            {mode === "diplomacy" && <path d="M58 60 C63 55 68 48 72 39" className="treaty-line" />}
          </>
        )}
      </svg>
      <div className="map-markers">
        {nodes.map((node: Region | Gate) => (
          <button
            key={node.id}
            style={{ left: `${node.x}%`, top: `${node.y}%` }}
            className={`map-marker ${node.id === selected?.id ? "active" : ""}`}
            onClick={() => onSelect(node.id)}
          >
            {node.name}
          </button>
        ))}
      </div>
      <div className="node-card">
        {mode === "city" ? <GateCard gate={selected as Gate} /> : <RegionCard region={selected as Region} />}
        {mode === "logistics" && <RouteMiniList routes={state.logistics_routes || []} />}
        {mode === "diplomacy" && <DiplomacyMiniCard state={state} />}
        {selectedEvent && <p className="map-context">当前急奏：{selectedEvent.title}</p>}
      </div>
    </div>
  );
}

function RegionCard({ region }: { region: Region }) {
  return (
    <>
      <h2>{region.name}</h2>
      <p>{region.kind} · 军事压力 {region.military_pressure} · 路线风险 {region.route_risk}</p>
      <div className="mini-stats">
        <span>控制 {region.control}</span>
        <span>民心 {region.public_support}</span>
        <span>粮储 {region.grain_stock}</span>
      </div>
    </>
  );
}

function GateCard({ gate }: { gate: Gate }) {
  return (
    <>
      <h2>{gate.name}</h2>
      <p>{gate.status} · 守将 {gate.commander} · 驻守 {gate.garrison}</p>
      <div className="mini-stats">
        <span>坚固 {gate.condition}</span>
        <span>内应风险 {gate.risk}</span>
        <span>器械 {gate.equipment}</span>
      </div>
    </>
  );
}

function RouteMiniList({ routes }: { routes: LogisticsRoute[] }) {
  return (
    <div className="route-mini-list">
      {routes.map((route) => (
        <div key={route.id}>
          <b>{route.name}</b>
          <span>{route.status} · ETA {route.eta} · 风险 {route.risk} · 截留 {route.corruption}</span>
        </div>
      ))}
    </div>
  );
}

function DiplomacyMiniCard({ state }: { state: GameState }) {
  const diplomacy = state.diplomacy || {
    status: "未接触",
    current_demand: "金营尚未正式入城索约",
    demand_severity: 0,
    impatience: 0,
    leverage: 0
  };
  return (
    <div className="diplomacy-mini">
      <b>{diplomacy.status}</b>
      <p>{diplomacy.current_demand}</p>
      <div className="mini-stats">
        <span>条件 {diplomacy.demand_severity}</span>
        <span>急躁 {diplomacy.impatience}</span>
        <span>筹码 {diplomacy.leverage}</span>
      </div>
    </div>
  );
}

function CommandDock(props: {
  state: GameState;
  onAudience: () => void;
  onDebate: () => void;
  onSecret: () => void;
  onDecree: () => void;
  onCourt: () => void;
  onReport: () => void;
  onHistory: () => void;
}) {
  const readyCases = props.state.court_cases.filter((item) => item.status === "ready").length;
  return (
    <nav className="command-dock" aria-label="御案操作">
      <CommandButton icon={<MessageSquareText />} label="召见" sub="问政" onClick={props.onAudience} />
      <CommandButton icon={<Landmark />} label="朝议" sub={(props.state.court_debates || []).length ? "已有议案" : "战和"} onClick={props.onDebate} />
      <CommandButton icon={<Eye />} label="密令" sub={`${props.state.secret_orders.filter((o) => o.status === "active").length} 进行中`} onClick={props.onSecret} />
      <CommandButton icon={<Scale />} label="对质" sub={readyCases ? `${readyCases} 案可开` : "证据不足"} onClick={props.onCourt} />
      <CommandButton icon={<FilePenLine />} label="拟旨" sub={`${props.state.directives.filter((d) => d.status !== "issued").length} 道草案`} onClick={props.onDecree} />
      <button className="issue-seal" onClick={props.onDecree}>
        <Stamp size={32} />
        <span>颁诏</span>
      </button>
      <CommandButton icon={<BookOpen />} label="回奏" sub="月末" onClick={props.onReport} />
      <CommandButton icon={<ScrollText />} label="史册" sub="旧事" onClick={props.onHistory} />
    </nav>
  );
}

function CommandButton({ icon, label, sub, onClick, disabled }: { icon: React.ReactNode; label: string; sub: string; onClick?: () => void; disabled?: boolean }) {
  return (
    <button className="command-button" onClick={onClick} disabled={disabled}>
      {icon}
      <span>{label}</span>
      <small>{sub}</small>
    </button>
  );
}

function Portrait({ id }: { id: string }) {
  const index = portraitIndex[id] ?? 0;
  const col = index % 3;
  const row = Math.floor(index / 3);
  const x = col === 0 ? 0 : col === 1 ? 50 : 100;
  const y = row === 0 ? 0 : 100;
  return (
    <span
      className="portrait"
      style={{
        backgroundPosition: `${x}% ${y}%`
      }}
    />
  );
}

function Progress({ value, tone }: { value: number; tone: "danger" | "warn" | "good" }) {
  return (
    <div className={`progress ${tone}`}>
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

function AudienceModal({ minister, answer, busy, onClose, onAsk }: { minister: Minister; answer: string; busy: string; onClose: () => void; onAsk: (message: string) => void }) {
  const [message, setMessage] = React.useState("要谁办、要多少钱、几日见效？");
  return (
    <Modal title={`召见：${minister.name}`} onClose={onClose} wide>
      <div className="audience-layout">
        <div className="minister-profile">
          <Portrait id={minister.id} />
          <h2>{minister.name}</h2>
          <p>{minister.office} · {minister.stance}</p>
          <p>{minister.summary}</p>
          <div className="stat-columns">
            <span>忠诚 {minister.loyalty}</span>
            <span>能力 {minister.ability}</span>
            <span>胆略 {minister.courage}</span>
            <span>声望 {minister.prestige}</span>
          </div>
        </div>
        <div className="dialogue-paper">
          <p className="muted">可问：要谁办、要多少钱、几日见效。大臣若给出可执行方案，会入御案草案。</p>
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
          <button className="cinnabar" disabled={!!busy} onClick={() => onAsk(message)}>{busy || "问政"}</button>
          {answer && <div className="answer-block">{answer}</div>}
        </div>
      </div>
    </Modal>
  );
}

function SecretModal({ state, onClose, onCreated }: { state: GameState; onClose: () => void; onCreated: (state: GameState) => void }) {
  const [busy, setBusy] = React.useState("");
  const create = async () => {
    setBusy("密令交付...");
    try {
      await api("/api/secret_orders", {
        method: "POST",
        body: JSON.stringify({
          title: "密查禁军军饷账册",
          assignee: "皇城司使",
          content: "三日内核验户部军饷拨付、东仓出入与殿前司实发账册，勿惊动户部。",
          tags: ["禁军欠饷", "东仓", "转运财税网络"]
        })
      });
      onCreated(await loadState());
    } finally {
      setBusy("");
    }
  };
  return (
    <Modal title="密令" onClose={onClose}>
      <p>户部称饷已拨，禁军却称三月无钱。可命皇城司暗查账册，首回合结算后产出证据。</p>
      <button className="cinnabar" onClick={create} disabled={!!busy}>{busy || "交付皇城司"}</button>
      <div className="modal-list">
        {state.secret_orders.map((order) => (
          <div className="list-card" key={order.id}>
            <b>{order.title}</b>
            <small>{order.assignee} · {order.status} · 风险 {order.risk}</small>
            {order.result && <p>{order.result}</p>}
          </div>
        ))}
      </div>
    </Modal>
  );
}

function DebateModal({ state, onClose, onState }: { state: GameState; onClose: () => void; onState: (state: GameState) => void }) {
  const [busy, setBusy] = React.useState("");
  const debate = (state.court_debates || [])[0];
  const create = async () => {
    setBusy("集百官...");
    try {
      const data = await api<{ state: GameState }>("/api/court/debate", {
        method: "POST",
        body: JSON.stringify({ topic: "战和与勤王" })
      });
      onState(data.state);
    } finally {
      setBusy("");
    }
  };
  return (
    <Modal title="朝议：战和与勤王" onClose={onClose} wide>
      {debate ? (
        <div className="debate-layout">
          <section className="debate-summary">
            <h2>{debate.topic}</h2>
            <p>{debate.summary}</p>
            <div className="tag-line">
              <span>议和</span>
              <span>勤王</span>
              <span>粮价</span>
            </div>
          </section>
          <section>
            <h3>殿上发言</h3>
            <div className="modal-list">
              {debate.speakers.map((speaker) => (
                <div className="list-card speaker-card" key={speaker.name}>
                  <b>{speaker.name} · {speaker.stance}</b>
                  <p>{speaker.line}</p>
                </div>
              ))}
            </div>
          </section>
          <section>
            <h3>可执行方案</h3>
            <div className="modal-list">
              {debate.options.map((option) => (
                <div className="list-card" key={option.title}>
                  <b>{option.title}</b>
                  <p>{option.benefit}</p>
                  <small>{option.cost}</small>
                </div>
              ))}
            </div>
            <p className="muted">朝议已把三道草案放入御案，可到“拟旨”中朱批准行。</p>
          </section>
        </div>
      ) : (
        <div className="debate-empty">
          <p>金使将至、勤王未动、粮价已涨。开朝议可让李纲、主和宰执、户部、开封府同殿交锋，并生成三道草案。</p>
          <button className="cinnabar" onClick={create} disabled={!!busy}>{busy || "开朝议"}</button>
        </div>
      )}
    </Modal>
  );
}

function DecreeModal({ state, busy, settleLog, onClose, onState, onIssue }: { state: GameState; busy: string; settleLog: string[]; onClose: () => void; onState: (state: GameState) => void; onIssue: () => void }) {
  const confirm = async (directive: Directive) => {
    const data = await api<{ directives: Directive[] }>(`/api/directives/${directive.id}/confirm`, { method: "POST" });
    onState({ ...state, directives: data.directives });
  };
  return (
    <Modal title="拟旨与颁诏" onClose={onClose} wide>
      <div className="decree-grid">
        <div>
          <h3>草案</h3>
          <div className="modal-list">
            {state.directives.length ? state.directives.map((directive) => (
              <div className="list-card decree-card" key={directive.id}>
                <div className="decree-head">
                  <b>{directive.title}</b>
                  <span>{directive.status}</span>
                </div>
                <p>{directive.text}</p>
                <small>形式：{directive.form} · 目标：{directive.target} · 期限：{directive.deadline}</small>
                <small>承办：{directive.assignee} · 资源：{directive.resources} · 风险：{directive.risk}</small>
                {directive.status === "draft" && <button onClick={() => confirm(directive)}>朱批准行</button>}
                {directive.result_summary && <p className="result-text">{directive.result_summary}</p>}
              </div>
            )) : <p className="muted">尚无草案。召见李纲、户部或皇城司可生成首批草案。</p>}
          </div>
        </div>
        <div className="issue-panel-modal">
          <h3>盖印结算</h3>
          <p>颁诏会推进到下月。若本月有皇城司查账密令，将在回奏中产出“东仓副册”。</p>
          <button className="issue-large" onClick={onIssue} disabled={busy === "月末结算"}>
            <Stamp size={34} /> {busy === "月末结算" ? "结算中" : "颁诏"}
          </button>
          <div className="settle-log">
            {settleLog.map((line, index) => <p key={`${line}-${index}`}>{line}</p>)}
          </div>
        </div>
      </div>
    </Modal>
  );
}

function WarPulsePanel({ state }: { state: GameState }) {
  const diplomacy = state.diplomacy || { status: "未接触", demand_severity: 0, impatience: 0 };
  const routes = state.logistics_routes || [];
  const latestBattle = (state.battle_reports || [])[0];
  const urgentRoute = routes.find((route) => route.risk >= 45) || routes[0];
  return (
    <section className="paper-panel war-pulse">
      <PanelTitle icon={<Flag size={18} />} title="围城脉搏" />
      <div className="pulse-grid">
        <div>
          <span>金宋外交</span>
          <b>{diplomacy.status}</b>
          <small>条件 {diplomacy.demand_severity} · 急躁 {diplomacy.impatience}</small>
        </div>
        <div>
          <span>粮运焦点</span>
          <b>{urgentRoute?.name || "未设路线"}</b>
          <small>{urgentRoute ? `${urgentRoute.status} · 风险 ${urgentRoute.risk}` : "暂无"}</small>
        </div>
      </div>
      {latestBattle ? (
        <div className="battle-note">
          <b>{latestBattle.title} · {latestBattle.outcome}</b>
          <p>{latestBattle.summary}</p>
        </div>
      ) : (
        <p className="muted">尚无正式战报。若金军威压继续上升，宣化门夜攻将成为第一场检验。</p>
      )}
    </section>
  );
}

function CourtModal({ state, onClose, onState }: { state: GameState; onClose: () => void; onState: (state: GameState) => void }) {
  const ready = state.court_cases.find((item) => item.status === "ready") || state.court_cases[0];
  const judge = async (caseItem: CourtCase, judgment: string) => {
    const data = await api<{ state: GameState }>(`/api/court_cases/${caseItem.id}/judgment`, {
      method: "POST",
      body: JSON.stringify({ judgment })
    });
    onState(data.state);
  };
  return (
    <Modal title="殿前对质" onClose={onClose} wide>
      {ready ? (
        <div className="court-layout">
          <div className="case-board">
            <h2>{ready.title}</h2>
            <p>{ready.stakes}</p>
            <div className="tag-line">
              {ready.suspects.map((item) => <span key={item}>{item}</span>)}
            </div>
            {ready.result && <div className="answer-block">{ready.result}</div>}
          </div>
          <div className="evidence-rack">
            <h3>证据架</h3>
            {state.evidence.map((evidence) => (
              <div className="evidence-slip large" key={evidence.id}>
                <b>{evidence.title}</b>
                <small>{evidence.source}</small>
                <p>{evidence.risk_if_revealed}</p>
              </div>
            ))}
          </div>
          <div className="judgment-zone">
            <h3>朱批裁断</h3>
            {["申饬", "下狱追银", "抄没追赃", "戴罪核账"].map((item) => (
              <button className="cinnabar" key={item} disabled={ready.status === "judged"} onClick={() => judge(ready, item)}>{item}</button>
            ))}
          </div>
        </div>
      ) : (
        <p>尚无可对质案件。先用密令取得证据。</p>
      )}
    </Modal>
  );
}

function ReportModal({ state, onClose }: { state: GameState; onClose: () => void }) {
  const report = state.reports[0];
  const latestBattle = (state.battle_reports || [])[0];
  return (
    <Modal title="月末回奏" onClose={onClose} wide>
      {report ? (
        <div className="report-body">
          <h2>{report.title}</h2>
          <p className="report-summary">{report.summary}</p>
          {state.game.ended ? <div className="ending-banner">{state.game.ending}</div> : null}
          <div className="report-grid">
            <section>
              <h3>大事时间线</h3>
              {report.timeline.map((line) => <p key={line}>· {line}</p>)}
            </section>
            <section>
              <h3>诏令执行</h3>
              {report.directives.map((item) => (
                <div className="list-card" key={item.title}>
                  <b>{item.title}</b>
                  <p>{item.result}</p>
                </div>
              ))}
            </section>
            <section>
              <h3>下月三急</h3>
              {report.warnings.map((line) => <p key={line}>· {line}</p>)}
            </section>
            <section>
              <h3>指标变化</h3>
              <div className="delta-list">
                {Object.entries(report.metrics_delta).map(([key, value]) => (
                  <span key={key} className={value >= 0 ? "delta-up" : "delta-down"}>{key} {value >= 0 ? "+" : ""}{value}</span>
                ))}
              </div>
            </section>
            {latestBattle ? (
              <section className="battle-report-card">
                <h3>城防战报</h3>
                <b>{latestBattle.title} · {latestBattle.outcome}</b>
                <p>{latestBattle.summary}</p>
                <small>{latestBattle.reasons.join(" / ")}</small>
              </section>
            ) : null}
          </div>
        </div>
      ) : <p>尚未有月末回奏。先颁诏推进一回合。</p>}
    </Modal>
  );
}

function HistoryModal({ state, onClose }: { state: GameState; onClose: () => void }) {
  return (
    <Modal title="史册" onClose={onClose}>
      <div className="modal-list">
        {state.memories.map((memory) => (
          <div className="list-card" key={memory.id}>
            <b>{memory.title}</b>
            <small>第 {memory.turn} 回合 · {memory.sentiment}</small>
            <p>{memory.outcome}</p>
          </div>
        ))}
      </div>
    </Modal>
  );
}

function LLMModal({ onClose, onRefresh }: { onClose: () => void; onRefresh: () => Promise<void> }) {
  const [baseUrl, setBaseUrl] = React.useState("https://api.deepseek.com");
  const [model, setModel] = React.useState("deepseek-v4-flash");
  const [apiKey, setApiKey] = React.useState("");
  const [busy, setBusy] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [ok, setOk] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    api<any>("/api/menu/status")
      .then((status) => {
        if (status.llm?.base_url) setBaseUrl(status.llm.base_url);
        if (status.llm?.model) setModel(status.llm.model);
      })
      .catch(() => undefined);
  }, []);

  const save = async () => {
    setBusy("保存中...");
    setMessage("");
    await api("/api/menu/llm", {
      method: "POST",
      body: JSON.stringify({ base_url: baseUrl, model, api_key: apiKey })
    });
    setApiKey("");
    await onRefresh();
    setBusy("");
    setMessage("模型配置已保存。");
  };

  const test = async () => {
    setBusy("测试中...");
    setMessage("");
    setOk(null);
    try {
      const result = await api<any>("/api/menu/llm/test", { method: "POST" });
      setOk(result.ok);
      setMessage(result.ok ? result.sample : result.error || result.sample);
    } catch (err: any) {
      setOk(false);
      setMessage(err.message);
    } finally {
      setBusy("");
      await onRefresh();
    }
  };

  return (
    <Modal title="LLM 配置" onClose={onClose}>
      <div className="llm-form">
        <label>
          <span>Base URL</span>
          <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} spellCheck={false} />
        </label>
        <label>
          <span>Model</span>
          <input value={model} onChange={(event) => setModel(event.target.value)} spellCheck={false} />
        </label>
        <label>
          <span>API Key</span>
          <input
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            type="password"
            placeholder="保存后不回显"
            spellCheck={false}
          />
        </label>
        <div className="llm-actions">
          <button className="cinnabar" disabled={!!busy} onClick={save}>{busy === "保存中..." ? busy : "保存"}</button>
          <button disabled={!!busy} onClick={test}>{busy === "测试中..." ? busy : "测试连接"}</button>
        </div>
        {message && <div className={`llm-result ${ok === false ? "bad" : ok ? "good" : ""}`}>{message}</div>}
        <p className="muted">无 key 时游戏完整使用规则层和固定模板；有 key 时用于召见口吻与月末回奏润色。</p>
      </div>
    </Modal>
  );
}

function Modal({ title, children, onClose, wide }: { title: string; children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section className={`modal-paper ${wide ? "wide" : ""}`} onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <h1>{title}</h1>
          <button onClick={onClose}>退下</button>
        </div>
        {children}
      </section>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
