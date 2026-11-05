"""Generate portfolio architecture diagrams as standalone SVG files.

Each diagram is a small spec of groups, nodes and edges. Output SVGs carry their own
light/dark palette (prefers-color-scheme), so they render correctly inside <img>.

usage: python3 tools/diagrams.py   # writes assets/diagrams/*.svg
"""
from pathlib import Path
import hashlib
import html
import re

OUT = Path(__file__).resolve().parent.parent / "assets" / "diagrams"

STYLE = """
<style>
  :root { --bg:#ffffff; --fg:#1f2328; --muted:#59636e; --line:#8c959f; --box:#f6f8fa;
          --new:#e6f4ea; --newline:#2f855a; --warn:#fff4e5; --warnline:#b7791f; --group:#fbfbfc; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --line:#6e7681; --box:#161b22;
            --new:#12261b; --newline:#3fb950; --warn:#2a1f0d; --warnline:#d29922; --group:#10151c; }
  }
  .bg { fill: var(--bg); }
  .grp { fill: var(--group); stroke: var(--line); stroke-dasharray: 4 4; }
  .grpt { fill: var(--muted); font-size: 12px; font-weight: 600; }
  .box { fill: var(--box); stroke: var(--line); }
  .new { fill: var(--new); stroke: var(--newline); }
  .warn { fill: var(--warn); stroke: var(--warnline); }
  .t { fill: var(--fg); font-size: 13px; }
  .s { fill: var(--muted); font-size: 11px; }
  .title { fill: var(--fg); font-size: 14px; font-weight: 700; }
  .e { stroke: var(--line); stroke-width: 1.4; fill: none; marker-end: url(#a); }
  .ed { stroke: var(--line); stroke-width: 1.4; fill: none; stroke-dasharray: 5 4; marker-end: url(#a); }
  .el { fill: var(--muted); font-size: 11px; }
  .ah { fill: var(--line); }
  text { font-family: Pretendard, -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; }
</style>
"""


ICON_DIR = Path(__file__).resolve().parent / "icons"
ICON = 28  # icon tile size inside a node
PAD = 44   # text area starts this far from the node's left edge when it has an icon

# Simple Icons (CC0) glyphs on a brand-colored tile
BRAND = {"postgresql": "#4169E1", "redis": "#FF4438", "mongodb": "#47A248", "mysql": "#4479A1",
         "elasticsearch": "#005571", "opensearch": "#005EB8", "jenkins": "#D24939", "langchain": "#1C3C3C",
         "kakaotalk": "#FFCD00", "influxdb": "#22ADF6", "graphql": "#E10098", "nestjs": "#E0234E"}
BRAND_GLYPH = {"kakaotalk": "#191919"}

# Generic glyphs (24x24, white stroke) on a neutral tile — for things that are not a product
GENERIC = {
    "server": '<rect x="4" y="4" width="16" height="6" rx="1.5"/><rect x="4" y="14" width="16" height="6" rx="1.5"/><circle cx="7.5" cy="7" r=".9" fill="#fff"/><circle cx="7.5" cy="17" r=".9" fill="#fff"/>',
    "db": '<ellipse cx="12" cy="6" rx="7" ry="2.5"/><path d="M5 6v12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6"/><path d="M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
    "user": '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-4 3.1-6 7-6s7 2 7 6"/>',
    "llm": '<path d="M12 3l1.8 7.2L21 12l-7.2 1.8L12 21l-1.8-7.2L3 12l7.2-1.8z" fill="#fff"/>',
    "translate": '<path d="M4 5h9M8.5 3v2M6 5c.5 3 2.5 5.5 5 6.5M11 5c-.5 3-2.5 5.5-5 6.5"/><path d="M13 20l3.5-8 3.5 8M14.2 17.5h4.6"/>',
    "chat": '<path d="M4 5h16v10h-9l-4 4v-4H4z"/>',
    "check": '<rect x="5" y="4" width="14" height="16" rx="1.5"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>',
    "send": '<path d="M3 11L21 4l-7 17-3-8z"/><path d="M11 13l10-9"/>',
    "bell": '<path d="M6 16v-5a6 6 0 0112 0v5l2 2H4z"/><path d="M10 21h4"/>',
    "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "rollback": '<path d="M5 12a7 7 0 107-7H8"/><path d="M10 2L7 5l3 3"/>',
    "sliders": '<path d="M5 7h14M5 12h14M5 17h14"/><circle cx="9" cy="7" r="1.8" fill="#fff"/><circle cx="15" cy="12" r="1.8" fill="#fff"/><circle cx="8" cy="17" r="1.8" fill="#fff"/>',
    "chart": '<path d="M6 19v-7M12 19V5M18 19v-4M4 19h16"/>',
    "funnel": '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
    "browser": '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M3 9h18"/>',
    "building": '<path d="M5 20V5h9v15M14 10h5v10M3 20h18M8 8h3M8 12h3M8 16h3"/>',
    "device": '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M10 7h4"/><circle cx="12" cy="16" r="1.2"/>',
    "fanout": '<circle cx="6" cy="12" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="12" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 12h8M7.6 10.8l8.8-3.6M7.6 13.2l8.8 3.6"/>',
    "graph": '<circle cx="6" cy="7" r="2.2"/><circle cx="18" cy="6" r="2.2"/><circle cx="12" cy="17" r="2.2"/><path d="M8 7.5l8-1M7 9l4 6M17 8l-4 7"/>',
}
GENERIC_TILE = "#6e7781"


