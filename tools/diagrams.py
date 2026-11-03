"""Generate portfolio architecture diagrams as standalone SVG files.

Each diagram is a small spec of groups, nodes and edges. Output SVGs carry their own
light/dark palette (prefers-color-scheme), so they render correctly inside <img>.

usage: python3 tools/diagrams.py   # writes assets/diagrams/*.svg
"""
from pathlib import Path
import html

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


def node(n):
    x, y, w, h = n["x"], n["y"], n["w"], n.get("h", 46)
    cls = n.get("kind", "box")
    lines = n["label"] if isinstance(n["label"], list) else [n["label"]]
    out = [f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>']
    total = len(lines)
    for i, line in enumerate(lines):
        cy = y + h / 2 + (i - (total - 1) / 2) * 16 + 4
        c = "t" if i == 0 else "s"
        out.append(f'<text class="{c}" x="{x + w / 2}" y="{cy}" text-anchor="middle">{html.escape(line)}</text>')
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
        parts.append(f'<text class="grpt" x="{g["x"] + 12}" y="{g["y"] + 18}">{html.escape(g["label"])}</text>')
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
    "latency": {
        "w": 760, "h": 530, "alt": "글로벌 리전 레이턴시 개선 전후 구조",
        "titles": [{"x": 20, "y": 24, "label": "Before — 모든 쓰기가 서울 리전으로 왕복"},
                   {"x": 20, "y": 266, "label": "After — 리전 로컬 쓰기 + 비동기 동기화"}],
        "groups": [
            {"x": 20, "y": 36, "w": 250, "h": 190, "label": "해외 리전"},
            {"x": 470, "y": 36, "w": 270, "h": 190, "label": "서울 리전"},
            {"x": 20, "y": 278, "w": 430, "h": 232, "label": "해외 리전"},
            {"x": 520, "y": 278, "w": 220, "h": 232, "label": "서울 리전"},
        ],
        "nodes": [
            {"id": "api0", "x": 55, "y": 108, "w": 180, "label": ["API 서버", "세션·DB·캐시 접근"]},
            {"id": "pg0", "x": 505, "y": 70, "w": 200, "label": ["PostgreSQL", "쓰기 (writer 1곳)"]},
            {"id": "rd0", "x": 505, "y": 150, "w": 200, "label": ["Redis", "세션·캐시·큐·Pub/Sub"]},
            {"id": "api1", "x": 45, "y": 360, "w": 160, "label": ["API 서버"]},
            {"id": "ddb", "x": 245, "y": 300, "w": 190, "h": 52, "kind": "new", "label": ["DynamoDB Global Table", "세션·대화방·연결 ~5ms"]},
            {"id": "lrd", "x": 245, "y": 366, "w": 190, "kind": "new", "label": ["로컬 Redis", "캐시·작업 큐 ~1ms"]},
            {"id": "q", "x": 245, "y": 428, "w": 190, "label": ["동기화 워커", "응답 후 비동기 (Bull 큐)"]},
            {"id": "pg1", "x": 545, "y": 310, "w": 170, "label": ["PostgreSQL", "최종 일관성 반영"]},
            {"id": "ps", "x": 545, "y": 400, "w": 170, "kind": "warn", "label": ["Pub/Sub fan-out", "남은 병목 ~150ms"]},
        ],
        "edges": [
            {"from": "api0", "to": "pg0", "label": "쓰기 왕복 ~150ms"},
            {"from": "api0", "to": "rd0", "label": "요청마다 여러 번 왕복", "dy": 14},
            {"from": "api1", "to": "ddb"},
            {"from": "api1", "to": "lrd"},
            {"from": "api1", "to": "q", "dashed": True},
            {"from": "q", "to": "pg1", "dashed": True, "label": "PG 동기화", "dx": 18, "dy": 4},
            {"from": "api1", "to": "ps", "dashed": True, "via": [(125, 494), (500, 494), (500, 423)], "label": "실시간 이벤트 발행", "dy": -6},
        ],
    },
    # Flitto — hyper-personalization knowledge graph
    "personalization": {
        "w": 760, "h": 330, "alt": "지식그래프 기반 초개인화 쌓기와 꺼내기 흐름",
        "groups": [{"x": 175, "y": 20, "w": 330, "h": 150, "label": "백그라운드 잡 (응답을 막지 않음)"}],
        "nodes": [
            {"id": "src", "x": 15, "y": 50, "w": 140, "h": 96, "label": ["사용자 활동", "대화 요약 · 노트", "AI 어시스턴트 대화", "용어 교정"]},
            {"id": "ext", "x": 190, "y": 70, "w": 140, "h": 56, "label": ["① 추출 LLM", "사용자 관련 사실"]},
            {"id": "jdg", "x": 350, "y": 70, "w": 140, "h": 56, "label": ["② 판단 LLM", "추가 / 갱신 / 유지"]},
            {"id": "kg", "x": 260, "y": 210, "w": 240, "h": 70, "kind": "new", "label": ["사용자별 지식그래프", "PostgreSQL + pgvector", "노드·관계·임베딩 · 과거 값은 닫아서 보존"]},
            {"id": "tr", "x": 560, "y": 170, "w": 185, "h": 52, "label": ["번역 프롬프트", "용어집(치환) + 배경지식(이해)"]},
            {"id": "ai", "x": 560, "y": 250, "w": 185, "h": 52, "label": ["AI 어시스턴트 답변", "질문과 가까운 사실만"]},
        ],
        "edges": [
            {"from": "src", "to": "ext"},
            {"from": "ext", "to": "jdg"},
            {"from": "jdg", "to": "kg", "label": "저장"},
            {"from": "kg", "to": "tr", "label": "꺼내기", "dy": -4},
            {"from": "kg", "to": "ai", "label": "의미 검색", "dy": 14},
        ],
    },
    # Flitto — LLM prompt management
    "llm-prompt": {
        "w": 760, "h": 300, "alt": "LLM 프롬프트 관리 체계 흐름",
        "nodes": [
            {"id": "po", "x": 20, "y": 40, "w": 150, "label": ["PO · 개발자", "프롬프트 수정·커밋"]},
            {"id": "gate", "x": 20, "y": 130, "w": 150, "h": 52, "kind": "warn", "label": ["평가 게이트", "골든셋 자동 채점"]},
            {"id": "ls", "x": 270, "y": 70, "w": 210, "h": 60, "kind": "new", "label": ["LangSmith (원본)", "staging / production 태그"]},
            {"id": "mir", "x": 270, "y": 210, "w": 210, "label": ["DB 미러", "장애 대비 폴백"]},
            {"id": "api", "x": 560, "y": 70, "w": 180, "h": 60, "label": ["API · 워커", "invoke(key, vars) 한 줄", "60초 캐시"]},
            {"id": "llm", "x": 560, "y": 210, "w": 180, "label": ["LLM Provider"]},
        ],
        "edges": [
            {"from": "po", "to": "ls", "label": "커밋 (서비스 무영향)", "dy": -12},
            {"from": "gate", "to": "ls", "label": "통과 시 태그 승격", "dy": 22},
            {"from": "ls", "to": "mir", "dashed": True, "label": "웹훅 · 주기 동기화", "dx": 52},
            {"from": "api", "to": "ls", "label": "1차 조회"},
            {"from": "api", "to": "mir", "dashed": True, "label": "2차 폴백", "dy": 16},
            {"from": "api", "to": "llm"},
        ],
    },
    # Flitto — log pipeline + secret change pipeline
    "ops": {
        "w": 760, "h": 300, "alt": "로그 파이프라인과 시크릿 변경 파이프라인",
        "titles": [{"x": 20, "y": 24, "label": "로그 파이프라인"}, {"x": 20, "y": 176, "label": "시크릿 변경 · 배포"}],
        "nodes": [
            {"id": "apps", "x": 20, "y": 44, "w": 160, "h": 52, "label": ["서비스 앱", "NestJS · Express · 다중 리전"]},
            {"id": "tp", "x": 210, "y": 44, "w": 170, "h": 52, "label": ["로그 전송기", "버퍼 → bulk · gzip · 백오프"]},
            {"id": "os", "x": 410, "y": 44, "w": 170, "h": 52, "kind": "new", "label": ["OpenSearch", "ISM 1일/5GB → 30일"]},
            {"id": "al", "x": 610, "y": 44, "w": 130, "h": 52, "kind": "warn", "label": ["디스크 알림", "80 · 90 · 95%"]},
            {"id": "jk", "x": 20, "y": 196, "w": 160, "h": 52, "label": ["Jenkins 파라미터", "변경 사유 필수"]},
            {"id": "ap", "x": 210, "y": 196, "w": 170, "h": 52, "kind": "warn", "label": ["운영 승인 단계", "값은 *** 마스킹"]},
            {"id": "sm", "x": 410, "y": 196, "w": 170, "h": 52, "label": ["Secrets Manager", "새 버전 · 감사 기록"]},
            {"id": "dp", "x": 610, "y": 196, "w": 130, "h": 52, "kind": "new", "label": ["배포", "실패 시 자동 롤백"]},
        ],
        "edges": [
            {"from": "apps", "to": "tp"}, {"from": "tp", "to": "os"}, {"from": "os", "to": "al"},
            {"from": "jk", "to": "ap"}, {"from": "ap", "to": "sm"}, {"from": "sm", "to": "dp"},
        ],
    },
    # bejewel — recommendation scheduler
    "recommend": {
        "w": 760, "h": 260, "alt": "추천 상품 스케줄러 재구축 흐름",
        "nodes": [
            {"id": "my", "x": 15, "y": 40, "w": 160, "h": 52, "label": ["MySQL", "유저 행동 지표 3억 건+"]},
            {"id": "agg", "x": 205, "y": 40, "w": 150, "h": 52, "label": ["1시간 집계", "스케줄러"]},
            {"id": "mg", "x": 385, "y": 40, "w": 160, "h": 52, "kind": "new", "label": ["MongoDB", "시간별 집계 (ID 조회)"]},
            {"id": "sc", "x": 385, "y": 160, "w": 160, "h": 52, "kind": "new", "label": ["추천 점수 계산", "배치 · 병렬 처리"]},
            {"id": "adm", "x": 205, "y": 160, "w": 150, "h": 52, "label": ["관리자 페이지", "가중치 설정"]},
            {"id": "es", "x": 585, "y": 160, "w": 160, "h": 52, "label": ["Elasticsearch", "bulk 갱신 · 재시도"]},
            {"id": "sl", "x": 585, "y": 40, "w": 160, "h": 52, "kind": "warn", "label": ["Slack · 로그", "재시도 초과 시"]},
        ],
        "edges": [
            {"from": "my", "to": "agg"}, {"from": "agg", "to": "mg"}, {"from": "mg", "to": "sc"},
            {"from": "adm", "to": "sc"}, {"from": "sc", "to": "es"}, {"from": "es", "to": "sl", "dashed": True},
        ],
    },
    # bejewel — message worker
    "message-worker": {
        "w": 760, "h": 220, "alt": "알림 메시지 워커 구조",
        "nodes": [
            {"id": "api", "x": 20, "y": 70, "w": 150, "label": ["API 서버", "발송 요청만 등록"]},
            {"id": "q", "x": 210, "y": 70, "w": 150, "kind": "new", "label": ["Redis 큐", "발송 job"]},
            {"id": "wk", "x": 400, "y": 70, "w": 170, "h": 52, "kind": "new", "label": ["메시지 워커 (분리 서버)", "배치 발송 · 중복 방지"]},
            {"id": "kt", "x": 610, "y": 30, "w": 130, "label": ["알림톡"]},
            {"id": "mg", "x": 610, "y": 130, "w": 130, "h": 52, "kind": "warn", "label": ["MongoDB", "반복 실패 이력"]},
        ],
        "edges": [
            {"from": "api", "to": "q"}, {"from": "q", "to": "wk"}, {"from": "wk", "to": "kt"},
            {"from": "wk", "to": "mg", "dashed": True, "label": "재시도 초과", "dx": -40, "dy": 16},
        ],
    },
    # bejewel — ES snapshot migration
    "es-migration": {
        "w": 760, "h": 200, "alt": "Elasticsearch 스냅샷 마이그레이션 자동화",
        "groups": [{"x": 175, "y": 20, "w": 570, "h": 160, "label": "Step Functions (각 단계 = Lambda)"}],
        "nodes": [
            {"id": "eb", "x": 15, "y": 80, "w": 140, "label": ["EventBridge", "주기 실행"]},
            {"id": "s1", "x": 195, "y": 80, "w": 125, "label": ["스냅샷 생성", "→ S3"]},
            {"id": "s2", "x": 335, "y": 80, "w": 125, "label": ["상태 확인", "실패 시 에러 처리"]},
            {"id": "s3", "x": 475, "y": 80, "w": 125, "kind": "new", "label": ["Restore", "Staging 반영"]},
            {"id": "s4", "x": 615, "y": 80, "w": 120, "label": ["클러스터", "상태 확인"]},
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
    "willog-servers": {
        "w": 760, "h": 300, "alt": "기능 기준 서버 분리 구조",
        "nodes": [
            {"id": "cl", "x": 20, "y": 30, "w": 150, "label": ["웹 · 모바일 웹"]},
            {"id": "cs", "x": 20, "y": 120, "w": 150, "label": ["고객사 시스템"]},
            {"id": "dv", "x": 20, "y": 210, "w": 150, "label": ["트래킹 디바이스"]},
            {"id": "core", "x": 250, "y": 30, "w": 190, "h": 52, "kind": "new", "label": ["Core", "GraphQL API · ECS"]},
            {"id": "cdl", "x": 250, "y": 120, "w": 190, "h": 52, "kind": "new", "label": ["CDL", "배송 데이터 연동 REST"]},
            {"id": "ddm", "x": 250, "y": 210, "w": 190, "h": 52, "kind": "new", "label": ["DDM", "디바이스 시계열 API"]},
            {"id": "noti", "x": 540, "y": 10, "w": 190, "label": ["Noti", "카카오톡 · SMS"]},
            {"id": "rdb", "x": 540, "y": 100, "w": 190, "label": ["RDB", "배송 · 주문"]},
            {"id": "inf", "x": 540, "y": 213, "w": 190, "label": ["InfluxDB", "디바이스 측정값"]},
        ],
        "edges": [
            {"from": "cl", "to": "core"}, {"from": "cs", "to": "cdl"}, {"from": "dv", "to": "ddm"},
            {"from": "core", "to": "noti"}, {"from": "core", "to": "rdb"}, {"from": "cdl", "to": "rdb"},
            {"from": "ddm", "to": "inf"},
        ],
    },
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in DIAGRAMS.items():
        (OUT / f"{name}.svg").write_text(render(spec), encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()
