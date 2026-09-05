"""重跑模块依赖聚合：验证 A 出边归零，并给出当前环状况。"""
import ast, pathlib, sys
from collections import defaultdict

ROOT = pathlib.Path("app")
# 模块归属（按 S1-001 §2 + S2-001 §2.1/§2.2 修正后）
def owner(rel: str) -> str | None:
    p = rel.replace("\\", "/")
    rules = [
        ("services/orchestration_app/", "O"),
        ("services/robot/", "B"), ("services/analysis/", "B"), ("services/storage/", "B"),
        ("services/robot_service", "B"), ("services/robot_asset_validator", "B"),
        ("models/robot", "B"), ("api/v1/endpoints/robots", "B"), ("api/v1/endpoints/onboarding", "B"),
        ("services/identity/", "A"), ("services/authz_guard", "A"), ("services/access_control", "A"),
        ("services/ownership", "A"), ("services/login_throttle", "A"),
        ("services/audit_event_service", "A"),
        ("models/user", "A"), ("models/rbac", "A"), ("models/school", "A"),
        ("models/audit_event", "A"), ("models/access_token", "A"), ("models/refresh_token", "A"),
        ("api/v1/endpoints/auth", "A"), ("api/v1/endpoints/admin", "A"), ("api/v1/endpoints/audit", "A"),
        ("services/knowledge/", "C"), ("services/knowledge_governance", "C"), ("models/knowledge", "C"),
        ("services/sop/", "D"), ("services/maintenance/", "D"), ("services/sop_service", "D"),
        ("services/fault_service", "D"), ("models/sop", "D"), ("models/fault", "D"),
        ("models/robot_sop_draft", "D"),
        ("services/pipeline/", "E"), ("services/task_service", "E"), ("services/event_service", "E"),
        ("services/snapshot_service", "E"), ("services/scoring_service", "E"),
        ("services/preflight_check", "E"), ("models/task", "E"), ("models/event", "E"),
        ("models/snapshot", "E"),
        ("services/teaching/", "F"), ("services/teaching_service", "F"),
        ("services/diagnosis_service", "F"), ("models/teaching", "F"),
        ("services/training/", "G"), ("services/memory/", "G"), ("models/training", "G"),
        ("models/skill_profile", "G"),
        ("services/evidence", "H"), ("services/incident_service", "H"),
        ("services/observation_service", "H"), ("services/assessment_service", "H"),
        ("models/evidence", "H"), ("models/incident", "H"), ("models/observation", "H"),
        ("models/assessment", "H"),
        ("services/orchestrator_v2", "I"), ("services/agent_service", "I"),
        ("services/orchestration/", "I"), ("services/intent/", "I"),
        ("services/policy_matrix", "I"), ("services/tool_executor", "I"),
        ("services/approval_service", "I"), ("services/multi_agent", "I"),
        ("models/approval", "I"), ("models/command", "I"), ("models/skill", "I"),
        ("services/llm/", "S1"),
        ("services/websocket_manager", "S2"), ("adapters/", "S2"),
        ("services/simulation/", "S3"), ("services/diagnosis/", "S3"),
    ]
    for pref, mod in rules:
        if pref in p:
            return mod
    return None

mod_of = {}
for f in ROOT.rglob("*.py"):
    if "__pycache__" in str(f): continue
    mod_of[str(f)] = owner(str(f))

def modname(path: str) -> str:
    return path[:-3].replace("/", ".").replace(".__init__", "")

by_module = {modname(k): k for k in mod_of}
edges = defaultdict(set)
for f, m in mod_of.items():
    if not m: continue
    try: tree = ast.parse(pathlib.Path(f).read_text())
    except SyntaxError: continue
    for n in ast.walk(tree):
        tgt = None
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("app."):
            tgt = n.module.replace(".", "/")
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("app."): tgt = a.name.replace(".", "/")
        if not tgt: continue
        cands = [k for k in mod_of if k[:-3] == tgt or k == tgt + "/__init__.py"]
        for c in cands:
            tm = mod_of[c]
            if tm and tm != m:
                edges[(m, tm)].add((f, c))

out_A = {k: v for k, v in edges.items() if k[0] == "A"}
print("=== A 的出边 ===")
if not out_A:
    print("  0 条 —— A 出边归零 ✅")
else:
    for (a, b), pairs in sorted(out_A.items()):
        print(f"  A→{b}: {len(pairs)} 条")
        for src, dst in sorted(pairs)[:3]:
            print(f"      {src} → {dst}")
print(f"\nA 的模块出方向数: {len(out_A)}")
print(f"A 的入度(被依赖模块数): {len({k[0] for k in edges if k[1]=='A'})}")
print(f"\n跨模块边合计: {sum(len(v) for v in edges.values())}")
print(f"非零依赖方向: {len(edges)}")
bidir = sorted({tuple(sorted(k)) for k in edges if (k[1], k[0]) in edges})
print(f"双向依赖模块对: {len(bidir)}")
for a, b in bidir:
    print(f"  {a} ↔ {b}: {a}→{b} {len(edges.get((a,b),()))} / {b}→{a} {len(edges.get((b,a),()))}")

# 强连通分量与环
import itertools
nodes = sorted({k[0] for k in edges} | {k[1] for k in edges})
adj = defaultdict(set)
for (a, b) in edges: adj[a].add(b)

def scc(nodes, adj):
    idx, low, on, st, out, c = {}, {}, set(), [], [], [0]
    def dfs(v):
        idx[v]=low[v]=c[0]; c[0]+=1; st.append(v); on.add(v)
        for w in adj[v]:
            if w not in idx: dfs(w); low[v]=min(low[v],low[w])
            elif w in on: low[v]=min(low[v],idx[w])
        if low[v]==idx[v]:
            comp=[]
            while True:
                w=st.pop(); on.discard(w); comp.append(w)
                if w==v: break
            out.append(comp)
    for v in nodes:
        if v not in idx: dfs(v)
    return out
comps=[c for c in scc(nodes,adj) if len(c)>1]
print(f"\n=== 强连通分量（size>1）: {len(comps)} 个 ===")
for c in comps: print(f"  size {len(c)}: {sorted(c)}")
print(f"环中模块总数: {sum(len(c) for c in comps)} / {len(nodes)}")
