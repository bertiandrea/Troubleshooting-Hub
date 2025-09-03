import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess, threading
from datetime import datetime

# ==========================
# CONFIGURAZIONE
# ==========================
CONFIG = {
    "window": {"title": "Troubleshooting Hub", "width_ratio": 0.8, "height_ratio": 0.8},
    "console": {"bg": "#1e1e1e", "fg": "#ffffff"},
    "postit": {"bg": "#fff9c4", "relief": "raised", "border": 2},
    "modules": [
        {
            "title": "Configurazione Rete",
            "commands": [
                {"name": "IP Config", "cmd": "ipconfig"},
                {"name": "IP Config Dettagliato", "cmd": "ipconfig /all"},
                {"name": "Rilascia IP", "cmd": "ipconfig /release"},
                {"name": "Rinnova IP", "cmd": "ipconfig /renew"},
                {"name": "Svuota Cache DNS", "cmd": "ipconfig /flushdns"},
                {"name": "Mostra Cache DNS", "cmd": "ipconfig /displaydns"},
            ],
        },
        {
            "title": "Test Connettività",
            "input_host": True,
            "input_port": True,
            "commands": [
                {"name": "Ping", "cmd": lambda app: f"ping {app.host_entry.get()}"},
                {"name": "Ping Continuo", "cmd": lambda app: f"ping -t {app.host_entry.get()}", "continuous": True},
                {"name": "Traceroute", "cmd": lambda app: f"tracert {app.host_entry.get()}"},
                {"name": "Traceroute (no DNS)", "cmd": lambda app: f"tracert -d {app.host_entry.get()}"},
                {"name": "Pathping", "cmd": lambda app: f"pathping {app.host_entry.get()}"},
                {"name": "Telnet", "cmd": lambda app: f"telnet {app.host_entry.get()} {app.port_entry.get()}"},
                {"name": "NSLookup", "cmd": lambda app: f"nslookup {app.host_entry.get()}"},
            ],
        },
        {
            "title": "Informazioni Rete",
            "commands": [
                {"name": "Tabella ARP", "cmd": "arp -a"},
                {"name": "Routing Table", "cmd": "route print"},
                {"name": "Connessioni Attive", "cmd": "netstat -a"},
                {"name": "Connessioni + Processi", "cmd": "netstat -anob"},
            ],
        },
        {
            "title": "Group Policy",
            "commands": [
                {"name": "Aggiorna GPO", "cmd": "gpupdate"},
                {"name": "Forza Aggiornamento GPO", "cmd": "gpupdate /force"},
                {"name": "Report GPO", "cmd": "gpresult /h c:\\gpo_report.html"},
            ],
        },
    ],
}

