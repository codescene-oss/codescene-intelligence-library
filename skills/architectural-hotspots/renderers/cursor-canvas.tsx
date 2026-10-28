import { Grid, H1, H2, Stack, Text, useHostTheme, useState } from "cursor/canvas";

// ---------------------------------------------------------------------------
// Report data: the only project-specific part of this canvas.
// Every value must come from CodeScene's MCP tools: explore_project_components, explore_project_files
// and estimate_engineering_outcomes. The shape is also published as report-data.schema.json.
// ---------------------------------------------------------------------------

type Range = { lower: number; upper: number };
type TrendInterpretation = { direction: "improving" | "declining" | "steady"; pace: "slow" | "fast" | null };

type ComponentData = {
  name: string;
  health: number;
  hotspotHealth: number | null;
  trend?: TrendInterpretation;
  changes: number;
  linesOfCode: number;
  files: number;
  hotspots: number;
  upliftTargets: number;
  worstFile?: { path: string; health: number };
};

type Outcome = { scope: string; baseline: number; target: number; defects: Range; developmentTime: Range; productivity: Range };

type ReportData = {
  project: { name: string; source: string };
  components: ComponentData[];
  outcomes: Outcome[];
  team?: { developers: number; hoursPerWeek: number; weeksPerYear: number };
};

// {{REPORT_DATA}}: replace the stub below with a ReportData object built from the project's CodeScene data.
// Keep everything outside this block unchanged.
const report: ReportData = {} as ReportData;
// {{/REPORT_DATA}}

// ---------------------------------------------------------------------------
// Generic layout below: no project-specific values.
// ---------------------------------------------------------------------------

const { project, components, outcomes } = report;

const healthyThreshold = 9;
const optimal = 10;

// CodeScene design system colours (reborn-ui/src/index.css). Alpha suffixes keep tints readable in light and dark mode.
const codescene = {
  conditionBad: "#ff0004",
  conditionWarn: "#ff9300",
  conditionGood: "#26a65b",
  optimal: "#0074e0",
  primaryLight: "#003d7a",
  primaryDark: "#5cb0ff",
  warnTint: "#ff930024",
  goodTint: "#26a65b14",
  brandTint: "#1f53e014",
};

function useCodeScenePrimary() {
  const theme = useHostTheme();
  return theme.kind.includes("light") ? codescene.primaryLight : codescene.primaryDark;
}

const dotColour = (health: number) =>
  health >= optimal ? codescene.optimal : health >= healthyThreshold ? codescene.conditionGood : codescene.conditionWarn;

// ---------------------------------------------------------------------------
// Trend: the component's averageCodeHealth.trend (direction and pace) from the components inventory
// ---------------------------------------------------------------------------

type Trend = "improving" | "declining" | "steady";

const trendOf = (c: ComponentData): Trend => c.trend?.direction ?? "steady";

const trendColour: Record<Trend, string> = {
  improving: codescene.conditionGood,
  declining: codescene.conditionBad,
  steady: "",
};

const trendText = (c: ComponentData) => {
  const trend = trendOf(c);
  if (trend === "steady") return c.trend ? "Steady" : "Not enough history";
  return `${trend === "improving" ? "▲ Improving" : "▼ Declining"}${c.trend?.pace ? `, ${c.trend.pace}` : ""}`;
};

const trendGlyph = { length: 24, gap: 5, maxRise: 14 };

function trendSegment(cx: number, cy: number, r: number, c: ComponentData) {
  const magnitude = c.trend?.pace === "fast" ? trendGlyph.maxRise : trendGlyph.maxRise / 2;
  const rise = trendOf(c) === "improving" ? magnitude : -magnitude;
  const x2 = cx - r - trendGlyph.gap;
  return { x1: x2 - trendGlyph.length, y1: cy + rise / 2, x2, y2: cy - rise / 2 };
}

// ---------------------------------------------------------------------------
// Quadrant model (Gartner PAID: impact = change activity, risk = low Code Health)
// ---------------------------------------------------------------------------

