#!/usr/bin/env python3
"""
Codex MCP Server — The Enforcer
Dual‑agent quality gate for snapshot, cleanup, validation, restore,
activity reporting, and project context indexing via MCP tools.
"""

import json  # JSON config, payloads, and artifacts
import os
import re  # Heuristics for code/comment detection
import subprocess
import hashlib  # Content hashing for snapshots
import asyncio  # Async MCP server + tools
import fnmatch  # Glob‑style include/exclude
import difflib  # Unified diff generation for reports
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
import ast
import ast
try:
    import mcp.server as mcp
    from mcp.server.stdio import stdio_server
except Exception:
    # Fallback stubs to allow direct module usage (e.g., prune/enforce) without MCP installed
    class _DummyTool:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _DummyServer:
        def __init__(self, name: str):
            self.name = name
        def list_tools(self):
            def _decorator(fn):
                return fn
            return _decorator
        def call_tool(self):
            def _decorator(fn):
                return fn
            return _decorator

    class _DummyMCP:
        Server = _DummyServer
        Tool = _DummyTool
        class TextContent:
            def __init__(self, type: str, text: str):
                self.type = type
                self.text = text

    mcp = _DummyMCP()

    def stdio_server(*args, **kwargs):  # type: ignore
        return None

@dataclass
class CodexSnapshot:
    """Snapshot of code state for comparison"""
    timestamp: str
    files: Dict[str, str]  # filepath -> content hash
    file_contents: Dict[str, str]  # filepath -> actual content
    metadata: Dict[str, Any]

@dataclass
class CodexReport:
    """Enforcement report with Russian Olympic Judge scoring"""
    score: float
    issues: List[str]
    fixes_applied: List[str]
    files_modified: List[str]
    timestamp: str
    pristine: bool  # True if score >= 9.0