# ==========================
# CONSOLE
# ==========================
class Console(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.output = scrolledtext.ScrolledText(
            self, bg=CONFIG["console"]["bg"], fg=CONFIG["console"]["fg"],
            insertbackground="white", state=tk.DISABLED
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        bar = ttk.Frame(self)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Pulisci", command=self.clear).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(bar, text="Salva", command=self.save).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(bar, text="Interrompi", command=self.app.stop_process).pack(side=tk.RIGHT, padx=2, pady=2)

    def append(self, text):
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    def clear(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete(1.0, tk.END)
        self.output.config(state=tk.DISABLED)

    def save(self):
        f = filedialog.asksaveasfilename(defaultextension=".txt")
        if f:
            with open(f, "w", encoding="utf-8") as file:
                file.write(self.output.get(1.0, tk.END))
            messagebox.showinfo("Salvato", f"Output salvato in {f}")

# ==========================
# MODULO DRAGGABILE
# ==========================
class Module(tk.Frame):
    def __init__(self, parent, app, title, commands, input_host=False, input_port=False):
        super().__init__(parent, bg=CONFIG["postit"]["bg"], relief=CONFIG["postit"]["relief"], bd=CONFIG["postit"]["border"])
        self.app = app
        self.canvas = parent
        self._drag_data = {"x": 0, "y": 0}

        header = tk.Label(self, text=title, bg=CONFIG["postit"]["bg"], font=("Arial", 10, "bold"))
        header.pack(fill=tk.X, pady=2)

        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)
        header.bind("<ButtonPress-1>", self.start_move)
        header.bind("<B1-Motion>", self.do_move)

        if input_host:
            hf = ttk.Frame(self); hf.pack(fill=tk.X, pady=2)
            ttk.Label(hf, text="Host/IP:").pack(side=tk.LEFT)
            self.app.host_entry = ttk.Entry(hf, width=20)
            self.app.host_entry.insert(0, "8.8.8.8")
            self.app.host_entry.pack(side=tk.LEFT, padx=5)

        if input_port:
            pf = ttk.Frame(self); pf.pack(fill=tk.X, pady=2)
            ttk.Label(pf, text="Porta:").pack(side=tk.LEFT)
            self.app.port_entry = ttk.Entry(pf, width=10)
            self.app.port_entry.insert(0, "80")
            self.app.port_entry.pack(side=tk.LEFT, padx=5)

        self.create_buttons(commands)

    def create_buttons(self, commands):
        for cmd_info in commands:
            name, cmd = cmd_info["name"], cmd_info["cmd"]
            continuous = cmd_info.get("continuous", False)

            frame = ttk.Frame(self)
            frame.pack(fill=tk.X, pady=1)

            b = ttk.Button(frame, text=name)
            b.pack(side=tk.LEFT, fill=tk.X, expand=True)

            if continuous:
                ttk.Label(frame, text="(Tieni premuto)", foreground="orange").pack(side=tk.RIGHT, padx=3)
                b.bind("<ButtonPress-1>", lambda e, c=cmd: self.app.start_continuous(c))
                b.bind("<ButtonRelease-1>", lambda e: self.app.stop_process())
            else:
                b.config(command=lambda c=cmd: self.app.run_command(c))

    def start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def do_move(self, event):
        new_x = self.winfo_x() + event.x - self._drag_data["x"]
        new_y = self.winfo_y() + event.y - self._drag_data["y"]

        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        fw, fh = self.winfo_width(), self.winfo_height()

        new_x = max(0, min(new_x, cw - fw))
        new_y = max(0, min(new_y, ch - fh))

        for widget in self.canvas.winfo_children():
            if widget is self or not isinstance(widget, Module):
                continue
            x1, y1 = widget.winfo_x(), widget.winfo_y()
            x2, y2 = x1 + widget.winfo_width(), y1 + widget.winfo_height()

            nx1, ny1 = new_x, new_y
            nx2, ny2 = new_x + fw, new_y + fh

            overlap = not (nx2 <= x1 or nx1 >= x2 or ny2 <= y1 or ny1 >= y2)
            if overlap:
                return

        self.place(x=new_x, y=new_y)

# ==========================
# APP PRINCIPALE
# ==========================
class TroubleshootingHub:
    def __init__(self, root):
        self.root, self.process = root, None
        cfg = CONFIG["window"]
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.title(cfg["title"])
        root.geometry(f"{int(sw*cfg['width_ratio'])}x{int(sh*cfg['height_ratio'])}")

        paned = ttk.Panedwindow(root, orient=tk.HORIZONTAL); paned.pack(fill=tk.BOTH, expand=True)
        self.left, right = tk.Canvas(paned, bg="#f0f0f0"), ttk.Frame(paned)
        paned.add(self.left, weight=2); paned.add(right, weight=1)

        self.console = Console(right, self)
        self.console.pack(fill=tk.BOTH, expand=True)

        self.modules = []

        self.root.after(100, self.place_modules)

    def place_modules(self):
        self.left.update_idletasks()
        canvas_width = self.left.winfo_width()

        current_x, current_y = 0, 0
        max_row_height = 0

        for m in CONFIG["modules"]:
            mod = Module(self.left, self, m["title"], m["commands"], m.get("input_host", False), m.get("input_port", False))
            mod.update_idletasks()

            fw, fh = mod.winfo_reqwidth(), mod.winfo_reqheight()

            if current_x + fw > canvas_width:
                current_x = 0
                current_y += max_row_height
                max_row_height = 0

            mod.place(x=current_x, y=current_y)
            self.modules.append(mod)

            current_x += fw
            max_row_height = max(max_row_height, fh)

        self.left.update_idletasks()

    def run_command(self, cmd):
        if self.process: return
        cmd = cmd(self) if callable(cmd) else cmd
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{ts}] Eseguendo: {cmd}\n")

        def task():
            try:
                self.process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                for line in iter(self.process.stdout.readline, ''):
                    if not line or not self.process: break
                    self.console.append(line)
                if self.process: self.process.wait()
            except Exception as e:
                self.console.append(f"ERRORE: {e}\n")
            finally:
                self.process = None

        threading.Thread(target=task, daemon=True).start()

    def start_continuous(self, cmd):
        if self.process: return
        cmd = cmd(self) if callable(cmd) else cmd
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{ts}] Avviato continuo: {cmd}\n")

        def task():
            try:
                self.process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(self.process.stdout.readline, ''):
                    if not line or not self.process: break
                    self.console.append(line)
                if self.process: self.process.wait()
            except Exception as e:
                self.console.append(f"ERRORE: {e}\n")
            finally:
                self.process = None

        threading.Thread(target=task, daemon=True).start()

    def stop_process(self):
        if self.process:
            try: self.process.terminate()
            except: pass
            self.process = None
            self.console.append("[INFO] Processo interrotto.\n")

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    root = tk.Tk()
    app = TroubleshootingHub(root)
    root.mainloop()