type QuadrantId = "address" | "plan" | "delay" | "ignore";

const quadrants: Record<QuadrantId, { name: string; action: string; description: string }> = {
  address: {
    name: "Address",
    action: "Prioritized uplift",
    description:
      "Unhealthy components where much of the development happens. The debt taxes most delivery work, so plan architectural refactoring here first.",
  },
  plan: {
    name: "Plan",
    action: "Maintain",
    description: "Healthy, busy components. Guard them with Code Health quality gates so debt doesn't creep in.",
  },
  delay: {
    name: "Delay",
    action: "Monitor",
    description: "Unhealthy but stable components. Revisit if development shifts there.",
  },
  ignore: {
    name: "Ignore",
    action: "No action",
    description: "Healthy and quiet components. Leave them as they are.",
  },
};

const median = (values: number[]) => {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};

const activityThreshold = Math.round(median(components.map((c) => c.changes)));

function quadrantOf({ changes, health }: ComponentData): QuadrantId {
  const active = changes >= activityThreshold;
  const healthy = health >= healthyThreshold;
  if (active) return healthy ? "plan" : "address";
  return healthy ? "ignore" : "delay";
}

// ---------------------------------------------------------------------------
// Chart geometry
// ---------------------------------------------------------------------------

const width = 900;
const height = 520;
const margin = { left: 60, right: 24, top: 20, bottom: 56 };
const plotWidth = width - margin.left - margin.right;
const plotHeight = height - margin.top - margin.bottom;

const xMin = Math.pow(10, Math.floor(Math.log10(Math.min(...components.map((c) => c.changes)) / 1.5)));
const xMax = Math.pow(10, Math.ceil(Math.log10(Math.max(...components.map((c) => c.changes)) * 1.5)));
const yMin = Math.floor(Math.min(...components.map((c) => c.health)) - 0.5);
const yMax = optimal;

const xTicks = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000].filter((t) => t >= xMin && t <= xMax);
const yTicks = Array.from({ length: Math.round((yMax - yMin) * 2) + 1 }, (_, i) => yMin + i * 0.5);

const xScale = (changes: number) =>
  margin.left + ((Math.log10(changes) - Math.log10(xMin)) / (Math.log10(xMax) - Math.log10(xMin))) * plotWidth;
const yScale = (health: number) => margin.top + ((yMax - health) / (yMax - yMin)) * plotHeight;

const largestComponent = Math.max(...components.map((c) => c.linesOfCode));
const bubbleRadius = (linesOfCode: number) => 6 + Math.sqrt(linesOfCode / largestComponent) * 14;

const diamondPath = (cx: number, cy: number, r: number) =>
  `M ${cx} ${cy - r} L ${cx + r} ${cy} L ${cx} ${cy + r} L ${cx - r} ${cy} Z`;

type Box = { x1: number; y1: number; x2: number; y2: number };

const overlaps = (a: Box, b: Box) => a.x1 < b.x2 && b.x1 < a.x2 && a.y1 < b.y2 && b.y1 < a.y2;

