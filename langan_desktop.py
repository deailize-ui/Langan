import os, sys, json, hashlib, secrets, threading, queue, importlib.util, urllib.request
from pathlib import Path
from html.parser import HTMLParser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

APP_NAME = "Langan Explorer Desktop"
MODEL_FILE = "SmolLM2-360M-Instruct-Q5_0.gguf"
DEFAULT_SOURCES = ["https://en.wikipedia.org/", "https://www.britannica.com/"]

def app_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

def resource_path(name):
    root = Path(getattr(sys, "_MEIPASS", app_dir()))
    candidate = root / name
    return candidate if candidate.exists() else app_dir() / name

DATA_DIR = app_dir() / "data"
DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"
LOGIC_FILE = DATA_DIR / "logic_engine.py"

DEFAULT_LOGIC = '''# Langan Explorer custom Python logic engine.
# Add your own trusted Python logic here.
# Optional function: analyze_problem(problem: str) -> dict

def analyze_problem(problem):
    return {
        "facts": [],
        "candidate_premises": [],
        "missing_information": [],
        "possible_conclusions": []
    }
'''

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip: self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            clean = " ".join(data.split())
            if clean: self.parts.append(clean)

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 250000).hex()

def load_settings():
    if not SETTINGS_FILE.exists():
        s = {"password_salt": secrets.token_hex(16), "password_hash": "", "sources": DEFAULT_SOURCES}
        SETTINGS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")
        return s
    try: s = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception: s = {}
    s.setdefault("password_salt", secrets.token_hex(16))
    s.setdefault("password_hash", "")
    s.setdefault("sources", DEFAULT_SOURCES)
    return s

class LanganApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)
        self.root.configure(bg="#101713")
        self.settings = load_settings()
        if not LOGIC_FILE.exists(): LOGIC_FILE.write_text(DEFAULT_LOGIC, encoding="utf-8")
        self.model, self.events = None, queue.Queue()
        self.logic_unlocked = False
        self._style()
        self._build()
        self.root.after(150, self._poll_events)
        self.root.after(350, self._load_model)
        if not self.settings["password_hash"]: self.root.after(900, self._set_new_password)

    def _style(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except Exception: pass
        s.configure("TNotebook", background="#101713", borderwidth=0)
        s.configure("TNotebook.Tab", background="#202c25", foreground="#dce8df", padding=(18, 10))
        s.map("TNotebook.Tab", background=[("selected", "#176b45")], foreground=[("selected", "white")])
        s.configure("TButton", padding=8, background="#176b45", foreground="white", borderwidth=0)
        s.map("TButton", background=[("active", "#20885a")])
        s.configure("TLabel", background="#101713", foreground="#e6eee8")
        s.configure("TFrame", background="#101713")
        s.configure("TEntry", fieldbackground="#1b2820", foreground="#e6eee8")

    def _label(self, parent, text):
        return tk.Label(parent, text=text, bg="#101713", fg="#c9d9ce", font=("Segoe UI", 10, "bold"))

    def _text(self, parent, height):
        return tk.Text(parent, height=height, bg="#17231b", fg="#e7f1e9", insertbackground="white",
                       relief="flat", wrap="word", font=("Consolas", 10), padx=10, pady=8)

    def _build(self):
        head = tk.Frame(self.root, bg="#101713"); head.pack(fill="x", padx=24, pady=(18, 8))
        tk.Label(head, text="LANGAN EXPLORER", bg="#101713", fg="#7ee0a8",
                 font=("Segoe UI", 20, "bold")).pack(side="left")
        self.model_status = tk.Label(head, text="Loading local model…", bg="#101713", fg="#f0c674")
        self.model_status.pack(side="right")
        tk.Label(self.root, text="Local AI analysis • editable logic • configurable evidence sources",
                 bg="#101713", fg="#9eafa4").pack(anchor="w", padx=26, pady=(0, 12))
        tabs = ttk.Notebook(self.root); tabs.pack(fill="both", expand=True, padx=20, pady=10)
        a, l, e = ttk.Frame(tabs), ttk.Frame(tabs), ttk.Frame(tabs)
        tabs.add(a, text="  ANALYZE  "); tabs.add(l, text="  LOGIC ENGINE  "); tabs.add(e, text="  EVIDENCE SOURCES  ")
        self._build_analysis(a); self._build_logic(l); self._build_sources(e)
        tk.Label(self.root, text="Experimental prototype: AI output and retrieved excerpts are not proof.",
                 bg="#101713", fg="#819187").pack(anchor="w", padx=24, pady=(0, 12))

    def _build_analysis(self, f):
        self._label(f, "Describe the problem").pack(anchor="w", padx=18, pady=(16, 6))
        self.problem = self._text(f, 7); self.problem.pack(fill="x", padx=18)
        row = tk.Frame(f, bg="#101713"); row.pack(fill="x", padx=18, pady=10)
        ttk.Button(row, text="Analyze problem", command=self._analyze).pack(side="left")
        ttk.Button(row, text="Research configured sources", command=self._research).pack(side="left", padx=8)
        ttk.Button(row, text="Clear", command=lambda: self.problem.delete("1.0", "end")).pack(side="left")
        self._label(f, "Analysis and logic-engine output").pack(anchor="w", padx=18, pady=(8, 6))
        self.output = self._text(f, 18); self.output.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        self.output.insert("1.0", "Enter a problem, then select Analyze problem.")

    def _build_logic(self, f):
        tk.Label(f, text="Administrator-only Python logic engine editor", bg="#101713", fg="#7ee0a8",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(16, 5))
        tk.Label(f, text="Unlock with your private password. Saved Python code runs with your Windows account permissions.",
                 bg="#101713", fg="#aebdb2").pack(anchor="w", padx=18, pady=(0, 10))
        row = tk.Frame(f, bg="#101713"); row.pack(fill="x", padx=18, pady=5)
        ttk.Button(row, text="Unlock editor", command=self._unlock_logic).pack(side="left")
        ttk.Button(row, text="Save code", command=self._save_logic).pack(side="left", padx=8)
        ttk.Button(row, text="Change admin password", command=self._change_password).pack(side="right")
        self.logic_editor = self._text(f, 27); self.logic_editor.pack(fill="both", expand=True, padx=18, pady=10)
        self.logic_editor.insert("1.0", "# Locked. Select Unlock editor.")
        self.logic_editor.configure(state="disabled")

    def _build_sources(self, f):
        tk.Label(f, text="Configure websites to consult for evidence", bg="#101713", fg="#7ee0a8",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(18, 8))
        tk.Label(f, text="Enter full public page URLs, one per line. The app fetches text from these pages. It does not crawl whole websites or verify claims.",
                 bg="#101713", fg="#aebdb2", wraplength=950, justify="left").pack(anchor="w", padx=18, pady=(0, 10))
        self.sources_text = self._text(f, 18); self.sources_text.pack(fill="both", expand=True, padx=18, pady=5)
        self.sources_text.insert("1.0", "\n".join(self.settings["sources"]))
        row = tk.Frame(f, bg="#101713"); row.pack(fill="x", padx=18, pady=10)
        ttk.Button(row, text="Save evidence sources", command=self._save_sources).pack(side="left")
        ttk.Button(row, text="Restore defaults", command=lambda: self._restore_sources()).pack(side="left", padx=8)

    def _save_settings(self):
        SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")

    def _set_new_password(self):
        p1 = simpledialog.askstring("Create administrator password", "Create a password (minimum 8 characters):", show="*")
        if p1 is None: return
        if len(p1) < 8:
            messagebox.showerror("Password too short", "Use at least 8 characters."); return self._set_new_password()
        p2 = simpledialog.askstring("Confirm password", "Enter it again:", show="*")
        if p1 != p2:
            messagebox.showerror("Mismatch", "Passwords do not match."); return self._set_new_password()
        self.settings["password_hash"] = password_hash(p1, self.settings["password_salt"])
        self._save_settings()
        messagebox.showinfo("Password saved", "Administrator password saved on this computer.")

    def _check_password(self):
        if not self.settings["password_hash"]:
            self._set_new_password()
            return bool(self.settings["password_hash"])
        p = simpledialog.askstring("Administrator access", "Enter administrator password:", show="*")
        if p is None: return False
        good = secrets.compare_digest(password_hash(p, self.settings["password_salt"]), self.settings["password_hash"])
        if not good: messagebox.showerror("Access denied", "Incorrect password.")
        return good

    def _unlock_logic(self):
        if not self._check_password(): return
        self.logic_editor.configure(state="normal")
        self.logic_editor.delete("1.0", "end")
        self.logic_editor.insert("1.0", LOGIC_FILE.read_text(encoding="utf-8"))
        messagebox.showinfo("Unlocked", "Python logic editor unlocked.")

    def _save_logic(self):
        if str(self.logic_editor.cget("state")) == "disabled":
            messagebox.showwarning("Locked", "Unlock the editor first."); return
        code = self.logic_editor.get("1.0", "end-1c")
        try: compile(code, str(LOGIC_FILE), "exec")
        except SyntaxError as e:
            messagebox.showerror("Python syntax error", f"Line {e.lineno}: {e.msg}"); return
        backup = LOGIC_FILE.with_suffix(".py.bak")
        if LOGIC_FILE.exists(): backup.write_text(LOGIC_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        LOGIC_FILE.write_text(code, encoding="utf-8")
        messagebox.showinfo("Saved", f"Logic code saved. Backup: {backup.name}\nIt will be loaded on the next analysis.")

    def _change_password(self):
        if self._check_password(): self._set_new_password()

    def _save_sources(self):
        urls = [x.strip() for x in self.sources_text.get("1.0", "end").splitlines() if x.strip()]
        if any(not x.startswith(("https://", "http://")) for x in urls):
            messagebox.showerror("Invalid URL", "Every source must begin with http:// or https://."); return
        self.settings["sources"] = urls; self._save_settings()
        messagebox.showinfo("Saved", f"{len(urls)} source URL(s) saved.")

    def _restore_sources(self):
        self.sources_text.delete("1.0", "end")
        self.sources_text.insert("1.0", "\n".join(DEFAULT_SOURCES))

    def _load_model(self):
        path = resource_path("models/" + MODEL_FILE)
        if not path.exists():
            self.model_status.config(text="Model file missing", fg="#ff9c82")
            self._append("MODEL FILE MISSING. Run DOWNLOAD_MODEL.bat and then build the EXE again.\n")
            return
        self.model_status.config(text="Loading SmolLM2…", fg="#f0c674")
        threading.Thread(target=self._model_worker, args=(str(path),), daemon=True).start()

    def _model_worker(self, path):
        try:
            from llama_cpp import Llama
            llm = Llama(model_path=path, n_ctx=2048, n_threads=max(2, (os.cpu_count() or 4)-1), verbose=False)
            self.events.put(("model_ok", llm))
        except Exception as e: self.events.put(("model_error", str(e)))

    def _poll_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "model_ok":
                    self.model = payload; self.model_status.config(text="SmolLM2 ready • offline", fg="#7ee0a8")
                    self._append("SmolLM2 loaded. Basic analysis can run offline.\n\n")
                elif kind == "model_error":
                    self.model_status.config(text="Model load failed", fg="#ff9c82"); self._append("MODEL ERROR: " + payload + "\n")
                elif kind == "output": self._append(payload)
        except queue.Empty: pass
        self.root.after(150, self._poll_events)

    def _append(self, text):
        self.output.configure(state="normal"); self.output.insert("end", text); self.output.see("end")

    def _run_model(self, prompt):
        if self.model is None: raise RuntimeError("Local model is not ready. Check the model status.")
        result = self.model.create_chat_completion(
            messages=[
                {"role": "system", "content": "You are Langan Explorer. Separate explicit facts from assumptions. An intended action is not proof it happened. Do not invent facts. Say unknown when necessary."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, max_tokens=700, response_format={"type": "json_object"}
        )
        parsed = json.loads(result["choices"][0]["message"]["content"])
        for key in ("facts", "candidate_premises", "missing_information", "possible_conclusions"):
            if not isinstance(parsed.get(key), list): parsed[key] = []
        return parsed

    def _load_custom_logic(self):
        spec = importlib.util.spec_from_file_location("langan_custom_logic", LOGIC_FILE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def _analyze(self):
        problem = self.problem.get("1.0", "end").strip()
        if not problem: messagebox.showwarning("Problem required", "Enter a problem first."); return
        self._append("\n" + "="*65 + "\nANALYSIS IN PROGRESS…\n")
        threading.Thread(target=self._analysis_worker, args=(problem,), daemon=True).start()

    def _analysis_worker(self, problem):
        try:
            prompt = ("Return ONLY a JSON object with four list-of-string keys: facts, candidate_premises, "
                      "missing_information, possible_conclusions. Facts must be explicitly stated. An intended action "
                      "is not proof it happened. Do not invent details or turn unknowns into conclusions.\n\nPROBLEM:\n" + problem)
            ai = self._run_model(prompt)
            try:
                module = self._load_custom_logic()
                fn = getattr(module, "analyze_problem", None)
                logic = fn(problem) if callable(fn) else {"notice": "No analyze_problem function found."}
            except Exception as e: logic = {"logic_engine_error": str(e)}
            output = {"AI analysis": ai, "Custom logic engine": logic,
                      "warning": "AI and custom-code outputs are suggestions, not proof. Verify independently."}
            self.events.put(("output", json.dumps(output, indent=2, ensure_ascii=False) + "\n"))
        except Exception as e: self.events.put(("output", "ANALYSIS ERROR: " + str(e) + "\n"))

    def _research(self):
        query = self.problem.get("1.0", "end").strip()
        if not query: messagebox.showwarning("Problem required", "Enter a claim to research."); return
        self._append("\nRESEARCHING CONFIGURED SOURCES…\n")
        threading.Thread(target=self._research_worker, args=(query,), daemon=True).start()

    def _research_worker(self, query):
        results = []
        for url in self.settings.get("sources", []):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "LanganExplorerDesktop/1.0"})
                with urllib.request.urlopen(req, timeout=15) as response:
                    raw = response.read(1000000).decode("utf-8", errors="ignore")
                parser = TextExtractor(); parser.feed(raw)
                results.append({"source": url, "excerpt": " ".join(parser.parts)[:5000]})
            except Exception as e: results.append({"source": url, "error": str(e)})
        self.events.put(("output", "RESEARCH RESULTS — leads only, not verified facts:\n" +
                         json.dumps(results, indent=2, ensure_ascii=False) + "\n"))

def main():
    root = tk.Tk()
    LanganApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