class CodexEnforcer:
    """The Enforcer - Maintains pristine code quality"""
    
    def __init__(self):
        # Latest in‑memory snapshot; persisted snapshots live under .codex/snapshots
        self.snapshot: Optional[CodexSnapshot] = None
        # Workspace root (all relative paths resolve from here)
        self.workspace_root = Path.cwd()
        # Cross‑agent artifacts for auditability and shared context
        self.codex_dir = self.workspace_root / ".codex"
        self.snapshots_dir = self.codex_dir / "snapshots"
        self.reports_dir = self.codex_dir / "reports"
        self.codex_dir.mkdir(exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        # Load merged config (defaults + codex_config.json)
        self.config = self.load_config()
        # JSONL activity stream of tool operations
        self.activity_log = self.codex_dir / "activity.log"
        # Central logs root under Claude rules dir (if available), else local .codex
        try:
            rules_dir = self.config.get("rules_dir")
            rules_path = Path(str(rules_dir)) if rules_dir else (Path.home() / ".claude" if (Path.home() / ".claude").exists() else None)
        except Exception:
            rules_path = None
        self.logs_root = (rules_path / "enforcer_logs") if rules_path else (self.codex_dir / "enforcer_logs")
        self.logs_root.mkdir(parents=True, exist_ok=True)
        
    def calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def load_config(self) -> Dict[str, Any]:
        """Load config from codex_config.json if present, else defaults."""
        default_config: Dict[str, Any] = {
            "mode": "strict",
            "max_file_lines": 500,
            "remove_prints": True,
            "remove_todos": False,
            "preserve_docblocks": True,
            "ignore_tests_for_prints": True,
            "extensions": [".py", ".pyi", ".js", ".jsx", ".cjs", ".mjs", ".ts", ".tsx"],
            "include": [],
            "exclude": [
                "**/node_modules/**",
                "**/.venv/**",
                "**/venv/**",
                "**/dist/**",
                "**/build/**",
                "**/.git/**",
                "**/__pycache__/**",
                "**/.pytest_cache/**",
                "**/.mypy_cache/**",
                "**/coverage/**",
                "**/.cache/**",
                "**/.next/**",
                "**/out/**",
                "**/target/**"
            ],
            "allowed_roots": [],
            "rules_dir": None
        }
        cfg_path = self.workspace_root / "codex_config.json"
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                default_config.update(data)
            except Exception:
                pass
        # Merge overrides from external rules directory (Claude MD folder)
        try:
            env_rules = os.environ.get("CLAUDE_RULES_DIR") or os.environ.get("CODEX_RULES_DIR")
            candidates: List[Path] = []
            if env_rules:
                candidates.append(Path(env_rules))
            if default_config.get("rules_dir"):
                candidates.append(Path(str(default_config.get("rules_dir"))))
            home_claude = Path.home() / ".claude"
            if home_claude.exists():
                candidates.append(home_claude)
            for d in candidates:
                if not d or not d.exists() or not d.is_dir():
                    continue
                for fname in ("codex_config.json", "codex_rules.json"):
                    p = d / fname
                    if p.exists():
                        try:
                            data = json.loads(p.read_text(encoding="utf-8"))
                            default_config.update(data)
                            default_config["rules_dir"] = str(d)
                            break
                        except Exception:
                            continue
                if default_config.get("rules_dir"):
                    break
        except Exception:
            pass
        return default_config

    def _allowed_roots(self) -> List[Path]:
        roots = self.config.get("allowed_roots") or []
        if not roots:
            return [self.workspace_root]
        return [Path(r).resolve() for r in roots]

    def _is_within_allowed(self, path: Path) -> bool:
        # Safety guard: only operate within configured allowed_roots
        rp = path.resolve()
        for root in self._allowed_roots():
            try:
                rp.relative_to(root)
                return True
            except Exception:
                continue
        return False

    def _log_activity(self, event: str, data: Optional[Dict[str, Any]] = None) -> None:
        try:
            record = {"ts": datetime.now().isoformat(), "event": event, "data": data or {}}
            with self.activity_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

    def _match_any(self, path: Path, patterns: List[str]) -> bool:
        s = str(path.as_posix())
        return any(fnmatch.fnmatch(s, pat) for pat in patterns)

    def expand_paths(self, inputs: List[str]) -> List[str]:
        """Expand files/dirs/globs; enforce allowed roots and include/exclude/extension filters."""
        exts: Set[str] = set(self.config.get("extensions", []))
        include: List[str] = self.config.get("include", [])
        exclude: List[str] = self.config.get("exclude", [])

        result: Set[Path] = set()
        for p in inputs:
            pth = Path(p)
            if any(ch in p for ch in ["*", "?", "["]):
                for m in self.workspace_root.glob(p):
                    if m.is_file():
                        result.add(m)
                    elif m.is_dir():
                        for f in m.rglob("*"):
                            if f.is_file():
                                result.add(f)
            elif pth.exists():
                if pth.is_file():
                    result.add(pth)
                elif pth.is_dir():
                    for f in pth.rglob("*"):
                        if f.is_file():
                            result.add(f)

        filtered: List[Path] = []
        for f in result:
            # Enforce allowed roots + filter by configured patterns
            if not self._is_within_allowed(f):
                continue
            if exts and f.suffix not in exts:
                continue
            if exclude and self._match_any(f, exclude):
                continue
            if include and not self._match_any(f, include):
                continue
            filtered.append(f)
        return [str(p) for p in sorted(set(filtered))]

    def _safe_name(self, name: Optional[str]) -> str:
        if not name:
            return "untitled"
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name))[:120] or "untitled"

    def _write_summary_markdown(self, dirpath: Path, header: str, summary: Dict[str, Any]) -> None:
        try:
            lines = [f"# {header}"]
            for k, v in summary.items():
                if isinstance(v, (list, dict)):
                    continue
                lines.append(f"- {k}: {v}")
            (dirpath / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    def _write_logs(self, kind: str, payload: Dict[str, Any], title: Optional[str], module: Optional[str]) -> Optional[Path]:
        try:
            ts = payload.get("timestamp") or datetime.now().isoformat()
            date_part = ts.split("T")[0]
            title_safe = self._safe_name(title)
            module_safe = self._safe_name(module)
            dirpath = self.logs_root / date_part / module_safe / title_safe
            dirpath.mkdir(parents=True, exist_ok=True)
            fname = f"{kind}_{ts.replace(':','-')}.json"
            out = dirpath / fname
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            summary = {
                "kind": kind,
                "score": payload.get("score"),
                "pristine": payload.get("pristine"),
                "files_modified": len(payload.get("files_modified", [])) if isinstance(payload.get("files_modified"), list) else None,
                "issues_count": len(payload.get("issues", [])) if isinstance(payload.get("issues"), list) else None
            }
            self._write_summary_markdown(dirpath, f"{kind} — {title or ''}".strip(), summary)
            return out
        except Exception:
            return None

    def build_rag_context(self, roots: List[str], title: Optional[str], module: Optional[str]) -> Dict[str, Any]:
        files = self.expand_paths(roots)
        js_exts = {'.js','.jsx','.ts','.tsx','.mjs','.cjs'}
        py_exts = {'.py'}
        js_files = [f for f in files if Path(f).suffix in js_exts]
        py_files = [f for f in files if Path(f).suffix in py_exts]

        types: Dict[str, Dict[str, Any]] = {}
        components: Dict[str, Dict[str, Any]] = {}
        state_vars: List[Dict[str, Any]] = []
        defaults: List[Dict[str, Any]] = []

        # JS/TS extraction heuristics
        iface_re = re.compile(r"(?:export\s+)?(interface|type)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*)?\{([\s\S]*?)\}\s*", re.MULTILINE)
        field_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_\.\?]*)\s*:\s*([^;]+);?\s*$")
        comp_fc_re = re.compile(r"const\s+([A-Z][A-Za-z0-9_]*)\s*:\s*React\.FC\s*<\s*([A-Za-z0-9_<> ,]+)\s*>", re.MULTILINE)
        comp_fn_re = re.compile(r"function\s+([A-Z][A-Za-z0-9_]*)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z0-9_<> ,]+)\s*\)")
        default_props_re = re.compile(r"([A-Z][A-Za-z0-9_]*)\.defaultProps\s*=\s*\{([\s\S]*?)\}\s*;?", re.MULTILINE)
        use_state_re = re.compile(r"const\s*\[\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*set[A-Za-z_][A-Za-z0-9_]*\s*\]\s*=\s*useState\s*\(([^)]*)\)")
        destruct_default_re = re.compile(r"function\s+[A-Z][A-Za-z0-9_]*\s*\(\s*\{([^}]*)\}\s*\)")
        destruct_field_re = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^,]+)")

        for f in js_files:
            try:
                text = Path(f).read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            # Interfaces / types
            for kind, name, body in iface_re.findall(text):
                fields = {}
                for line in body.splitlines():
                    m = field_re.match(line.strip())
                    if m:
                        fields[m.group(1)] = m.group(2).strip()
                types[name] = {"kind": kind, "fields": fields, "file": f}
            # Components using React.FC<Props>
            for comp, props in comp_fc_re.findall(text):
                components.setdefault(comp, {"props": props, "file": f})
            # Components with typed function parameter
            for comp, param, props in comp_fn_re.findall(text):
                components.setdefault(comp, {"props": props, "file": f})
            # defaultProps
            for comp, body in default_props_re.findall(text):
                dd = {}
                for line in body.splitlines():
                    m = field_re.match(line.strip().rstrip(','))
                    if m:
                        dd[m.group(1)] = m.group(2).strip()
                if dd:
                    defaults.append({"component": comp, "defaults": dd, "file": f})
            # useState
            for name, init in use_state_re.findall(text):
                state_vars.append({"var": name, "initial": init.strip(), "file": f})
            # destructured defaults in function params
            for params in destruct_default_re.findall(text):
                for dm in destruct_field_re.findall(params):
                    defaults.append({"param_default": {dm[0]: dm[1].strip()}, "file": f})

        # Python extraction: dataclasses and Pydantic models
        dataclass_dec_re = re.compile(r"@dataclass")
        class_re = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(\([A-Za-z0-9_, ]+\))?\s*:\s*")
        field_line_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([^=\n]+?)(?:\s*=\s*(.+))?$")
        base_model_re = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((?:[^)]*BaseModel[^)]*)\)\s*:")
        for f in py_files:
            try:
                text = Path(f).read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            is_dataclass = dataclass_dec_re.search(text) is not None
            for m in class_re.finditer(text):
                cls = m.group(1)
                base_part = m.group(2) or ""
                is_model = ('BaseModel' in base_part)
                # naive body slice
                start = m.end()
                body = []
                for line in text[start:].splitlines():
                    if line and not line.startswith((' ', '\t')):
                        break
                    body.append(line)
                fields = {}
                for line in body:
                    fm = field_line_re.match(line)
                    if fm:
                        name = fm.group(1)
                        type_s = (fm.group(2) or '').strip()
                        default = (fm.group(3) or '').strip()
                        fields[name] = {"type": type_s, "default": default or None}
                        if default:
                            defaults.append({"class": cls, "field": name, "default": default, "file": f})
                if fields:
                    kind = 'dataclass' if is_dataclass else ('pydantic_model' if is_model else 'class')
                    types[cls] = {"kind": kind, "fields": fields, "file": f}

        # Visual graphs (Mermaid)
        class_lines = ["classDiagram"]
        for tname, t in types.items():
            class_lines.append(f"class {tname}")
            fl = t.get('fields') or {}
            for fname, finfo in fl.items():
                ttype = finfo.get('type') if isinstance(finfo, dict) else str(finfo)
                class_lines.append(f"{tname} : {fname} {ttype}")
        graph_lines = ["graph TD"]
        for cname, c in components.items():
            p = c.get('props')
            if p:
                graph_lines.append(f"{cname}--> {re.sub(r'[<> ,]', '_', p)}")

        # Write RAG outputs near a log anchor
        ts = datetime.now().isoformat()
        log_path = self._write_logs("rag_context", {"timestamp": ts, "types_count": len(types), "components_count": len(components), "state_count": len(state_vars)}, title, module)
        out_base = (log_path.parent if log_path else (self.logs_root / ts.split('T')[0] / self._safe_name(module) / self._safe_name(title))) / "rag"
        out_base.mkdir(parents=True, exist_ok=True)
        try:
            (out_base / "index.md").write_text("\n".join([
                "# RAG Context Index",
                f"- Types: {len(types)}",
                f"- Components: {len(components)}",
                f"- State vars: {len(state_vars)}",
                f"- Defaults: {len(defaults)}",
            ]) + "\n", encoding='utf-8')
        except Exception:
            pass
        try:
            tlines = ["# Types"]
            for tn, tv in sorted(types.items()):
                tlines.append(f"\n## {tn} ({tv.get('kind')})\n- File: {tv.get('file')}")
                fl = tv.get('fields') or {}
                for fn, fval in fl.items():
                    if isinstance(fval, dict):
                        tlines.append(f"- {fn}: {fval.get('type')} (default: {fval.get('default')})")
                    else:
                        tlines.append(f"- {fn}: {fval}")
            (out_base / "types.md").write_text("\n".join(tlines) + "\n", encoding='utf-8')
        except Exception:
            pass
        try:
            clines = ["# Components"]
            for cn, cv in sorted(components.items()):
                clines.append(f"\n## {cn}\n- File: {cv.get('file')}\n- Props: {cv.get('props')}")
                p = cv.get('props')
                if p and p in types:
                    clines.append("- Prop fields:")
                    for fn, fval in (types[p].get('fields') or {}).items():
                        if isinstance(fval, dict):
                            clines.append(f"  - {fn}: {fval.get('type')} (default: {fval.get('default')})")
                        else:
                            clines.append(f"  - {fn}: {fval}")
            (out_base / "components.md").write_text("\n".join(clines) + "\n", encoding='utf-8')
        except Exception:
            pass
        try:
            slines = ["# State"]
            for s in state_vars:
                slines.append(f"- {s.get('var')} = {s.get('initial')}  (file: {s.get('file')})")
            (out_base / "state.md").write_text("\n".join(slines) + "\n", encoding='utf-8')
        except Exception:
            pass
        try:
            dlines = ["# Defaults"]
            for d in defaults:
                dlines.append(f"- File: {d.get('file')}  ->  {json.dumps(d)}")
            (out_base / "defaults.md").write_text("\n".join(dlines) + "\n", encoding='utf-8')
        except Exception:
            pass
        try:
            (out_base / "types_graph.mmd").write_text("\n".join(class_lines) + "\n", encoding='utf-8')
            (out_base / "component_props.mmd").write_text("\n".join(graph_lines) + "\n", encoding='utf-8')
        except Exception:
            pass

        # Append knowledge cache
        try:
            kn_dir = self.logs_root / self._safe_name(module)
            kn_dir.mkdir(parents=True, exist_ok=True)
            (kn_dir / "knowledge.jsonl").open("a", encoding='utf-8').write(json.dumps({
                "timestamp": ts,
                "title": title,
                "module": module,
                "types": len(types),
                "components": len(components),
                "state_vars": len(state_vars),
                "defaults": len(defaults),
                "out_dir": str(out_base)
            }) + "\n")
        except Exception:
            pass

        return {"types": len(types), "components": len(components), "state_vars": len(state_vars), "defaults": len(defaults), "out_dir": str(out_base)}

    def compute_rules_hash(self) -> str:
        try:
            # Hash the active config dict for deterministic rules hash
            canonical = json.dumps(self.config, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        except Exception:
            return ""

    def rules_contract_path(self) -> Optional[Path]:
        try:
            rules_dir = self.config.get("rules_dir")
            if rules_dir:
                p = Path(str(rules_dir))
                if p.exists() and p.is_dir():
                    return p / "codex_rules.json"
        except Exception:
            return None
        home = Path.home() / ".claude" / "codex_rules.json"
        return home if home.exists() else None

    def prune_dryrun(self, roots: List[str], entry_points: Optional[List[str]] = None, languages: Optional[List[str]] = None) -> Dict[str, Any]:
        """Suggest removal of extra files and unused symbols (dry-run only)."""
        langs = set((languages or ['python','js']))
        files = self.expand_paths(roots)
        py_files = [f for f in files if f.endswith('.py')] if 'python' in langs else []
        js_files = [f for f in files if any(f.endswith(ext) for ext in ('.js','.jsx','.ts','.tsx','.mjs','.cjs'))] if 'js' in langs else []

        contents: Dict[str, str] = {}
        for f in py_files + js_files:
            try:
                contents[f] = Path(f).read_text(encoding='utf-8', errors='ignore')
            except Exception:
                contents[f] = ''

        stem_to_files: Dict[str, List[str]] = {}
        for f in py_files + js_files:
            stem = Path(f).stem
            stem_to_files.setdefault(stem, []).append(f)

        py_imports: Dict[str, List[str]] = {}
        py_defs: Dict[str, List[str]] = {}
        for f in py_files:
            src = contents.get(f, '')
            imps: List[str] = []
            defs: List[str] = []
            try:
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for n in node.names:
                            imps.append(n.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imps.append(node.module.split('.')[0])
                    elif isinstance(node, ast.FunctionDef):
                        if not node.name.startswith('_'):
                            defs.append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        if not node.name.startswith('_'):
                            defs.append(node.name)
            except Exception:
                pass
            py_imports[f] = imps
            py_defs[f] = defs

        js_imports: Dict[str, List[str]] = {}
        js_defs: Dict[str, List[str]] = {}
        imp_re = re.compile(r"import\s+(?:[^;]+?)\s+from\s+['\"]([^'\"]+)['\"]|require\(\s*['\"]([^'\"]+)['\"]\s*\)")
        exp_fn = re.compile(r"export\s+(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)")
        exp_cls = re.compile(r"export\s+class\s+([A-Za-z_][A-Za-z0-9_]*)")
        exp_var = re.compile(r"export\s+(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)")
        for f in js_files:
            src = contents.get(f, '')
            imps: List[str] = []
            defs: List[str] = []
            try:
                for m in imp_re.finditer(src):
                    target = m.group(1) or m.group(2)
                    if target:
                        imps.append(target)
                defs += [m.group(1) for m in exp_fn.finditer(src)]
                defs += [m.group(1) for m in exp_cls.finditer(src)]
                defs += [m.group(1) for m in exp_var.finditer(src)]
            except Exception:
                pass
            js_imports[f] = imps
            js_defs[f] = defs

        def resolve_import(cur_file: str, spec: str) -> List[str]:
            res: List[str] = []
            if spec.startswith('.'):
                base = Path(cur_file).parent
                cand = (base / spec)
                for ext in ('', '.py','.js','.jsx','.ts','.tsx','.mjs','.cjs'):
                    p = cand if ext=='' else cand.with_suffix(ext)
                    if p.exists() and str(p) in contents:
                        res.append(str(p))
                for ext in ('.py','.js','.ts'):
                    p = cand / ('index'+ext)
                    if p.exists() and str(p) in contents:
                        res.append(str(p))
            else:
                stem = spec.split('/')[-1]
                res.extend(stem_to_files.get(stem, []))
            return res

        graph: Dict[str, List[str]] = {}
        for f in py_files:
            deps: List[str] = []
            for spec in py_imports.get(f, []):
                deps.extend(resolve_import(f, spec))
            graph[f] = list(sorted(set(deps)))
        for f in js_files:
            deps: List[str] = []
            for spec in js_imports.get(f, []):
                deps.extend(resolve_import(f, spec))
            graph[f] = list(sorted(set(graph.get(f, []) + deps)))

        seeds: List[str] = []
        if entry_points:
            for ep in entry_points:
                p = Path(ep)
                if p.exists():
                    seeds.append(str(p.resolve()))
        else:
            candidates = [
                'backend/main.py','backend/start_dev.py','backend/__main__.py',
                'src/index.tsx','src/main.tsx','src/index.ts','src/index.js','src/main.js'
            ]
            for c in candidates:
                for r in roots:
                    p = (Path(r)/c)
                    if p.exists():
                        seeds.append(str(p.resolve()))
        if not seeds:
            seeds = py_files + js_files

        reachable: Set[str] = set()
        stack = list(seeds)
        while stack:
            cur = stack.pop()
            if cur in reachable:
                continue
            reachable.add(cur)
            for dep in graph.get(cur, []):
                if dep not in reachable:
                    stack.append(dep)

        scanned = set(py_files + js_files)
        extra_files = sorted([f for f in scanned if str(Path(f).resolve()) not in reachable])

        symbol_refs: Dict[str, int] = {}
        for f, defs in list(py_defs.items()) + list(js_defs.items()):
            for name in defs:
                count = 0
                pat = re.compile(r"\b"+re.escape(name)+r"\b")
                for text in contents.values():
                    count += len(pat.findall(text))
                symbol_refs[name] = count
        unused_symbols: Dict[str, List[str]] = {}
        for f, defs in list(py_defs.items()) + list(js_defs.items()):
            for name in defs:
                if symbol_refs.get(name, 0) <= 1:
                    unused_symbols.setdefault(f, []).append(name)

        result = {
            'summary': {
                'scanned_files': len(scanned),
                'reachable_files': len(reachable),
                'extra_files': len(extra_files),
                'files_with_unused_symbols': len(unused_symbols)
            },
            'extra_files': extra_files,
            'unused_symbols': unused_symbols,
            'entry_points': seeds,
        }
        ts = datetime.now().isoformat().replace(':','-')
        out = self.reports_dir / f"prune_dryrun_{ts}.json"
        try:
            out.write_text(json.dumps(result, indent=2), encoding='utf-8')
        except Exception:
            pass
        self._log_activity('prune_dryrun', {'roots': roots, 'report': str(out)})
        return result

    def prune_apply(self, roots: List[str], entry_points: Optional[List[str]] = None, languages: Optional[List[str]] = None) -> Dict[str, Any]:
        """Apply prune by deleting extra files and removing unused top-level symbols. Creates backups."""
        res = self.prune_dryrun(roots, entry_points, languages)
        ts = datetime.now().isoformat().replace(':','-')
        backup_root = self.codex_dir / f"prune_backups/{ts}"
        backup_root.mkdir(parents=True, exist_ok=True)

        deleted: List[str] = []
        edited: List[Dict[str, Any]] = []
        errors: List[str] = []

        def _rel_to_allowed(p: Path) -> Path:
            rp = p.resolve()
            for root in self._allowed_roots():
                try:
                    rel = rp.relative_to(root)
                    # Prefix by root name to avoid collisions across roots
                    return Path(self._safe_name(root.name)) / rel
                except Exception:
                    continue
            # Fallback: use drive/anchor-safe path fragments
            try:
                return Path(rp.drive.replace(':','')) / rp.relative_to(rp.anchor)
            except Exception:
                return Path(rp.name)

        # Delete extra files
        for f in res.get('extra_files', []):
            try:
                p = Path(f)
                # Ensure within allowed roots and file exists
                if not self._is_within_allowed(p) or not p.exists() or not p.is_file():
                    continue
                # Backup (preserve relative path within its allowed root)
                bpath = backup_root / _rel_to_allowed(p)
                bpath.parent.mkdir(parents=True, exist_ok=True)
                try:
                    bpath.write_text(p.read_text(encoding='utf-8', errors='ignore'), encoding='utf-8')
                except Exception:
                    # fallback binary copy
                    try:
                        bpath.write_bytes(p.read_bytes())
                    except Exception:
                        pass
                p.unlink()
                deleted.append(f)
            except Exception as e:
                errors.append(f"delete_failed:{f}:{e}")

        # Remove unused symbols (Python only; JS left as suggestions due to parsing limits)
        unused = res.get('unused_symbols', {})
        for f, names in unused.items():
            try:
                p = Path(f)
                if not p.suffix == '.py':
                    continue
                if not self._is_within_allowed(p) or not p.exists() or not p.is_file():
                    continue
                src = p.read_text(encoding='utf-8', errors='ignore')
                # Backup (preserve relative path within its allowed root)
                bpath = backup_root / _rel_to_allowed(p)
                bpath.parent.mkdir(parents=True, exist_ok=True)
                if not bpath.exists():
                    try:
                        bpath.write_text(src, encoding='utf-8')
                    except Exception:
                        try:
                            bpath.write_bytes(p.read_bytes())
                        except Exception:
                            pass
                try:
                    tree = ast.parse(src)
                    to_remove = set(names)
                    new_body = []
                    removed = []
                    for node in tree.body:
                        keep = True
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            if node.name in to_remove and not node.name.startswith('_'):
                                keep = False
                                removed.append(node.name)
                        if keep:
                            new_body.append(node)
                    if removed:
                        tree.body = new_body
                        try:
                            new_src = ast.unparse(tree)
                        except Exception:
                            # fallback: do not modify if unparse fails
                            new_src = None
                        if new_src is not None and new_src.strip() != src.strip():
                            p.write_text(new_src + ("\n" if not new_src.endswith("\n") else ""), encoding='utf-8')
                            edited.append({"file": f, "removed_symbols": removed})
                except Exception as e:
                    errors.append(f"edit_failed:{f}:{e}")
            except Exception as e:
                errors.append(f"edit_failed:{f}:{e}")

        result = {
            "deleted_files": deleted,
            "edited_files": edited,
            "errors": errors,
            "backup_dir": str(backup_root)
        }
        # Persist apply report
        out = self.reports_dir / f"prune_apply_{ts}.json"
        try:
            out.write_text(json.dumps(result, indent=2), encoding='utf-8')
        except Exception:
            pass
        self._log_activity('prune_apply', {"roots": roots, "report": str(out)})
        return result
    
    def remove_debug_statements(self, content: str, file_type: str, filepath: str) -> Tuple[str, int]:
        """Remove debug statements with config awareness and keep-markers."""
        removed_count = 0
        cfg = self.config
        mode = (cfg.get("mode") or "strict").lower()
        remove_prints = bool(cfg.get("remove_prints", True))
        remove_todos = bool(cfg.get("remove_todos", False))
        ignore_tests = bool(cfg.get("ignore_tests_for_prints", True))
        is_test_file = any(seg in filepath.replace("\\", "/").lower() for seg in ["/tests/", "/test_", "_test.py", ".spec.", ".test."])

        def keep_line(line: str) -> bool:
            return "codex: keep" in line or "noqa: codex-keep-print" in line

        lines = content.splitlines()
        new_lines: List[str] = []

        if file_type in ['.py', '.python']:
            for line in lines:
                if remove_todos and re.search(r"^\s*#\s*(TODO|DEBUG)\b", line):
                    removed_count += 1
                    continue
                if remove_prints and not (ignore_tests and is_test_file):
                    if re.match(r"^\s*print\s*\(.*\)\s*(?:#.*)?$", line) and not keep_line(line):
                        if mode == "lenient" and not re.search(r"DEBUG|debug", line):
                            new_lines.append(line)
                        else:
                            removed_count += 1
                        continue
                new_lines.append(line)
        elif file_type in ['.js', '.jsx', '.ts', '.tsx']:
            for line in lines:
                if remove_todos and re.search(r"^\s*//\s*(TODO|DEBUG)\b", line):
                    removed_count += 1
                    continue
                if remove_prints and not (ignore_tests and is_test_file):
                    if re.match(r"^\s*console\.(log|debug|info|warn|error)\s*\(.*\)\s*;?\s*(?://.*)?$", line) and not keep_line(line):
                        if mode == "lenient" and not re.search(r"DEBUG|debug", line):
                            new_lines.append(line)
                        else:
                            removed_count += 1
                        continue
                    if re.match(r"^\s*debugger\s*;?\s*$", line):
                        removed_count += 1
                        continue
                new_lines.append(line)
        else:
            new_lines = lines

        content = "\n".join(new_lines)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        return content, removed_count
    
    def remove_dead_code(self, content: str, file_type: str) -> Tuple[str, int]:
        """Remove commented-out code blocks using safer heuristics."""
        removed_count = 0
        preserve_docblocks = bool(self.config.get("preserve_docblocks", True))

        def is_python_commented_code(line: str) -> bool:
            m = re.match(r"^\s*#\s*(.*)$", line)
            if not m:
                return False
            body = m.group(1).strip()
            if not body:
                return False
            return bool(re.match(r"(def\b|class\b|if\b|for\b|while\b|try\b|except\b|with\b|return\b|from\b|import\b|@|\w+\s*=|\w+\(.*\):?)", body))

        def is_js_codey(text: str) -> bool:
            return bool(re.search(r"\b(function|const|let|var|return|if|for|while|class|=>)\b|=\s*\w|\)\s*\{", text))

        if file_type in ['.py', '.python']:
            lines = content.splitlines()
            new_lines: List[str] = []
            i = 0
            while i < len(lines):
                if lines[i].lstrip().startswith('#'):
                    block: List[str] = []
                    while i < len(lines) and lines[i].lstrip().startswith('#'):
                        block.append(lines[i])
                        i += 1
                    codey = sum(1 for ln in block if is_python_commented_code(ln))
                    if len(block) >= 3 and codey >= max(2, len(block)//2):
                        removed_count += 1
                        continue
                    else:
                        new_lines.extend(block)
                else:
                    new_lines.append(lines[i])
                    i += 1
            content = "\n".join(new_lines)
        elif file_type in ['.js', '.jsx', '.ts', '.tsx']:
            def replace_block(m: re.Match) -> str:
                block = m.group(0)
                if preserve_docblocks and block.startswith("/**"):
                    return block
                inner = re.sub(r"^/\*|\*/$", "", block, flags=re.DOTALL).strip()
                if inner.count("\n") >= 2 and is_js_codey(inner):
                    nonlocal removed_count
                    removed_count += 1
                    return ""
                return block
            content = re.sub(r"/\*[\s\S]*?\*/", replace_block, content)

            lines = content.splitlines()
            new_lines: List[str] = []
            i = 0
            while i < len(lines):
                if lines[i].lstrip().startswith('//'):
                    block: List[str] = []
                    while i < len(lines) and lines[i].lstrip().startswith('//'):
                        block.append(lines[i])
                        i += 1
                    bodies = [re.sub(r"^\s*//\s*", "", ln).strip() for ln in block]
                    codey = sum(1 for b in bodies if is_js_codey(b))
                    if len(block) >= 3 and codey >= max(2, len(block)//2):
                        removed_count += 1
                        continue
                    else:
                        new_lines.extend(block)
                else:
                    new_lines.append(lines[i])
                    i += 1
            content = "\n".join(new_lines)
        return content, removed_count

    def ensure_nonempty_python_blocks(self, content: str) -> str:
        """Ensure Python block headers have a body; insert 'pass' if emptied by cleanup."""
        lines = content.splitlines()
        out: List[str] = []
        i = 0
        header_re = re.compile(r"^([ \t]*)(if |elif |else:|for |while |try:|except |finally:|def |class |with ).*: ?$")
        n = len(lines)
        while i < n:
            line = lines[i]
            out.append(line)
            m = header_re.match(line)
            if m:
                indent = m.group(1)
                header_indent = len(indent.replace('\t', '    '))
                j = i + 1
                # skip blank lines
                while j < n and lines[j].strip() == '':
                    j += 1
                if j >= n:
                    out.append((indent + '    ' + 'pass'))
                else:
                    # compute next line indent
                    nxt = lines[j]
                    nxt_indent = len((re.match(r"^[ \t]*", nxt).group(0)).replace('\t', '    ')) if nxt is not None else 0
                    if nxt.strip().startswith('#'):
                        # if only comments follow before dedent, still ensure body
                        k = j
                        while k < n and lines[k].strip().startswith('#'):
                            k += 1
                        if k >= n or len((re.match(r"^[ \t]*", lines[k]).group(0)).replace('\t','    ')) <= header_indent:
                            out.append((indent + '    ' + 'pass'))
                    elif nxt_indent <= header_indent:
                        out.append((indent + '    ' + 'pass'))
            i += 1
        return "\n".join(out)
    
    def check_file_length(self, content: str, filepath: str) -> List[str]:
        """Check if file exceeds configured limit, with exemptions."""
        issues = []
        path_obj = Path(filepath)
        exempt = self.config.get("length_exempt_patterns") or []
        if exempt and self._match_any(path_obj, exempt):
            return issues
        lines = content.split('\n')
        limit = int(self.config.get("max_file_lines", 500))
        if limit and len(lines) > limit:
            issues.append(f"File {filepath} has {len(lines)} lines (exceeds {limit} line limit)")
        return issues
    
    def score_code_quality(self, issues: List[str], fixes: List[str]) -> float:
        """
        Russian Olympic Judge Scoring
        10.0 = Perfect, zero flaws
        9.5-9.9 = Excellent, minor style issues only
        9.0-9.4 = Very good, small issues
        8.0-8.9 = Good, some cleanup needed
        <9.0 = NOT pristine, must fix
        """
        if not issues and not fixes:
            return 10.0
        
        score = 10.0
        
        # Deduct for issues found
        for issue in issues:
            if "exceeds 500 line" in issue:
                score -= 0.5
            elif "debug statement" in issue.lower():
                score -= 0.2
            elif "dead code" in issue.lower():
                score -= 0.3
            elif "missing docstring" in issue.lower():
                score -= 0.1
            else:
                score -= 0.1
        
        # Bonus for fixes applied
        if len(fixes) > 0:
            score += min(0.2, len(fixes) * 0.05)
        
        return max(0.0, min(10.0, score))
    
    async def take_snapshot(self, paths: List[str]) -> CodexSnapshot:
        """Take pristine snapshot of specified files and persist it"""
        snapshot_files = {}
        file_contents = {}
        
        file_list = self.expand_paths(paths)
        for path in file_list:
            filepath = Path(path)
            if filepath.exists() and filepath.is_file():
                content = filepath.read_text(encoding='utf-8')
                snapshot_files[str(filepath)] = self.calculate_hash(content)
                file_contents[str(filepath)] = content
        
        timestamp = datetime.now().isoformat()
        snapshot = CodexSnapshot(
            timestamp=timestamp,
            files=snapshot_files,
            file_contents=file_contents,
            metadata={
                "workspace": str(self.workspace_root),
                "file_count": len(snapshot_files)
            }
        )
        
        self.snapshot = snapshot
        snap_path = self.snapshots_dir / f"snapshot_{timestamp.replace(':','-')}.json"
        try:
            snap_path.write_text(json.dumps(asdict(snapshot), indent=2), encoding='utf-8')
        except Exception:
            pass
        self._log_activity("snapshot", {"paths": file_list, "snapshot": snap_path.name})
        return snapshot
    
    def _make_diff(self, original: str, modified: str, path: str) -> str:
        if original == modified:
            return ""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
        return "".join(diff)

    async def enforce_quality(self, paths: List[str], auto_fix: bool = True, dry_run: bool = False, title: Optional[str] = None, module: Optional[str] = None) -> CodexReport:
        """Enforce code quality standards on specified files. Supports dry_run."""
        issues = []
        fixes_applied = []
        files_modified = []
        diffs: Dict[str, str] = {}
        
        file_list = self.expand_paths(paths)
        for path in file_list:
            filepath = Path(path)
            if not filepath.exists():
                issues.append(f"File not found: {path}")
                continue
            
            content = filepath.read_text(encoding='utf-8')
            original_content = content
            file_ext = filepath.suffix
            
            # Check file length
            length_issues = self.check_file_length(content, path)
            issues.extend(length_issues)
            
            if auto_fix:
                # Remove debug statements
                content, debug_removed = self.remove_debug_statements(content, file_ext, str(filepath))
                if debug_removed > 0:
                    fixes_applied.append(f"Removed {debug_removed} debug statements from {path}")
                
                # Remove dead code
                content, dead_removed = self.remove_dead_code(content, file_ext)
                if dead_removed > 0:
                    fixes_applied.append(f"Removed {dead_removed} dead code blocks from {path}")
                
                # Python block safety: ensure no empty blocks after cleanup
                if file_ext in ('.py', '.python'):
                    try:
                        content = self.ensure_nonempty_python_blocks(content)
                    except Exception:
                        pass

                # Write back if modified
                if content != original_content:
                    if dry_run:
                        files_modified.append(path)
                    else:
                        filepath.write_text(content, encoding='utf-8')
                        files_modified.append(path)
                    diffs[path] = self._make_diff(original_content, content, path)
        
        # Calculate score
        score = self.score_code_quality(issues, fixes_applied)
        
        report = CodexReport(
            score=score,
            issues=issues,
            fixes_applied=fixes_applied,
            files_modified=files_modified,
            timestamp=datetime.now().isoformat(),
            pristine=score >= 9.0
        )
        report_payload = {
            "score": report.score,
            "pristine": report.pristine,
            "issues": report.issues,
            "fixes_applied": report.fixes_applied,
            "files_modified": report.files_modified,
            "dry_run": dry_run,
            "diffs": diffs,
            "timestamp": report.timestamp,
            "inputs": paths,
            "title": title,
            "module": module,
            "rules_id": self.config.get("rules_id") or self.compute_rules_hash()[:8],
            "rules_hash": self.compute_rules_hash(),
        }
        try:
            rep_path = self.reports_dir / f"enforce_{report.timestamp.replace(':','-')}.json"
            rep_path.write_text(json.dumps(report_payload, indent=2), encoding='utf-8')
        except Exception:
            rep_path = None
        # Also mirror to centralized logs
        self._write_logs("enforce", report_payload, title, module)
        self._log_activity("enforce", {"paths": file_list, "auto_fix": auto_fix, "dry_run": dry_run, "report": rep_path.name if rep_path else None})
        return report

# Initialize server and enforcer
server = mcp.Server("codex-enforcer")
enforcer = CodexEnforcer()

@server.list_tools()
async def list_tools():
    return [
        mcp.Tool(
            name="codex_snapshot",
            description="Take pristine snapshot of specified files for later comparison",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to snapshot"
                    },
                    "label": {"type": "string", "description": "Optional label for this snapshot"}
                },
                "required": ["paths"]
            }
        ),
        mcp.Tool(
            name="codex_rag_context",
            description="Build a human-readable RAG context (types, props, state, defaults, Mermaid graphs)",
            inputSchema={
                "type": "object",
                "properties": {
                    "roots": {"type": "array", "items": {"type": "string"}},
                    "title": {"type": "string"},
                    "module": {"type": "string"}
                },
                "required": ["roots"]
            }
        ),
        mcp.Tool(
            name="codex_rules_contract_get",
            description="Return active rules contract and computed rules hash",
            inputSchema={"type": "object", "properties": {}}
        ),
        mcp.Tool(
            name="codex_rules_contract_set",
            description="Persist a new rules contract to rules_dir (codex_rules.json)",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract": {"type": "object"},
                    "rules_id": {"type": "string"}
                },
                "required": ["contract"]
            }
        ),
        mcp.Tool(
            name="codex_attest_submit",
            description="Submit an attestation (self/peer/recheck) with checklist and evidence",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "enum": ["builder","enforcer","builder_recheck"]},
                    "rules_id": {"type": "string"},
                    "rules_hash": {"type": "string"},
                    "checklist": {"type": "array", "items": {"type": "object"}},
                    "evidence": {"type": "object"},
                    "title": {"type": "string"},
                    "module": {"type": "string"}
                },
                "required": ["agent","rules_id","rules_hash","checklist"]
            }
        ),
        mcp.Tool(
            name="codex_verify_attestations",
            description="Verify required attestations exist and share rules hash",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "module": {"type": "string"},
                    "date": {"type": "string"},
                    "require": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["title","module"]
            }
        ),
        mcp.Tool(
            name="codex_gate_finalize",
            description="Finalize enforcement gate if attestations verified",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "module": {"type": "string"},
                    "rules_id": {"type": "string"}
                },
                "required": ["title","module","rules_id"]
            }
        ),
        mcp.Tool(
            name="codex_enforce",
            description="Enforce code quality standards and clean up code (supports dry_run)",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to enforce"
                    },
                    "auto_fix": {
                        "type": "boolean",
                        "description": "Automatically apply fixes",
                        "default": True
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview changes without writing",
                        "default": False
                    },
                    "title": {"type": "string", "description": "Optional human title for this run"},
                    "module": {"type": "string", "description": "Optional module/category label"}
                },
                "required": ["paths"]
            }
        ),
        mcp.Tool(
            name="codex_validate",
            description="Validate code meets pristine standards (9.0+ score required)",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to validate"
                    }
                },
                "required": ["paths"]
            }
        ),
        mcp.Tool(
            name="codex_restore",
            description="Restore files from the most recent snapshot or by id",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "snapshot_id": {"type": "string", "description": "snapshot timestamp or filename"}
                },
                "required": ["paths"]
            }
        ),
        mcp.Tool(
            name="codex_version",
            description="Show Codex Enforcer version and active configuration",
            inputSchema={"type": "object", "properties": {}}
        ),
        mcp.Tool(
            name="codex_activity",
            description="Show recent Codex activity (snapshots, enforcements)",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 50}},
                "required": []
            }
        ),
        mcp.Tool(
            name="codex_set_allowed_roots",
            description="Set allowed root directories Codex is permitted to modify",
            inputSchema={
                "type": "object",
                "properties": {"roots": {"type": "array", "items": {"type": "string"}}},
                "required": ["roots"]
            }
        ),
        mcp.Tool(
            name="codex_prune_dryrun",
            description="Analyze and propose removal of extra files and unused symbols (no writes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "roots": {"type": "array", "items": {"type": "string"}},
                    "entry_points": {"type": "array", "items": {"type": "string"}},
                    "languages": {"type": "array", "items": {"type": "string"}},
                    "title": {"type": "string"},
                    "module": {"type": "string"}
                },
                "required": ["roots"]
            }
        ),
        mcp.Tool(
            name="codex_prune_apply",
            description="Apply prune: delete extra files and remove unused symbols (creates backups)",
            inputSchema={
                "type": "object",
                "properties": {
                    "roots": {"type": "array", "items": {"type": "string"}},
                    "entry_points": {"type": "array", "items": {"type": "string"}},
                    "languages": {"type": "array", "items": {"type": "string"}},
                    "confirm": {"type": "boolean", "default": False},
                    "title": {"type": "string"},
                    "module": {"type": "string"}
                },
                "required": ["roots"]
            }
        ),
        mcp.Tool(
            name="codex_set_rules_dir",
            description="Set and persist the external rules directory (Claude MD folder)",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        ),
        mcp.Tool(
            name="codex_context_index",
            description="Index a project into a universal context template (writes .codex/context_index.json)",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {"type": "string"},
                    "max_depth": {"type": "integer", "default": 3},
                    "include_hidden": {"type": "boolean", "default": False},
                    "title": {"type": "string"},
                    "module": {"type": "string"}
                },
                "required": ["root"]
            }
        ),
        mcp.Tool(
            name="codex_context_init",
            description="Alias for codex_context_index (initialize context index)",
            inputSchema={
                "type": "object",
                "properties": {
                    "root": {"type": "string"},
                    "max_depth": {"type": "integer", "default": 3},
                    "include_hidden": {"type": "boolean", "default": False},
                    "title": {"type": "string"},
                    "module": {"type": "string"}
                },
                "required": ["root"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]):
    if name == "codex_snapshot":
        snapshot = await enforcer.take_snapshot(arguments["paths"])
        return [mcp.TextContent(
            type="text",
            text=json.dumps({
                "status": "snapshot_taken",
                "timestamp": snapshot.timestamp,
                "files_captured": len(snapshot.files),
                "files": list(snapshot.files.keys())
            }, indent=2)
        )]
    
    elif name == "codex_enforce":
        report = await enforcer.enforce_quality(
            arguments["paths"],
            arguments.get("auto_fix", True),
            arguments.get("dry_run", False),
            arguments.get("title"),
            arguments.get("module")
        )
        return [mcp.TextContent(
            type="text",
            text=json.dumps({
                "score": report.score,
                "pristine": report.pristine,
                "issues": report.issues,
                "fixes_applied": report.fixes_applied,
                "files_modified": report.files_modified,
                "recommendation": "APPROVED" if report.pristine else "NEEDS WORK"
            }, indent=2)
        )]
    
    elif name == "codex_validate":
        report = await enforcer.enforce_quality(
            arguments["paths"],
            auto_fix=False  # Just validate, don't fix
        )
        
        validation = {
            "score": report.score,
            "pristine": report.pristine,
            "status": "PASS" if report.pristine else "FAIL",
            "issues": report.issues,
            "required_score": 9.0,
            "recommendation": "Ready for production" if report.pristine else "Needs cleanup"
        }
        
        return [mcp.TextContent(
            type="text",
            text=json.dumps(validation, indent=2)
        )]
    elif name == "codex_restore":
        snap_id = arguments.get("snapshot_id")
        snap_file: Optional[Path] = None
        if snap_id:
            candidate = enforcer.snapshots_dir / (snap_id if snap_id.endswith('.json') else f"snapshot_{snap_id.replace(':','-')}.json")
            if candidate.exists():
                snap_file = candidate
        if snap_file is None:
            snaps = sorted(enforcer.snapshots_dir.glob("snapshot_*.json"))
            snap_file = snaps[-1] if snaps else None
        if not snap_file or not snap_file.exists():
            return [mcp.TextContent(type="text", text=json.dumps({"status": "no_snapshot"}, indent=2))]
        snap = json.loads(snap_file.read_text(encoding='utf-8'))
        files = snap.get("file_contents", {})
        restored: List[str] = []
        missing: List[str] = []
        for p in enforcer.expand_paths(arguments.get("paths", [])):
            if p in files:
                Path(p).write_text(files[p], encoding='utf-8')
                restored.append(p)
            else:
                missing.append(p)
        return [mcp.TextContent(type="text", text=json.dumps({
            "status": "restored",
            "snapshot": snap.get("timestamp"),
            "restored": restored,
            "missing": missing
        }, indent=2))]
    elif name == "codex_version":
        cfg = enforcer.config
        info = {
            "name": "codex-enforcer",
            "version": "1.1.0",
            "workspace": str(enforcer.workspace_root),
            "config": cfg
        }
        return [mcp.TextContent(type="text", text=json.dumps(info, indent=2))]
    elif name == "codex_activity":
        limit = int(arguments.get("limit", 50))
        entries: List[str] = []
        try:
            if enforcer.activity_log.exists():
                lines = enforcer.activity_log.read_text(encoding="utf-8").splitlines()
                entries = lines[-limit:]
        except Exception:
            pass
        return [mcp.TextContent(type="text", text=json.dumps({"entries": [json.loads(e) for e in entries if e.strip()]}, indent=2))]
    elif name == "codex_set_allowed_roots":
        roots = arguments.get("roots", [])
        enforcer.config["allowed_roots"] = roots
        try:
            cfg_path = enforcer.workspace_root / "codex_config.json"
            current = {}
            if cfg_path.exists():
                current = json.loads(cfg_path.read_text(encoding="utf-8"))
            current["allowed_roots"] = roots
            cfg_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        except Exception:
            pass
        enforcer._log_activity("set_allowed_roots", {"roots": roots})
        return [mcp.TextContent(type="text", text=json.dumps({"status": "ok", "allowed_roots": roots}, indent=2))]
    elif name == "codex_set_rules_dir":
        path = arguments.get("path")
        d = Path(path)
        if not d.exists() or not d.is_dir():
            return [mcp.TextContent(type="text", text=json.dumps({"error": "rules_dir_not_found", "path": path}, indent=2))]
        enforcer.config["rules_dir"] = str(d)
        # Persist to workspace config
        try:
            cfg_path = enforcer.workspace_root / "codex_config.json"
            current = {}
            if cfg_path.exists():
                current = json.loads(cfg_path.read_text(encoding="utf-8"))
            current["rules_dir"] = str(d)
            cfg_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        except Exception:
            pass
        enforcer._log_activity("set_rules_dir", {"rules_dir": str(d)})
        return [mcp.TextContent(type="text", text=json.dumps({"status": "ok", "rules_dir": str(d)}, indent=2))]
    elif name == "codex_context_index" or name == "codex_context_init":
        root = Path(arguments.get("root"))
        max_depth = int(arguments.get("max_depth", 3))
        include_hidden = bool(arguments.get("include_hidden", False))
        if not root.exists() or not root.is_dir():
            return [mcp.TextContent(type="text", text=json.dumps({"error": "root_not_found"}, indent=2))]
        if not enforcer._is_within_allowed(root):
            return [mcp.TextContent(type="text", text=json.dumps({"error": "root_outside_allowed"}, indent=2))]

        def is_hidden(p: Path) -> bool:
            name = p.name
            return name.startswith('.') and name not in {'.env'}

        tree: Dict[str, Any] = {}
        exclude = enforcer.config.get("exclude", [])
        exts = set(enforcer.config.get("extensions", []))

        def build_tree(dir_path: Path, depth: int) -> Any:
            if depth > max_depth:
                return "…"
            items = []
            try:
                for p in sorted(dir_path.iterdir(), key=lambda x: x.name.lower()):
                    if not include_hidden and is_hidden(p):
                        continue
                    if enforcer._match_any(p, exclude):
                        continue
                    if p.is_dir():
                        items.append({"dir": p.name, "children": build_tree(p, depth + 1)})
                    else:
                        if not exts or p.suffix in exts:
                            try:
                                size = p.stat().st_size
                            except Exception:
                                size = None
                            items.append({"file": p.name, "size": size})
            except Exception:
                return "(unreadable)"
            return items

        tree = {"root": str(root), "structure": build_tree(root, 0)}

        meta: Dict[str, Any] = {}
        def read_json(p: Path) -> Optional[Dict[str, Any]]:
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None

        pkg = root / "package.json"
        if pkg.exists():
            pj = read_json(pkg)
            if pj:
                meta["node"] = {
                    "name": pj.get("name"),
                    "scripts": pj.get("scripts", {}),
                    "dependencies": list((pj.get("dependencies") or {}).keys()),
                    "devDependencies": list((pj.get("devDependencies") or {}).keys())
                }
        req = root / "requirements.txt"
        if req.exists():
            try:
                lines = [ln.strip() for ln in req.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith('#')]
                meta["python_requirements"] = lines
            except Exception:
                pass
        pyproj = root / "pyproject.toml"
        if pyproj.exists():
            try:
                text = pyproj.read_text(encoding="utf-8")
                deps = re.findall(r"^\s*dependencies\s*=\s*\[(.*?)\]", text, flags=re.MULTILINE | re.DOTALL)
                if deps:
                    inner = deps[0]
                    pkgs = re.findall(r"\"([^\"]+)\"", inner)
                    meta["python_pyproject_deps"] = pkgs
            except Exception:
                pass

        # Go modules (go.mod)
        gomod = root / "go.mod"
        if gomod.exists():
            try:
                lines = gomod.read_text(encoding="utf-8").splitlines()
                module_name = None
                requires: List[str] = []
                in_require_block = False
                for ln in lines:
                    if ln.startswith("module "):
                        module_name = ln.split(" ", 1)[1].strip()
                    if ln.strip().startswith("require ("):
                        in_require_block = True
                        continue
                    if in_require_block and ln.strip().startswith(")"):
                        in_require_block = False
                        continue
                    if in_require_block:
                        parts = ln.strip().split()
                        if parts:
                            requires.append(parts[0])
                    elif ln.strip().startswith("require "):
                        parts = ln.strip().split()
                        if len(parts) >= 2:
                            requires.append(parts[1])
                meta["golang"] = {"module": module_name, "requires": requires}
            except Exception:
                pass

        # Rust (Cargo.toml)
        cargo = root / "Cargo.toml"
        if cargo.exists():
            try:
                text = cargo.read_text(encoding="utf-8")
                # package name
                m = re.search(r"\[package\][\s\S]*?^name\s*=\s*\"([^\"]+)\"", text, flags=re.MULTILINE)
                pkg_name = m.group(1) if m else None
                # dependencies section lines
                deps: List[str] = []
                dm = re.search(r"^\[dependencies\][\s\S]*?(?=^\[|\Z)", text, flags=re.MULTILINE)
                if dm:
                    block = dm.group(0)
                    for ln in block.splitlines():
                        ln = ln.strip()
                        if not ln or ln.startswith('#') or ln.startswith('['):
                            continue
                        deps.append(ln.split('=')[0].strip())
                meta["rust"] = {"package": pkg_name, "dependencies": deps}
            except Exception:
                pass

        index = {"tree": tree, "meta": meta, "generated_at": datetime.now().isoformat()}
        out = enforcer.codex_dir / "context_index.json"
        try:
            out.write_text(json.dumps(index, indent=2), encoding="utf-8")
        except Exception:
            pass
        # Mirror to centralized logs with optional title/module
        enforcer._write_logs(
            "context_index",
            {"timestamp": datetime.now().isoformat(), "root": str(root), "index_summary": {"entries": len(tree.get("structure", [])) if isinstance(tree.get("structure"), list) else None}},
            arguments.get("title"),
            arguments.get("module")
        )
        enforcer._log_activity("context_index", {"root": str(root), "file": str(out)})
        return [mcp.TextContent(type="text", text=json.dumps(index, indent=2))]
    elif name == "codex_prune_dryrun":
        res = enforcer.prune_dryrun(
            arguments.get("roots", []),
            arguments.get("entry_points"),
            arguments.get("languages")
        )
        enforcer._write_logs("prune_dryrun", {"timestamp": datetime.now().isoformat(), **res}, arguments.get("title"), arguments.get("module"))
        return [mcp.TextContent(type="text", text=json.dumps(res, indent=2))]
    elif name == "codex_prune_apply":
        if not arguments.get("confirm", False):
            preview = enforcer.prune_dryrun(
                arguments.get("roots", []),
                arguments.get("entry_points"),
                arguments.get("languages")
            )
            return [mcp.TextContent(type="text", text=json.dumps({"preview": preview, "note": "Set confirm=true to apply."}, indent=2))]
        applied = enforcer.prune_apply(
            arguments.get("roots", []),
            arguments.get("entry_points"),
            arguments.get("languages")
        )
        enforcer._write_logs("prune_apply", {"timestamp": datetime.now().isoformat(), **applied}, arguments.get("title"), arguments.get("module"))
        return [mcp.TextContent(type="text", text=json.dumps(applied, indent=2))]
    elif name == "codex_rules_contract_get":
        rules_path = enforcer.rules_contract_path()
        contract = enforcer.config
        if rules_path and rules_path.exists():
            try:
                contract = json.loads(rules_path.read_text(encoding='utf-8'))
            except Exception:
                pass
        res = {
            "rules_id": enforcer.config.get("rules_id") or enforcer.compute_rules_hash()[:8],
            "rules_hash": enforcer.compute_rules_hash(),
            "contract": contract,
            "rules_path": str(rules_path) if rules_path else None
        }
        return [mcp.TextContent(type="text", text=json.dumps(res, indent=2))]
    elif name == "codex_rules_contract_set":
        rules_dir = enforcer.config.get("rules_dir") or str((Path.home() / ".claude"))
        target = Path(rules_dir) / "codex_rules.json"
        contract = arguments.get("contract", {})
        rid = arguments.get("rules_id")
        try:
            Path(rules_dir).mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(contract, indent=2), encoding='utf-8')
            if rid:
                enforcer.config["rules_id"] = rid
        except Exception as e:
            return [mcp.TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]
        res = {"status": "ok", "rules_path": str(target)}
        return [mcp.TextContent(type="text", text=json.dumps(res, indent=2))]
    elif name == "codex_attest_submit":
        agent = arguments.get("agent")
        rules_id = arguments.get("rules_id")
        rules_hash = arguments.get("rules_hash")
        checklist = arguments.get("checklist") or []
        evidence = arguments.get("evidence") or {}
        ts = datetime.now().isoformat()
        payload = {"timestamp": ts, "agent": agent, "rules_id": rules_id, "rules_hash": rules_hash, "checklist": checklist, "evidence": evidence}
        out = enforcer._write_logs("attest_" + str(agent), payload, arguments.get("title"), arguments.get("module"))
        res = {"status": "ok", "path": str(out) if out else None}
        return [mcp.TextContent(type="text", text=json.dumps(res, indent=2))]
    elif name == "codex_verify_attestations":
        date = arguments.get("date") or datetime.now().isoformat().split("T")[0]
        module = enforcer._safe_name(arguments.get("module"))
        title = enforcer._safe_name(arguments.get("title"))
        dirpath = enforcer.logs_root / date / module / title
        require = set(arguments.get("require") or ["builder","enforcer","builder_recheck"])
        found = {}
        rhash = None
        try:
            for p in dirpath.glob("attest_*.json"):
                data = json.loads(p.read_text(encoding='utf-8'))
                ag = data.get("agent")
                if ag:
                    found[ag] = data
                    rh = data.get("rules_hash")
                    if rhash is None:
                        rhash = rh
                    elif rh and rh != rhash:
                        return [mcp.TextContent(type="text", text=json.dumps({"status": "mismatch_rules_hash", "path": str(p)}, indent=2))]
        except Exception:
            pass
        missing = [r for r in require if r not in found]
        status = "ok" if not missing else "missing_attestations"
        return [mcp.TextContent(type="text", text=json.dumps({"status": status, "missing": missing, "rules_hash": rhash, "dir": str(dirpath)}, indent=2))]
    elif name == "codex_gate_finalize":
        title = enforcer._safe_name(arguments.get("title"))
        module = enforcer._safe_name(arguments.get("module"))
        date = datetime.now().isoformat().split("T")[0]
        dirpath = enforcer.logs_root / date / module / title
        # Verify attestations
        verify_res = await call_tool("codex_verify_attestations", {"title": title, "module": module, "date": date})
        ver = {}
        try:
            ver = json.loads(verify_res[0].text)
        except Exception:
            pass
        status = "pass" if ver.get("status") == "ok" else "fail"
        result = {"timestamp": datetime.now().isoformat(), "status": status, "rules_id": arguments.get("rules_id")}
        try:
            (dirpath / "gate_result.json").write_text(json.dumps(result, indent=2), encoding='utf-8')
            enforcer._write_summary_markdown(dirpath, f"gate_result — {title}", result)
        except Exception:
            pass
        return [mcp.TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "codex_rag_context":
        roots = arguments.get("roots", [])
        out = enforcer.build_rag_context(roots, arguments.get("title"), arguments.get("module"))
        return [mcp.TextContent(type="text", text=json.dumps(out, indent=2))]
    
    return [mcp.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