function placeLabels<T extends ComponentData & { cx: number; cy: number; r: number }>(points: T[]) {
  const obstacles: Box[] = points.map((p) => {
    const trendWidth = trendOf(p) === "steady" ? 0 : trendGlyph.gap + trendGlyph.length;
    const halfHeight = trendOf(p) === "steady" ? p.r : Math.max(p.r, trendGlyph.maxRise / 2);
    return { x1: p.cx - p.r - trendWidth, y1: p.cy - halfHeight, x2: p.cx + p.r, y2: p.cy + halfHeight };
  });
  const placed: Box[] = [];
  return points.map((p) => {
    const w = p.name.length * 6.4;
    const h = 13;
    const candidates = [
      { x: p.cx + p.r + 5, y: p.cy + 4, anchor: "start" as const },
      { x: p.cx - p.r - 5, y: p.cy + 4, anchor: "end" as const },
      { x: p.cx, y: p.cy - p.r - 6, anchor: "middle" as const },
      { x: p.cx, y: p.cy + p.r + 14, anchor: "middle" as const },
    ];
    const boxOf = (c: (typeof candidates)[number]): Box => {
      const x1 = c.anchor === "start" ? c.x : c.anchor === "end" ? c.x - w : c.x - w / 2;
      return { x1, y1: c.y - h + 3, x2: x1 + w, y2: c.y + 3 };
    };
    const inside = (b: Box) => b.x1 >= margin.left && b.x2 <= width - margin.right && b.y1 >= margin.top;
    const own = obstacles[points.indexOf(p)];
    const choice =
      candidates.find((c) => {
        const b = boxOf(c);
        return inside(b) && !placed.some((o) => overlaps(o, b)) && !obstacles.some((o) => o !== own && overlaps(o, b));
      }) ?? candidates[0];
    placed.push(boxOf(choice));
    return { ...p, label: choice };
  });
}