def _aws(name, x, y, size):
    """Embed an AWS Architecture Icon (64x64 or 40x40 source) as a nested svg."""
    src = (ICON_DIR / "aws" / f"{name}.svg").read_text()
    vb = src.split('viewBox="', 1)[1].split('"', 1)[0]
    inner = src.split(">", 2)[2] if src.startswith("<?xml") else src.split(">", 1)[1]
    inner = inner.rsplit("</svg>", 1)[0]
    inner = re.sub(r"<title>.*?</title>", "", inner)
    inner = re.sub(r'\s(id|xmlns:xlink)="[^"]*"', "", inner)
    return f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="{vb}">{inner}</svg>'


def _brand(name, x, y, size):
    src = (ICON_DIR / "brand" / f"{name}.svg").read_text()
    d = src.split(' d="', 1)[1].split('"', 1)[0]
    g, pad = BRAND_GLYPH.get(name, "#fff"), size * 0.18
    return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="6" fill="{BRAND[name]}"/>'
            f'<svg x="{x + pad}" y="{y + pad}" width="{size - 2 * pad}" height="{size - 2 * pad}" viewBox="0 0 24 24"><path fill="{g}" d="{d}"/></svg>')


def _generic(name, x, y, size):
    pad = size * 0.14
    return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="6" fill="{GENERIC_TILE}"/>'
            f'<svg x="{x + pad}" y="{y + pad}" width="{size - 2 * pad}" height="{size - 2 * pad}" viewBox="0 0 24 24">'
            f'<g fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{GENERIC[name]}</g></svg>')


def icon(name, x, y, size=ICON):
    kind, key = name.split(":", 1)
    return {"aws": _aws, "brand": _brand, "g": _generic}[kind](key, x, y, size)


def text_width(line, size):
    """Rough rendered width — CJK ≈ 1em, latin ≈ 0.58em. Used only to warn about overflow."""
    return sum(size * (1.0 if ord(c) > 0x2E80 else 0.32 if c == " " else 0.6) for c in line)


def node(n):
    x, y, w, h = n["x"], n["y"], n["w"], n.get("h", 46)
    cls = n.get("kind", "box")
    lines = n["label"] if isinstance(n["label"], list) else [n["label"]]
    out = [f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>']
    tx, room = x + w / 2, w - 12
    if n.get("icon"):
        out.append(icon(n["icon"], x + 9, y + (h - ICON) / 2))
        tx, room = x + PAD + (w - PAD - 8) / 2, w - PAD - 8
    total = len(lines)
    for i, line in enumerate(lines):
        cy = y + h / 2 + (i - (total - 1) / 2) * 16 + 4
        c = "t" if i == 0 else "s"
        if text_width(line, 13 if i == 0 else 11) > room:
            print(f"  ! overflow in {n['id']}: {line!r}")
        out.append(f'<text class="{c}" x="{tx}" y="{cy}" text-anchor="middle">{html.escape(line)}</text>')
    return "\n".join(out)


def anchor(n, toward):
    """Point on the box border facing `toward` (cx, cy)."""
    x, y, w, h = n["x"], n["y"], n["w"], n.get("h", 46)
    cx, cy = x + w / 2, y + h / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx else float("inf")
    sy = (h / 2) / abs(dy) if dy else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def center(n):
    return n["x"] + n["w"] / 2, n["y"] + n.get("h", 46) / 2


def edge(e, nodes):
    a, b = nodes[e["from"]], nodes[e["to"]]
    via = e.get("via", [])
    p1 = anchor(a, via[0] if via else center(b))
    p2 = anchor(b, via[-1] if via else center(a))
    pts = [p1, *via, p2]
    cls = "ed" if e.get("dashed") else "e"
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    out = [f'<path class="{cls}" d="{d}"/>']
    if e.get("label"):
        q1, q2 = (pts[1], pts[2]) if len(pts) > 2 else (p1, p2)
        mx, my = (q1[0] + q2[0]) / 2 + e.get("dx", 0), (q1[1] + q2[1]) / 2 + e.get("dy", -6)
        out.append(f'<text class="el" x="{mx:.1f}" y="{my:.1f}" text-anchor="middle">{html.escape(e["label"])}</text>')
    return "\n".join(out)


def render(spec):
    W, H = spec["w"], spec["h"]
    nodes = {n["id"]: n for n in spec["nodes"]}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{html.escape(spec["alt"])}">',
             STYLE,
             '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0,0 L10,5 L0,10 z"/></marker></defs>',
             f'<rect class="bg" width="{W}" height="{H}"/>']
    for g in spec.get("groups", []):
        parts.append(f'<rect class="grp" x="{g["x"]}" y="{g["y"]}" width="{g["w"]}" height="{g["h"]}" rx="10"/>')
        lx = g["x"] + 12
        for ic in g.get("icons", []):
            parts.append(icon(ic, lx, g["y"] + 5, 18))
            lx += 22
        parts.append(f'<text class="grpt" x="{lx + (2 if g.get("icons") else 0)}" y="{g["y"] + 18}">{html.escape(g["label"])}</text>')
    for t in spec.get("titles", []):
        parts.append(f'<text class="title" x="{t["x"]}" y="{t["y"]}">{html.escape(t["label"])}</text>')
    for e in spec["edges"]:
        parts.append(edge(e, nodes))
    for n in spec["nodes"]:
        parts.append(node(n))
    parts.append("</svg>")
    return "\n".join(parts)