function QuadrantChart() {
  const theme = useHostTheme();
  const primary = useCodeScenePrimary();

  const splitX = xScale(activityThreshold);
  const splitY = yScale(healthyThreshold);
  const left = margin.left;
  const right = margin.left + plotWidth;
  const top = margin.top;
  const bottom = margin.top + plotHeight;

  const regions: { id: QuadrantId; x: number; y: number; w: number; h: number; anchor: "start" | "end" }[] = [
    { id: "ignore", x: left, y: top, w: splitX - left, h: splitY - top, anchor: "start" },
    { id: "plan", x: splitX, y: top, w: right - splitX, h: splitY - top, anchor: "end" },
    { id: "delay", x: left, y: splitY, w: splitX - left, h: bottom - splitY, anchor: "start" },
    { id: "address", x: splitX, y: splitY, w: right - splitX, h: bottom - splitY, anchor: "end" },
  ];

  const points = [...components]
    .sort((a, b) => b.linesOfCode - a.linesOfCode)
    .map((c) => ({ ...c, cx: xScale(c.changes), cy: yScale(c.health), r: bubbleRadius(c.linesOfCode) }));
  const labelled = placeLabels(points);
  const [hovered, setHovered] = useState<string | null>(null);
  const active = labelled.find((c) => c.name === hovered);

  return (
    <div style={{ position: "relative" }}>
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto", display: "block" }}>
      {regions.map((r) => (
        <g key={r.id}>
          <rect
            x={r.x}
            y={r.y}
            width={r.w}
            height={r.h}
            fill={r.id === "address" ? codescene.warnTint : r.id === "plan" ? codescene.goodTint : "transparent"}
          />
          <text
            x={r.anchor === "start" ? r.x + 10 : r.x + r.w - 10}
            y={r.id === "delay" || r.id === "address" ? r.y + r.h - 26 : r.y + 20}
            textAnchor={r.anchor}
            fontSize={14}
            fontWeight={700}
            letterSpacing={0.5}
            fill={r.id === "address" ? codescene.conditionWarn : r.id === "plan" ? codescene.conditionGood : theme.text.secondary}
          >
            {quadrants[r.id].name.toUpperCase()}
          </text>
          <text
            x={r.anchor === "start" ? r.x + 10 : r.x + r.w - 10}
            y={r.id === "delay" || r.id === "address" ? r.y + r.h - 10 : r.y + 36}
            textAnchor={r.anchor}
            fontSize={12}
            fill={theme.text.tertiary}
          >
            {quadrants[r.id].action}
          </text>
        </g>
      ))}

      {yTicks.map((t) => (
        <g key={`y${t}`}>
          <line x1={left} x2={right} y1={yScale(t)} y2={yScale(t)} stroke={theme.stroke.tertiary} />
          <text x={left - 8} y={yScale(t) + 4} textAnchor="end" fontSize={11} fill={theme.text.tertiary}>
            {t.toFixed(1)}
          </text>
        </g>
      ))}
      {xTicks.map((t) => (
        <g key={`x${t}`}>
          <line x1={xScale(t)} x2={xScale(t)} y1={top} y2={bottom} stroke={theme.stroke.tertiary} />
          <text x={xScale(t)} y={bottom + 16} textAnchor="middle" fontSize={11} fill={theme.text.tertiary}>
            {t}
          </text>
        </g>
      ))}

      <line x1={splitX} x2={splitX} y1={top} y2={bottom} stroke={primary} strokeWidth={1.5} strokeDasharray="6 4" />
      <line x1={left} x2={right} y1={splitY} y2={splitY} stroke={primary} strokeWidth={1.5} strokeDasharray="6 4" />
      <rect x={left} y={top} width={plotWidth} height={plotHeight} fill="none" stroke={theme.stroke.secondary} />

      {labelled.map((c) => {
        if (trendOf(c) === "steady") return null;
        const s = trendSegment(c.cx, c.cy, c.r, c);
        const colour = trendColour[trendOf(c)];
        return (
          <g key={`trend-${c.name}`} pointerEvents="none">
            <line x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} stroke={theme.bg.editor} strokeWidth={6} strokeLinecap="round" />
            <line
              x1={s.x1}
              y1={s.y1}
              x2={s.x2}
              y2={s.y2}
              stroke={colour}
              strokeWidth={2.5}
              strokeLinecap="round"
            />
            <circle cx={s.x1} cy={s.y1} r={2.5} fill={theme.bg.editor} stroke={colour} strokeWidth={1.5} />
          </g>
        );
      })}
      {labelled.map((c) => {
        const isHovered = hovered === c.name;
        const hoverProps = {
          onMouseEnter: () => setHovered(c.name),
          onMouseLeave: () => setHovered((current) => (current === c.name ? null : current)),
          style: { cursor: "pointer" },
        };
        if (quadrantOf(c) === "address") {
          return (
            <g key={c.name} {...hoverProps}>
              <circle
                cx={c.cx}
                cy={c.cy}
                r={c.r + 7}
                fill={codescene.warnTint}
                stroke={codescene.conditionWarn}
                strokeOpacity={isHovered ? 1 : 0.5}
              />
              <path
                d={diamondPath(c.cx, c.cy, c.r)}
                fill={codescene.conditionWarn}
                stroke={isHovered ? theme.text.primary : theme.bg.editor}
                strokeWidth={1.5}
              />
            </g>
          );
        }
        return (
          <circle
            key={c.name}
            {...hoverProps}
            cx={c.cx}
            cy={c.cy}
            r={c.r}
            fill={dotColour(c.health)}
            fillOpacity={isHovered ? 1 : 0.85}
            stroke={isHovered ? theme.text.primary : theme.bg.editor}
            strokeWidth={1.5}
          />
        );
      })}
      {labelled.map((c) => (
        <text
          key={`label-${c.name}`}
          pointerEvents="none"
          x={c.label.x}
          y={c.label.y}
          textAnchor={c.label.anchor}
          fontSize={11}
          fontWeight={quadrantOf(c) === "address" ? 600 : 400}
          fill={quadrantOf(c) === "address" ? theme.text.primary : theme.text.secondary}
        >
          {c.name}
        </text>
      ))}

      <text x={left + plotWidth / 2} y={height - 12} textAnchor="middle" fontSize={12} fill={theme.text.secondary}>
        Change activity: commits to the component's files (log scale) → more relevant
      </text>
      <text
        x={16}
        y={top + plotHeight / 2}
        textAnchor="middle"
        fontSize={12}
        fill={theme.text.secondary}
        transform={`rotate(-90 16 ${top + plotHeight / 2})`}
      >
        Average Code Health (1–10) → healthier
      </text>
    </svg>
    {active && <ComponentTooltip component={active} />}
    </div>
  );
}

function ComponentTooltip({ component: c }: { component: ComponentData & { cx: number; cy: number; r: number } }) {
  const theme = useHostTheme();
  const below = c.cy - c.r < 140;
  const rows: [string, string, string | undefined][] = [
    ["Code Health", c.health.toFixed(2), dotColour(c.health)],
    [
      "12-month trend",
      trendText(c),
      trendColour[trendOf(c)] || undefined,
    ],
    [
      "Hotspot Code Health",
      c.hotspotHealth === null ? "—" : c.hotspotHealth.toFixed(2),
      c.hotspotHealth === null ? undefined : dotColour(c.hotspotHealth),
    ],
    ["Commits", String(c.changes), undefined],
    ["Size", `${c.linesOfCode.toLocaleString("en-US")} lines in ${c.files} files`, undefined],
    ["Hotspots", String(c.hotspots), undefined],
  ];
  if (c.worstFile) {
    rows.push(["Worst file", `${c.worstFile.path} (${c.worstFile.health.toFixed(2)})`, dotColour(c.worstFile.health)]);
  }
  return (
    <div
      style={{
        position: "absolute",
        left: `${(c.cx / width) * 100}%`,
        top: `${(c.cy / height) * 100}%`,
        transform: below ? `translate(-50%, ${c.r + 14}px)` : `translate(-50%, calc(-100% - ${c.r + 14}px))`,
        pointerEvents: "none",
        background: theme.bg.editor,
        border: `1px solid ${theme.stroke.secondary}`,
        borderRadius: 6,
        boxShadow: "0 4px 14px rgba(0, 0, 0, 0.18)",
        padding: "8px 12px",
        minWidth: 240,
        zIndex: 1,
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 700, color: theme.text.primary, marginBottom: 2 }}>{c.name}</div>
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          marginBottom: 6,
          color: quadrantOf(c) === "address" ? codescene.conditionWarn : theme.text.tertiary,
        }}
      >
        {`${quadrants[quadrantOf(c)].name} · ${quadrants[quadrantOf(c)].action}`}
      </div>
      {rows.map(([label, value, colour]) => (
        <div key={label} style={{ display: "flex", justifyContent: "space-between", gap: 16, fontSize: 11, lineHeight: "17px" }}>
          <span style={{ color: theme.text.secondary }}>{label}</span>
          <span style={{ color: colour ?? theme.text.primary, fontWeight: colour ? 600 : 400, textAlign: "right" }}>{value}</span>
        </div>
      ))}
    </div>
  );
}

function Legend() {
  const items = [
    { label: `Unhealthy (below ${healthyThreshold.toFixed(1)})`, colour: dotColour(healthyThreshold - 1) },
    { label: `Healthy (${healthyThreshold.toFixed(1)} or higher)`, colour: dotColour(healthyThreshold) },
    { label: `Optimal (${optimal.toFixed(1)})`, colour: dotColour(optimal) },
  ];
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <svg width={16} height={16} viewBox="0 0 16 16">
          <path d={diamondPath(8, 8, 6)} fill={codescene.conditionWarn} />
        </svg>
        <Text size="small" weight="semibold">
          Architectural hotspot to address
        </Text>
      </div>
      {items.map((item) => (
        <div key={item.label} style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <div style={{ width: 10, height: 10, borderRadius: 5, background: item.colour }} />
          <Text size="small" tone="secondary">
            {item.label}
          </Text>
        </div>
      ))}
      <TrendLegend />
      <Text size="small" tone="tertiary">
        Bubble size: lines of code
      </Text>
    </div>
  );
}