DIAGRAMS = {
    # Flitto — global latency: before / after
    # 인프라 매핑 근거(2026-11-05 실측): 서버 = EKS eks-rtt-<리전>(apps/chat-tr/deploy/build.sh:41-45),
    # PG = RDS PostgreSQL rtt-prod(해외는 읽기 복제본), Redis = ElastiCache(서울 kr-redis · 해외 *-valkey-rtt).
    # Before 의 API 서버는 k8s 전환(2026-07-01, 7ea312acf) 전이라 EC2(ansible · pm2).
    "latency": {
        "w": 760, "h": 530, "alt": "글로벌 리전 레이턴시 개선 전후 구조",
        "titles": [{"x": 20, "y": 24, "label": "Before — 모든 쓰기가 서울 리전으로 왕복"},
                   {"x": 20, "y": 266, "label": "After — 리전 로컬 쓰기 + 비동기 동기화"}],
        "groups": [
            {"x": 20, "y": 36, "w": 250, "h": 190, "label": "해외 리전", "icons": ["aws:region"]},
            {"x": 470, "y": 36, "w": 270, "h": 190, "label": "서울 리전", "icons": ["aws:region"]},
            {"x": 20, "y": 278, "w": 430, "h": 232, "label": "해외 리전", "icons": ["aws:region"]},
            {"x": 515, "y": 278, "w": 225, "h": 232, "label": "서울 리전", "icons": ["aws:region"]},
        ],
        "nodes": [
            {"id": "api0", "x": 45, "y": 108, "w": 195, "icon": "aws:ec2", "label": ["API 서버 (당시 EC2)", "세션·DB·캐시 접근"]},
            {"id": "pg0", "x": 495, "y": 70, "w": 220, "icon": "aws:rds", "label": ["PostgreSQL (RDS)", "쓰기 (writer 1곳)"]},
            {"id": "rd0", "x": 495, "y": 150, "w": 220, "icon": "aws:elasticache", "label": ["Redis (ElastiCache)", "세션·캐시·큐·Pub/Sub"]},
            {"id": "api1", "x": 32, "y": 360, "w": 148, "icon": "aws:eks", "label": ["API 서버", "EKS (리전별)"]},
            {"id": "ddb", "x": 212, "y": 300, "w": 232, "h": 52, "kind": "new", "icon": "aws:dynamodb", "label": ["DynamoDB Global Table", "세션·대화방·연결 수 ~5ms"]},
            {"id": "lrd", "x": 212, "y": 366, "w": 232, "kind": "new", "icon": "aws:elasticache", "label": ["로컬 ElastiCache", "Valkey · 작업 큐 · Pub/Sub 구독"]},
            {"id": "q", "x": 212, "y": 428, "w": 232, "icon": "g:clock", "label": ["PG 비동기 쓰기", "응답을 기다리지 않음"]},
            {"id": "pg1", "x": 535, "y": 310, "w": 190, "icon": "aws:rds", "label": ["PostgreSQL (RDS)", "최종 일관성 반영"]},
            {"id": "ps", "x": 535, "y": 400, "w": 190, "kind": "warn", "icon": "g:fanout", "label": ["Pub/Sub fan-out", "남은 병목 ~150ms"]},
        ],
        "edges": [
            {"from": "api0", "to": "pg0", "label": "쓰기 왕복 ~150ms"},
            {"from": "api0", "to": "rd0", "label": "요청마다 여러 번 왕복", "dy": 14},
            {"from": "api1", "to": "ddb"},
            {"from": "api1", "to": "lrd"},
            {"from": "api1", "to": "q", "dashed": True},
            {"from": "q", "to": "pg1", "dashed": True, "label": "뒤따라 반영", "dx": -6, "dy": -22},
            {"from": "api1", "to": "ps", "dashed": True, "via": [(110, 494), (495, 494), (495, 423)], "label": "실시간 이벤트 발행", "dy": -6},
        ],
    },
    # Flitto — hyper-personalization knowledge graph (쌓기 = job-worker 큐, apps/job-worker/src/queue/hyper-personalization-graph)
    "personalization": {
        "w": 760, "h": 340, "alt": "지식그래프 기반 초개인화 쌓기와 꺼내기 흐름",
        "groups": [{"x": 180, "y": 20, "w": 565, "h": 140, "label": "백그라운드 잡 (job-worker · EKS, 응답을 막지 않음)", "icons": ["aws:eks"]}],
        "nodes": [
            {"id": "src", "x": 10, "y": 40, "w": 155, "h": 96, "icon": "g:user", "label": ["사용자 활동", "대화 요약 · 노트", "AI 어시스턴트 대화", "용어 교정"]},
            {"id": "ext", "x": 195, "y": 60, "w": 200, "h": 56, "icon": "g:llm", "label": ["① 추출 LLM", "사용자 관련 사실"]},
            {"id": "jdg", "x": 420, "y": 52, "w": 310, "h": 72, "icon": "g:llm", "label": ["② 판단 LLM", "같은 대상 · 같은 값 → 누적", "값이 바뀜 → 과거 값을 닫고 새 값"]},
            {"id": "kg", "x": 200, "y": 215, "w": 280, "h": 70, "kind": "new", "icon": "aws:rds", "label": ["사용자별 지식그래프", "RDS PostgreSQL + pgvector", "노드·관계·임베딩 · 과거 값은 닫아서 보존"]},
            {"id": "tr", "x": 525, "y": 190, "w": 220, "h": 52, "icon": "g:translate", "label": ["번역 프롬프트", "용어집(치환) + 배경지식(이해)"]},
            {"id": "ai", "x": 525, "y": 268, "w": 220, "h": 52, "icon": "g:chat", "label": ["AI 어시스턴트 답변", "질문과 가까운 사실만"]},
        ],
        "edges": [
            {"from": "src", "to": "ext"},
            {"from": "ext", "to": "jdg"},
            {"from": "jdg", "to": "kg", "label": "저장", "dx": 30, "dy": 8},
            {"from": "kg", "to": "tr", "label": "꺼내기", "dy": -4},
            {"from": "kg", "to": "ai", "label": "의미 검색", "dx": -8, "dy": 22},
        ],
    },
    # Flitto — LLM prompt management. 읽는 쪽 = LlmInvoker 를 쓰는 API 앱 5개 + job-worker, 호출 시점에 조회(SWR 캐시 60초)
    # 미러 = PG llm_prompt_repo / llm_prompt_commit (prompt-resolver.service.ts:5-6), provider 4종 (llm-prompt/providers/)
    "llm-prompt": {
        "w": 760, "h": 300, "alt": "LLM 프롬프트 관리 체계 흐름",
        "nodes": [
            {"id": "po", "x": 10, "y": 40, "w": 160, "icon": "g:user", "label": ["PO · 개발자", "프롬프트 수정·커밋"]},
            {"id": "gate", "x": 10, "y": 130, "w": 160, "h": 52, "kind": "warn", "icon": "g:check", "label": ["테스트 결과 검토", "직접 호출한 결과표"]},
            {"id": "ls", "x": 295, "y": 70, "w": 210, "h": 60, "kind": "new", "icon": "brand:langchain", "label": ["LangSmith (원본)", "staging / production 태그"]},
            {"id": "mir", "x": 295, "y": 205, "w": 210, "h": 60, "icon": "aws:rds", "label": ["DB 미러", "RDS PostgreSQL", "장애 대비 폴백"]},
            {"id": "api", "x": 553, "y": 60, "w": 197, "h": 80, "icon": "aws:eks", "label": ["API 앱 · job-worker", "EKS · 호출할 때 조회", "invoke(key, vars) 한 줄", "60초 캐시"]},
            {"id": "llm", "x": 553, "y": 205, "w": 197, "h": 60, "icon": "g:llm", "label": ["LLM Provider", "Vertex AI · OpenAI", "Bedrock · Upstage"]},
        ],
        "edges": [
            {"from": "po", "to": "ls", "label": "커밋 (서비스 무영향)", "dx": 6, "dy": -14},
            {"from": "gate", "to": "ls", "label": "통과 시 운영 태그", "dx": 6, "dy": 26},
            {"from": "ls", "to": "mir", "dashed": True, "label": "웹훅 · 주기 동기화", "dx": 52},
            {"from": "api", "to": "ls", "label": "1차 조회"},
            {"from": "api", "to": "mir", "dashed": True, "label": "2차 폴백", "dy": 16},
            {"from": "api", "to": "llm"},
        ],
    },
    # Flitto — log pipeline + secret change pipeline
    # 전송기 = 앱 프로세스 안 Winston transport(당시 packages/shared/.../winston-opensearch.transport.ts, 지금 nest-common).
    # OpenSearch = Amazon OpenSearch Service rtt-log-es (VPC) — 운영 시크릿 OPENSEARCH_ENDPOINT. Express 앱은 2026-09 제거(57dcb4be6).
    "ops": {
        "w": 760, "h": 300, "alt": "로그 파이프라인과 시크릿 변경 파이프라인",
        "titles": [{"x": 20, "y": 24, "label": "로그 파이프라인"}, {"x": 20, "y": 184, "label": "시크릿 변경 · 배포"}],
        "nodes": [
            {"id": "apps", "x": 15, "y": 40, "w": 160, "h": 80, "icon": "aws:eks", "label": ["서비스 앱", "NestJS · EKS", "5개 리전"]},
            {"id": "tp", "x": 193, "y": 40, "w": 170, "h": 80, "icon": "g:send", "label": ["로그 전송기", "앱 프로세스 내부", "버퍼 → bulk · gzip", "지수 백오프"]},
            {"id": "os", "x": 381, "y": 40, "w": 200, "h": 80, "kind": "new", "icon": "aws:opensearch", "label": ["OpenSearch Service", "AWS 관리형", "ISM 1일/5GB → 30일"]},
            {"id": "al", "x": 599, "y": 40, "w": 146, "h": 80, "kind": "warn", "icon": "g:bell", "label": ["디스크 알림", "80 · 90 · 95%"]},
            {"id": "jk", "x": 15, "y": 200, "w": 172, "h": 64, "icon": "brand:jenkins", "label": ["Jenkins 파라미터", "변경 사유 필수"]},
            {"id": "ap", "x": 205, "y": 200, "w": 158, "h": 64, "kind": "warn", "icon": "g:shield", "label": ["운영 승인 단계", "값은 *** 마스킹"]},
            {"id": "sm", "x": 381, "y": 200, "w": 200, "h": 64, "icon": "aws:secretsmanager", "label": ["Secrets Manager", "새 버전 · 감사 기록"]},
            {"id": "dp", "x": 599, "y": 200, "w": 146, "h": 64, "kind": "new", "icon": "g:rollback", "label": ["배포", "실패 시", "자동 롤백"]},
        ],
        "edges": [
            {"from": "apps", "to": "tp"}, {"from": "tp", "to": "os"}, {"from": "os", "to": "al"},
            {"from": "jk", "to": "ap"}, {"from": "ap", "to": "sm"}, {"from": "sm", "to": "dp"},
        ],
    },
    # bejewel — recommendation scheduler
    # 근거: MySQL = RDS(health 체크 'rds', 노션 "AWS RDS(MySQL)"), 점수 계산 = scheduler 앱 @Cron — ECS 배포 추정(Dockerfile-scheduler · ECR, terraform 의 다른 워커와 같은 틀).
    # MongoDB·Elasticsearch 는 호스팅 근거 없음 → 제품 로고만.
    "recommend": {
        "w": 760, "h": 260, "alt": "추천 상품 스케줄러 재구축 흐름",
        "nodes": [
            {"id": "my", "x": 15, "y": 40, "w": 175, "h": 56, "icon": "aws:rds", "label": ["MySQL (RDS)", "유저 행동 로그 3억 건+"]},
            {"id": "agg", "x": 205, "y": 40, "w": 165, "h": 56, "icon": "g:funnel", "label": ["일별 행동 집계", "(동료 구현)"]},
            {"id": "mg", "x": 385, "y": 40, "w": 180, "h": 56, "kind": "new", "icon": "brand:mongodb", "label": ["MongoDB", "상품 × 일 × 행동 유형"]},
            {"id": "sc", "x": 385, "y": 156, "w": 180, "h": 72, "kind": "new", "icon": "aws:ecs", "label": ["추천 점수 계산", "스케줄러 앱 · ECS", "1,000개 읽기", "100개씩 병렬"]},
            {"id": "adm", "x": 205, "y": 164, "w": 165, "h": 56, "icon": "g:sliders", "label": ["가중치 설정값", "쿼리에서 분리"]},
            {"id": "es", "x": 580, "y": 164, "w": 165, "h": 56, "icon": "brand:elasticsearch", "label": ["Elasticsearch", "100건씩 bulk 반영"]},
            {"id": "sl", "x": 580, "y": 40, "w": 165, "h": 56, "kind": "warn", "icon": "g:bell", "label": ["Slack 알림", "작업 실패 시"]},
        ],
        "edges": [
            {"from": "my", "to": "agg"}, {"from": "agg", "to": "mg"}, {"from": "mg", "to": "sc"},
            {"from": "adm", "to": "sc"}, {"from": "sc", "to": "es"}, {"from": "es", "to": "sl", "dashed": True},
        ],
    },
    # bejewel — message worker
    # 근거: 워커 = ECS(EC2 launch type) amondz-terraform-v2/5.ecs/var.tfvars:9 "message-ec2", Bull Redis = ElastiCache 추정(같은 레포 다른 Bull 큐가 *.cache.amazonaws.com),
    # API 서버 = ECS 추정(같은 terraform 틀), 알림톡 = BizM(스윗트래커) API — constants/service/bizm.js:92
    "message-worker": {
        "w": 760, "h": 220, "alt": "알림 메시지 워커 구조",
        "nodes": [
            {"id": "api", "x": 15, "y": 70, "w": 160, "icon": "aws:ecs", "label": ["API 서버", "발송 요청만 등록"]},
            {"id": "q", "x": 195, "y": 70, "w": 165, "kind": "new", "icon": "aws:elasticache", "label": ["Redis 큐", "ElastiCache · Bull"]},
            {"id": "wk", "x": 380, "y": 61, "w": 200, "h": 64, "kind": "new", "icon": "aws:ecs", "label": ["메시지 워커 (분리 서버)", "ECS", "500건씩 병렬 · 1초 간격"]},
            {"id": "kt", "x": 605, "y": 22, "w": 140, "h": 52, "icon": "brand:kakaotalk", "label": ["알림톡", "BizM API"]},
            {"id": "mg", "x": 605, "y": 130, "w": 140, "h": 52, "kind": "warn", "icon": "brand:mongodb", "label": ["MongoDB", "반복 실패 이력"]},
        ],
        "edges": [
            {"from": "api", "to": "q"}, {"from": "q", "to": "wk"}, {"from": "wk", "to": "kt"},
            {"from": "wk", "to": "mg", "dashed": True, "label": "3회 재시도 후", "dx": -40, "dy": 16},
        ],
    },
    # bejewel — ES snapshot migration (근거: 노션 이력서 "AWS Step Function, Lambda, AWS EventBridge, S3를 활용하여 Elasticsearch Migration 스케줄러 구현")
    "es-migration": {
        "w": 760, "h": 200, "alt": "Elasticsearch 스냅샷 마이그레이션 자동화",
        "groups": [{"x": 170, "y": 20, "w": 580, "h": 160, "label": "Step Functions (각 단계 = Lambda)", "icons": ["aws:stepfunctions", "aws:lambda"]}],
        "nodes": [
            {"id": "eb", "x": 10, "y": 77, "w": 145, "h": 52, "icon": "aws:eventbridge", "label": ["EventBridge", "주기 실행"]},
            {"id": "s1", "x": 182, "y": 77, "w": 132, "h": 52, "icon": "aws:s3", "label": ["스냅샷 생성", "→ S3"]},
            {"id": "s2", "x": 326, "y": 70, "w": 132, "h": 64, "icon": "g:check", "label": ["상태 확인", "실패 시", "에러 처리"]},
            {"id": "s3", "x": 470, "y": 77, "w": 132, "h": 52, "kind": "new", "icon": "brand:elasticsearch", "label": ["Restore", "Staging 반영"]},
            {"id": "s4", "x": 614, "y": 77, "w": 126, "h": 52, "icon": "g:check", "label": ["클러스터", "상태 확인"]},
        ],
        "edges": [{"from": "eb", "to": "s1"}, {"from": "s1", "to": "s2"}, {"from": "s2", "to": "s3"}, {"from": "s3", "to": "s4"}],
    },
    # personal — brain vault: overall loop (real wiring, 2026-11-03)
    "bv-overview": {
        "w": 760, "h": 360, "alt": "brain-vault 전체 구조 — 에이전트가 읽고 쓰는 흐름",
        "groups": [{"x": 300, "y": 12, "w": 445, "h": 336, "label": "brain-vault (Obsidian · obsidian-git 자동 백업)"}],
        "nodes": [
            {"id": "s", "x": 15, "y": 40, "w": 230, "h": 64, "label": ["Claude Code 세션", "여러 기기 · 여러 계정 · 같은 vault"]},
            {"id": "r", "x": 15, "y": 150, "w": 230, "h": 76, "label": ["읽기", "① 기억 허브 자동 로드", "② 시작 훅: 폴더 _index · 최근 결정", "③ 링크·depends-on 따라가기"]},
            {"id": "w", "x": 15, "y": 260, "w": 230, "h": 76, "kind": "new", "label": ["쓰기", "새 사실 = 기억 파일 1개 + 허브 1줄", "작업 노트 = 속성 + 엣지", "인계 노트 → 이전 인계 대체"]},
            {"id": "mem", "x": 320, "y": 40, "w": 200, "h": 64, "kind": "new", "label": ["기억 층 memory/", "사실 299 · 허브 1 · 색인 6"]},
            {"id": "cfg", "x": 535, "y": 40, "w": 195, "h": 64, "label": ["claude-config/", "규칙 · 훅 · 스킬 (~/.claude 링크)"]},
            {"id": "prj", "x": 320, "y": 150, "w": 200, "h": 64, "kind": "new", "label": ["작업 층 projects/", "노트 913 · 도메인 허브 66"]},
            {"id": "car", "x": 535, "y": 150, "w": 195, "h": 64, "label": ["산출 층", "career · artifacts"]},
            {"id": "obs", "x": 320, "y": 260, "w": 410, "h": 64, "label": ["Obsidian 화면 — 같은 파일을 사람이 본다", "그래프 뷰 · 백링크 · 속성 패널 · 도메인 허브 Bases 표"]},
        ],
        "edges": [
            {"from": "s", "to": "r"},
            {"from": "r", "to": "w", "label": "작업", "dx": 22, "dy": 4},
            {"from": "r", "to": "mem", "label": "읽기", "dx": -8, "dy": -4},
            {"from": "w", "to": "prj", "dashed": True, "label": "쓰기", "dx": -8, "dy": -4},
        ],
    },
    # personal — brain vault: memory layer graph (real counts)
    "bv-memory": {
        "w": 760, "h": 300, "alt": "기억 층 그래프 — 허브 · 색인 · 사실 노트",
        "nodes": [
            {"id": "hub", "x": 15, "y": 110, "w": 170, "h": 70, "kind": "warn", "label": ["MEMORY.md 허브", "모든 세션에 자동 로드", "색인 링크만 · 한 줄 = 훅"]},
            {"id": "i1", "x": 235, "y": 15, "w": 170, "h": 46, "label": ["색인: 작업 방식 피드백", "35줄"]},
            {"id": "i2", "x": 235, "y": 75, "w": 170, "h": 46, "label": ["색인: 진행 중 작업", "72줄"]},
            {"id": "i3", "x": 235, "y": 135, "w": 170, "h": 46, "label": ["색인: 운영 지식", "21줄"]},
            {"id": "i4", "x": 235, "y": 195, "w": 170, "h": 46, "label": ["색인: 보관 · 기타", "45 + 12줄"]},
            {"id": "fact", "x": 460, "y": 60, "w": 285, "h": 120, "kind": "new", "label": ["사실 노트 299개 — 한 사실 = 한 파일", "속성 type: 프로젝트 142 · 피드백 106 · 참조 44", "modified (수정 시각) · originSessionId (출처 세션)", "본문 [[링크]] 507 — 연결 485", "가장 많이 참조된 노트 = '단정 전에 경로 전체를 본다' (19)"]},
            {"id": "todo", "x": 460, "y": 215, "w": 285, "h": 52, "label": ["아직 안 쓴 기억 22", "링크만 있고 파일 없음 = 써야 할 것 표시"]},
        ],
        "edges": [
            {"from": "hub", "to": "i1"}, {"from": "hub", "to": "i2"}, {"from": "hub", "to": "i3"}, {"from": "hub", "to": "i4"},
            {"from": "i2", "to": "fact"}, {"from": "fact", "to": "todo", "dashed": True},
        ],
    },
    # personal — brain vault: work layer + time axis (real handoff chain, names generalized)
    "bv-time": {
        "w": 760, "h": 330, "alt": "작업 층 그래프와 시간 축 — 실제 인계 노트 체인",
        "titles": [{"x": 20, "y": 24, "label": "시간 축 — 세션 인계 노트 15개가 superseded-by 로 이어진 실제 체인 (9/30 → 10/17)"}],
        "nodes": [
            {"id": "h1", "x": 15, "y": 45, "w": 130, "h": 52, "label": ["인계 09-30", "설계 확정"]},
            {"id": "h2", "x": 165, "y": 45, "w": 130, "h": 52, "label": ["인계 10-01", "미완 정리"]},
            {"id": "h3", "x": 315, "y": 45, "w": 130, "h": 52, "label": ["인계 10-02", "상용 준비"]},
            {"id": "hd", "x": 465, "y": 45, "w": 110, "h": 52, "label": ["… 11개 …"]},
            {"id": "h15", "x": 595, "y": 45, "w": 150, "h": 52, "kind": "new", "label": ["인계 10-17", "체인 끝 = 현재 상태"]},
            {"id": "moc", "x": 15, "y": 180, "w": 180, "h": 64, "kind": "warn", "label": ["도메인 허브 (MOC) 66", "moc 링크 828", "Bases: domain 으로 자동 표"]},
            {"id": "n", "x": 260, "y": 170, "w": 230, "h": 84, "label": ["작업 노트 913", "domain · status · created · tags", "status: draft → active → done → archived", "날짜로 시작하는 파일 232"]},
            {"id": "dep", "x": 560, "y": 150, "w": 185, "h": 52, "label": ["depends-on 925", "읽을 때 같이 읽을 노트"]},
            {"id": "impl", "x": 560, "y": 225, "w": 185, "h": 52, "label": ["implements 456", "노트 ↔ 브랜치·커밋"]},
        ],
        "edges": [
            {"from": "h1", "to": "h2"}, {"from": "h2", "to": "h3"}, {"from": "h3", "to": "hd"}, {"from": "hd", "to": "h15"},
            {"from": "n", "to": "moc", "label": "moc", "dy": -6}, {"from": "n", "to": "dep"}, {"from": "n", "to": "impl", "dashed": True},
        ],
    },
    # personal — brain vault: spec flow + handoff flow (from skills/*/SKILL.md)
    "bv-workflow": {
        "w": 760, "h": 330, "alt": "작업 방식 — 명세 체인과 세션 인계",
        "titles": [{"x": 20, "y": 22, "label": "명세 체인 — 명세서도 vault 노드 (domain · moc · implements)"},
                   {"x": 20, "y": 190, "label": "세션 인계 — 인계서는 handoff/ 노드, 다음 인계가 superseded-by 로 잇는다"}],
        "nodes": [
            {"id": "d", "x": 15, "y": 38, "w": 170, "h": 76, "kind": "new", "label": ["/spec-docs", "코드 분석 → 명세서", "Phase · 완료 기준 · 용어", "구현은 안 한다"]},
            {"id": "rv", "x": 200, "y": 38, "w": 170, "h": 76, "label": ["/spec-review", "다른 모델 교차 비판 2라운드", "+ 보안 관점", "외부 의견 먼저 → 차이만 합성"]},
            {"id": "rn", "x": 385, "y": 38, "w": 170, "h": 76, "label": ["/spec-run", "Phase 별 실행", "3파일+ = 격리된 워커", "Phase 마다 결과 4항목"]},
            {"id": "vf", "x": 570, "y": 38, "w": 175, "h": 76, "label": ["/spec-verify", "교차 비판 + 프로젝트 기준", "수렴 게이트 · 라운드 상한 3", "지적 판정을 명세에 기록"]},
            {"id": "ho", "x": 15, "y": 210, "w": 240, "h": 100, "kind": "new", "label": ["/handoff-out (세션 끝)", "① 산출물이 vault 에 기록됐는지 검색으로 감사", "② 다시 볼 수 있는 것 = 명령 + 기대값", "③ 다시 못 보는 것 = 결정 · 기각 · 실패 · 제약", "④ 코드블럭 출력 + handoff/ 에 저장"]},
            {"id": "hn", "x": 280, "y": 225, "w": 190, "h": 70, "kind": "warn", "label": ["인계 노트 136개", "2026-08 ~ 11", "이어 쓴 39개 = superseded-by"]},
            {"id": "hi", "x": 495, "y": 210, "w": 250, "h": 100, "label": ["/handoff-in (새 세션)", "① 적힌 명령을 실제로 실행 — [시간] 태그부터", "② 현재 상태는 실측 > 인계서", "③ 불일치를 근거와 함께 보고", "④ 착수하지 않고 대기"]},
        ],
        "edges": [
            {"from": "d", "to": "rv"}, {"from": "rv", "to": "rn"}, {"from": "rn", "to": "vf"},
            {"from": "ho", "to": "hn"}, {"from": "hn", "to": "hi"},
        ],
    },
    # willog — server split by function
    # 근거: Core·DDM = ECS(EC2 launch type) legacy-nestjs/*/taskdef-prod.json:31, CDL = API Gateway + Lambda serverless/platform-client-data-loader/serverless.yml:74,
    # Noti = Lambda + SOLAPI serverless/platform-noti-manager/.../solapi.util.ts:1, RDB = MySQL(package.json) — RDS 추정(같은 회사 다른 DB 가 Aurora 클러스터)
    "willog-servers": {
        "w": 760, "h": 300, "alt": "기능 기준 서버 분리 구조",
        "nodes": [
            {"id": "cl", "x": 15, "y": 30, "w": 165, "icon": "g:browser", "label": ["웹 · 모바일 웹"]},
            {"id": "cs", "x": 15, "y": 129, "w": 165, "icon": "g:building", "label": ["고객사 시스템"]},
            {"id": "dv", "x": 15, "y": 216, "w": 165, "icon": "g:device", "label": ["트래킹 디바이스"]},
            {"id": "core", "x": 240, "y": 27, "w": 220, "h": 52, "kind": "new", "icon": "aws:ecs", "label": ["Core", "GraphQL API · ECS"]},
            {"id": "cdl", "x": 240, "y": 120, "w": 220, "h": 64, "kind": "new", "icon": "aws:lambda", "label": ["CDL", "API Gateway · Lambda", "배송 데이터 연동 REST"]},
            {"id": "ddm", "x": 240, "y": 213, "w": 220, "h": 52, "kind": "new", "icon": "aws:ecs", "label": ["DDM", "디바이스 시계열 API · ECS"]},
            {"id": "noti", "x": 525, "y": 8, "w": 220, "h": 64, "icon": "aws:lambda", "label": ["Noti", "Lambda · SOLAPI", "카카오톡 · SMS"]},
            {"id": "rdb", "x": 525, "y": 110, "w": 220, "icon": "aws:rds", "label": ["RDB (MySQL · RDS)", "배송 · 주문"]},
            {"id": "inf", "x": 525, "y": 216, "w": 220, "icon": "brand:influxdb", "label": ["InfluxDB", "디바이스 측정값"]},
        ],
        "edges": [
            {"from": "cl", "to": "core"}, {"from": "cs", "to": "cdl"}, {"from": "dv", "to": "ddm"},
            {"from": "core", "to": "noti"}, {"from": "core", "to": "rdb"}, {"from": "cdl", "to": "rdb"},
            {"from": "ddm", "to": "inf"},
        ],
    },
}


PAGES = [OUT.parent.parent / "portfolio.html"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    versions = {}
    for name, spec in DIAGRAMS.items():
        svg = render(spec)
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        versions[name] = hashlib.sha1(svg.encode()).hexdigest()[:8]
        print("wrote", name)
    # GitHub Pages caches assets for 10 min — stamp each <img> with a content hash so a push shows up at once
    for page in PAGES:
        src = page.read_text(encoding="utf-8")
        out = re.sub(r'assets/diagrams/([a-z0-9-]+)\.svg(\?v=[0-9a-f]+)?',
                     lambda m: f"assets/diagrams/{m.group(1)}.svg?v={versions[m.group(1)]}" if m.group(1) in versions else m.group(0), src)
        if out != src:
            page.write_text(out, encoding="utf-8")
            print("stamped", page.name)


if __name__ == "__main__":
    main()