function TrendLegend() {
  const items: { label: string; colour: string; rise: number }[] = [
    { label: "Improving", colour: trendColour.improving, rise: 8 },
    { label: "Declining", colour: trendColour.declining, rise: -8 },
  ];
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
      <Text size="small" tone="secondary">
        12-month trend:
      </Text>
      {items.map((item) => (
        <div key={item.label} style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <svg width={22} height={14} viewBox="0 0 22 14">
            <line
              x1={3}
              y1={7 + item.rise / 2}
              x2={19}
              y2={7 - item.rise / 2}
              stroke={item.colour}
              strokeWidth={2.5}
              strokeLinecap="round"
            />
          </svg>
          <Text size="small" tone="secondary">
            {item.label}
          </Text>
        </div>
      ))}
    </div>
  );
}

function AddressList({ items }: { items: ComponentData[] }) {
  const theme = useHostTheme();
  const columns = "16px minmax(140px, 1.2fr) 72px 92px 80px 64px 64px minmax(160px, 1.6fr)";
  const number = { fontSize: 12, fontVariantNumeric: "tabular-nums" as const, textAlign: "right" as const };
  const header = ["", "Component", "Code Health", "12-mo trend", "Hotspot CH", "Commits", "Hotspots", "Worst file"];
  return (
    <div style={{ border: `1px solid ${theme.stroke.secondary}`, borderRadius: 6, overflow: "hidden" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: columns,
          gap: 12,
          padding: "6px 12px",
          background: codescene.warnTint,
          color: theme.text.secondary,
          fontSize: 11,
          fontWeight: 600,
        }}
      >
        {header.map((h, i) => (
          <span key={h || "marker"} style={{ textAlign: i >= 2 && i <= 6 ? "right" : "left" }}>
            {h}
          </span>
        ))}
      </div>
      {items.map((c) => (
        <div
          key={c.name}
          style={{
            display: "grid",
            gridTemplateColumns: columns,
            gap: 12,
            alignItems: "center",
            padding: "8px 12px",
            borderTop: `1px solid ${theme.stroke.tertiary}`,
          }}
        >
          <svg width={12} height={12} viewBox="0 0 12 12">
            <path d={diamondPath(6, 6, 5)} fill={codescene.conditionWarn} />
          </svg>
          <span style={{ fontSize: 12, fontWeight: 600, color: theme.text.primary, overflowWrap: "anywhere" }}>{c.name}</span>
          <span style={{ ...number, color: dotColour(c.health), fontWeight: 600 }}>{c.health.toFixed(2)}</span>
          <span style={{ ...number, color: trendColour[trendOf(c)] || theme.text.tertiary, fontWeight: 600 }}>{trendText(c)}</span>
          <span style={{ ...number, color: c.hotspotHealth === null ? theme.text.tertiary : dotColour(c.hotspotHealth) }}>
            {c.hotspotHealth === null ? "—" : c.hotspotHealth.toFixed(2)}
          </span>
          <span style={{ ...number, color: theme.text.secondary }}>{c.changes}</span>
          <span style={{ ...number, color: theme.text.secondary }}>{c.hotspots}</span>
          <span style={{ fontSize: 12, color: theme.text.secondary, overflowWrap: "anywhere" }}>
            {c.worstFile ? (
              <>
                {c.worstFile.path}{" "}
                <span style={{ color: dotColour(c.worstFile.health), fontWeight: 600 }}>{c.worstFile.health.toFixed(2)}</span>
              </>
            ) : (
              "—"
            )}
          </span>
        </div>
      ))}
    </div>
  );
}

const signedPercent = (value: number) => `${value > 0 ? "+" : "−"}${Math.abs(value).toFixed(0)}`;

const midpointPercent = ({ lower, upper }: Range) => `${signedPercent((lower + upper) / 2)}%`;

function OutcomeCard({ outcome, featured }: { outcome: Outcome; featured: boolean }) {
  const theme = useHostTheme();
  const primary = useCodeScenePrimary();
  const metrics = [
    { label: "Defects", value: midpointPercent(outcome.defects) },
    { label: "Development time", value: midpointPercent(outcome.developmentTime) },
    { label: "Productivity", value: midpointPercent(outcome.productivity) },
  ];
  return (
    <div
      style={{
        border: `1px solid ${featured ? primary : theme.stroke.secondary}`,
        background: featured ? codescene.brandTint : "transparent",
        borderRadius: 6,
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: featured ? primary : theme.text.primary }}>{outcome.scope}</span>
        <span style={{ fontSize: 12, color: theme.text.secondary }}>
          Code Health <span style={{ color: dotColour(outcome.baseline), fontWeight: 600 }}>{outcome.baseline.toFixed(2)}</span>
          {" → "}
          <span style={{ color: dotColour(outcome.target), fontWeight: 600 }}>{outcome.target.toFixed(2)}</span>
        </span>
      </div>
      {metrics.map((m) => (
        <div key={m.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
          <span style={{ fontSize: 12, color: theme.text.secondary }}>{m.label}</span>
          <span style={{ fontSize: 20, fontWeight: 700, color: codescene.conditionGood, fontVariantNumeric: "tabular-nums" }}>
            {m.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function OutcomesSection({ addressNames }: { addressNames: string[] }) {
  return (
    <Stack gap={8}>
      <H2>{`What uplifting ${addressNames.join(" and ")} to ${optimal.toFixed(1)} buys`}</H2>
      <Grid columns="minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr)" gap={16} align="stretch">
        {outcomes.map((o, i) => (
          <div key={o.scope}>
            <OutcomeCard outcome={o} featured={i === 0} />
          </div>
        ))}
      </Grid>
      <Text size="small" tone="tertiary">
        Estimated change: the midpoint of the CodeScene outcome model's 90% interval. Component cards: development inside that component.
        Whole codebase: the lines-of-code-weighted average across all components shown, with the Address components at{" "}
        {optimal.toFixed(1)} and everything else unchanged.
      </Text>
    </Stack>
  );
}

const team = report.team ?? { developers: 10, hoursPerWeek: 40, weeksPerYear: 46 };
const hoursPerDeveloper = team.hoursPerWeek * team.weeksPerYear;
const teamHours = team.developers * hoursPerDeveloper;

function workShare(scope: string) {
  const component = components.find((c) => c.name === scope);
  if (!component) return 1;
  return component.changes / components.reduce((sum, c) => sum + c.changes, 0);
}

function hoursSaved(outcome: Outcome) {
  const productivityGain = (outcome.productivity.lower + outcome.productivity.upper) / 2 / 100;
  return teamHours * workShare(outcome.scope) * (productivityGain / (1 + productivityGain));
}

const formatHours = (hours: number) => Math.round(hours / 10) * 10;

function RoiCard({ outcome, featured }: { outcome: Outcome; featured: boolean }) {
  const theme = useHostTheme();
  const primary = useCodeScenePrimary();
  const saved = hoursSaved(outcome);
  const share = workShare(outcome.scope);
  const metrics = [
    { label: "Hours saved per year", value: formatHours(saved).toLocaleString("en-US") },
    { label: "Full-time developers freed", value: (saved / hoursPerDeveloper).toFixed(1) },
    { label: "Per developer per week", value: `${(saved / team.developers / team.weeksPerYear).toFixed(1)} h` },
  ];
  return (
    <div
      style={{
        border: `1px solid ${featured ? primary : theme.stroke.secondary}`,
        background: featured ? codescene.brandTint : "transparent",
        borderRadius: 6,
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: featured ? primary : theme.text.primary }}>{outcome.scope}</span>
        <span style={{ fontSize: 12, color: theme.text.secondary }}>
          {share === 1 ? "All of the team's development time" : `${Math.round(share * 100)}% of the team's commits`}
        </span>
      </div>
      {metrics.map((m) => (
        <div key={m.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
          <span style={{ fontSize: 12, color: theme.text.secondary }}>{m.label}</span>
          <span style={{ fontSize: 20, fontWeight: 700, color: primary, fontVariantNumeric: "tabular-nums" }}>{m.value}</span>
        </div>
      ))}
    </div>
  );
}

function RoiSection() {
  return (
    <Stack gap={8}>
      <H2>{`ROI for a team of ${team.developers} developers`}</H2>
      <Grid columns="minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr)" gap={16} align="stretch">
        {outcomes.map((o, i) => (
          <div key={o.scope}>
            <RoiCard outcome={o} featured={i === 0} />
          </div>
        ))}
      </Grid>
      <Text size="small" tone="tertiary">
        {`Assumes ${team.developers} developers at ${team.hoursPerWeek} hours a week for ${team.weeksPerYear} weeks a year ` +
          `(${teamHours.toLocaleString("en-US")} team hours). A productivity gain p means the same work takes 1/(1 + p) of ` +
          `the time, using the midpoint estimates above. Component cards count only the time spent in that component, ` +
          `approximated by its share of commits. The two component cards add up to roughly the whole-codebase figure.`}
      </Text>
    </Stack>
  );
}

function Intro() {
  const primary = useCodeScenePrimary();
  return (
    <div style={{ background: codescene.brandTint, borderLeft: `3px solid ${primary}`, borderRadius: 4, padding: "12px 16px" }}>
      <Stack gap={4}>
        <Text weight="semibold" style={{ color: primary }}>
          The idea
        </Text>
        <Text>
          Code Health per architectural component shows where the technical debt sits. Change activity across a
          component's files shows how much of the team's work runs through it. Together they show which parts of the
          architecture are worth uplifting, and which debt can safely wait.
        </Text>
      </Stack>
    </div>
  );
}

export default function ArchitecturalDebtQuadrant() {
  const primary = useCodeScenePrimary();
  const byQuadrant = (id: QuadrantId) => components.filter((c) => quadrantOf(c) === id);
  const address = byQuadrant("address").sort((a, b) => b.changes - a.changes);
  const order: QuadrantId[] = ["address", "plan", "delay", "ignore"];
  const totalChanges = components.reduce((sum, c) => sum + c.changes, 0);
  const addressShare = Math.round((address.reduce((sum, c) => sum + c.changes, 0) / totalChanges) * 100);

  return (
    <Stack gap={24} style={{ padding: 24, maxWidth: 1120 }}>
      <Stack gap={12}>
        <Stack gap={2}>
          <Text size="small" weight="semibold" style={{ color: primary, letterSpacing: 0.6, textTransform: "uppercase" }}>
            CodeScene · Architectural debt
          </Text>
          <H1>Architectural hotspots: where to pay down technical debt</H1>
        </Stack>
        <Intro />
      </Stack>

      <Stack gap={10}>
        <Legend />
        <QuadrantChart />
        <Text size="small" tone="tertiary">
          One bubble per architectural component in {project.name}. Vertical split: median change activity across
          components ({activityThreshold} commits). Horizontal split: Healthy ({healthyThreshold.toFixed(1)}). The line left
          of a bubble shows the direction of the component's Code Health trend, steeper when the pace is fast; steady
          components have no line. Hover a bubble for details. Quadrants follow
          Gartner's PAID model, with change activity as impact and low Code Health as risk. Source: {project.source}.
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>Address first</H2>
        <Text size="small" tone="secondary">
          {`${address.length} components carry ${addressShare}% of all commits while scoring below ${healthyThreshold.toFixed(1)}.`}
        </Text>
        <AddressList items={address} />
      </Stack>

      {outcomes.length > 0 && <OutcomesSection addressNames={address.map((c) => c.name)} />}

      {outcomes.length > 0 && <RoiSection />}

      <Stack gap={8}>
        <H2>The four quadrants</H2>
        <Grid columns={4} gap={20}>
          {order.map((id) => (
            <div key={id} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Text size="small" weight="semibold">
                {`${quadrants[id].name} · ${quadrants[id].action} (${byQuadrant(id).length})`}
              </Text>
              <Text size="small" tone="secondary">
                {quadrants[id].description}
              </Text>
            </div>
          ))}
        </Grid>
      </Stack>
    </Stack>
  );
}
