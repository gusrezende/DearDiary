import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from datetime import datetime

ARQUIVO = os.path.join(os.path.expanduser("~"), "meu_diario.json")

HUMOR_OPCOES = ["😊 Feliz", "😌 Tranquilo", "😐 Neutro", "😔 Triste",
                "😤 Irritado", "😴 Cansado", "🤩 Animado"]

C = {
    "fundo":        "#f5f4f0",
    "sidebar":      "#111111",
    "sidebar2":     "#1c1c1c",   # fundo de pasta expandida
    "titulo_app":   "#ffffff",
    "texto_side":   "#cccccc",
    "texto_fraco":  "#888888",
    "pasta_fg":     "#ffffff",
    "sel":          "#ffffff",
    "sel_fg":       "#111111",
    "area":         "#ffffff",
    "borda":        "#d8d5ce",
    "texto":        "#1a1a1a",
    "cursor":       "#111111",
    "btn_pri":      "#111111",
    "btn_pri_fg":   "#ffffff",
    "sucesso":      "#2d6a4f",
}

# ── Persistência ─────────────────────────────────────────────────────────────
# Formato do JSON:
# {
#   "pastas": [{"id": "...", "nome": "..."}, ...],
#   "paginas": [{"id": "...", "pasta_id": "..." | null, "titulo": "...",
#                "texto": "...", "humor": "...", "data": "..."}, ...]
# }

def _novo_id():
    import uuid
    return str(uuid.uuid4())[:8]

def carregar_dados():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
        # Compatibilidade com formato antigo (lista simples)
        if isinstance(dados, list):
            return {"pastas": [], "paginas": dados}
        return dados
    return {"pastas": [], "paginas": []}

def salvar_dados(dados):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ── App ──────────────────────────────────────────────────────────────────────

class DiarioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diário")
        self.root.geometry("980x700")
        self.root.configure(bg=C["fundo"])
        self.root.resizable(True, True)

        dados = carregar_dados()
        self.pastas  = dados.get("pastas", [])
        self.paginas = dados.get("paginas", [])

        # Migra páginas antigas sem id
        for p in self.paginas:
            if "id" not in p:
                p["id"] = _novo_id()
            if "pasta_id" not in p:
                p["pasta_id"] = None

        # pastas expandidas
        self.expandidas = set()
        self.pagina_atual_id = None   # id da página aberta

        self._estilos()
        self._ui()
        self._redesenhar_arvore()

    # ── Estilos ──────────────────────────────────────────────────────────────

    def _estilos(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Humor.TCombobox",
                    fieldbackground=C["area"], background=C["area"],
                    foreground=C["texto"], selectbackground=C["borda"],
                    selectforeground=C["texto"], relief="flat",
                    bordercolor=C["borda"])
        s.map("Humor.TCombobox",
              fieldbackground=[("readonly", C["area"])],
              foreground=[("readonly", C["texto"])],
              bordercolor=[("focus", C["texto"])])

    # ── UI ───────────────────────────────────────────────────────────────────

    def _ui(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sb = tk.Frame(self.root, bg=C["sidebar"], width=250)
        self.sb.grid(row=0, column=0, sticky="nsew")
        self.sb.grid_propagate(False)
        self.sb.grid_rowconfigure(2, weight=1)
        self.sb.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        cab = tk.Frame(self.sb, bg=C["sidebar"])
        cab.grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 0))
        tk.Label(cab, text="✦", font=("Georgia", 20),
                 bg=C["sidebar"], fg=C["titulo_app"]).pack(side="left", padx=(0, 8))
        tk.Label(cab, text="Diário", font=("Georgia", 17, "bold"),
                 bg=C["sidebar"], fg=C["titulo_app"]).pack(side="left")

        tk.Frame(self.sb, height=1, bg="#2a2a2a").grid(
            row=1, column=0, sticky="ew", padx=20, pady=14)

        # Área de árvore com scroll
        tree_outer = tk.Frame(self.sb, bg=C["sidebar"])
        tree_outer.grid(row=2, column=0, sticky="nsew")
        tree_outer.grid_rowconfigure(0, weight=1)
        tree_outer.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(tree_outer, bg=C["sidebar"],
                                highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        sb_scroll = tk.Scrollbar(tree_outer, orient="vertical",
                                 bg=C["sidebar"], troughcolor=C["sidebar"],
                                 activebackground="#444444", relief="flat", bd=0,
                                 command=self.canvas.yview)
        sb_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=sb_scroll.set)

        self.tree_frame = tk.Frame(self.canvas, bg=C["sidebar"])
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.tree_frame, anchor="nw")

        self.tree_frame.bind("<Configure>", self._on_tree_resize)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Botões inferiores
        bf = tk.Frame(self.sb, bg=C["sidebar"])
        bf.grid(row=3, column=0, sticky="ew", padx=14, pady=12)
        bf.grid_columnconfigure(0, weight=1)
        bf.grid_columnconfigure(1, weight=1)

        self._btn(bf, "＋ Pasta", self._nova_pasta,
                  C["btn_pri_fg"], "#2a2a2a").grid(
            row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 6))

        self._btn(bf, "＋ Página", self._nova_pagina,
                  C["btn_pri_fg"], C["btn_pri"]).grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 6))

        self._btn(bf, "🗑  Excluir selecionado", self._excluir_selecionado,
                  "#bb3333", "#2a1a1a").grid(
            row=1, column=0, columnspan=2, sticky="ew")

    def _on_tree_resize(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Árvore de pastas/páginas ─────────────────────────────────────────────

    def _redesenhar_arvore(self):
        for w in self.tree_frame.winfo_children():
            w.destroy()

        row = 0

        # Páginas sem pasta ("Sem pasta")
        soltas = [p for p in self.paginas if not p.get("pasta_id")]
        if soltas:
            row = self._render_pasta_virtual(row, soltas)

        # Pastas
        for pasta in self.pastas:
            row = self._render_pasta(row, pasta)

        self.tree_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_pasta_virtual(self, row, paginas):
        """Renderiza o grupo 'Sem pasta' para páginas sem pasta_id."""
        pid = "__sem_pasta__"
        expandida = pid in self.expandidas

        linha = tk.Frame(self.tree_frame, bg=C["sidebar"], cursor="hand2")
        linha.grid(row=row, column=0, sticky="ew", padx=0)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        seta = "▾" if expandida else "▸"
        tk.Label(linha, text=f"  {seta}  📂  Sem pasta",
                 font=("Segoe UI", 10), bg=C["sidebar"],
                 fg=C["texto_fraco"], anchor="w", padx=4, pady=5
                 ).pack(fill="x")

        linha.bind("<Button-1>", lambda e, i=pid: self._toggle_pasta(i))
        for w in linha.winfo_children():
            w.bind("<Button-1>", lambda e, i=pid: self._toggle_pasta(i))

        row += 1
        if expandida:
            for p in paginas:
                row = self._render_pagina_item(row, p, indent=24)
        return row

    def _render_pasta(self, row, pasta):
        pid = pasta["id"]
        expandida = pid in self.expandidas
        paginas_pasta = [p for p in self.paginas if p.get("pasta_id") == pid]
        selecionada = (self.sel_tipo == "pasta" and self.sel_id == pid
                       ) if hasattr(self, "sel_tipo") else False

        bg = "#2a2a2a" if selecionada else C["sidebar"]
        seta = "▾" if expandida else "▸"
        n = len(paginas_pasta)
        label_txt = f"  {seta}  🗂  {pasta['nome']}  ({n})"

        linha = tk.Frame(self.tree_frame, bg=bg, cursor="hand2")
        linha.grid(row=row, column=0, sticky="ew")

        lbl = tk.Label(linha, text=label_txt,
                       font=("Segoe UI", 10, "bold"),
                       bg=bg, fg=C["pasta_fg"],
                       anchor="w", padx=4, pady=6)
        lbl.pack(fill="x")

        def on_click_pasta(e, i=pid):
            self.sel_tipo = "pasta"
            self.sel_id = i
            self._toggle_pasta(i)

        linha.bind("<Button-1>", on_click_pasta)
        lbl.bind("<Button-1>", on_click_pasta)

        # Botão renomear (hover-like)
        btn_ren = tk.Label(linha, text="✎", font=("Segoe UI", 10),
                           bg=bg, fg=C["texto_fraco"], cursor="hand2", padx=6)
        btn_ren.place(relx=1.0, rely=0.5, anchor="e", x=-8)
        btn_ren.bind("<Button-1>", lambda e, i=pid: self._renomear_pasta(i))

        row += 1
        if expandida:
            for p in paginas_pasta:
                row = self._render_pagina_item(row, p, indent=28)
        return row

    def _render_pagina_item(self, row, pagina, indent=16):
        pid = pagina["id"]
        selecionada = self.pagina_atual_id == pid
        bg = "#333333" if selecionada else C["sidebar"]

        titulo = pagina.get("titulo") or datetime.fromisoformat(
            pagina["data"]).strftime("%d/%m/%Y")
        humor = pagina.get("humor", "")
        emoji = humor.split()[0] if humor else "·"
        txt = f"{emoji}  {titulo[:26]}"

        linha = tk.Frame(self.tree_frame, bg=bg, cursor="hand2")
        linha.grid(row=row, column=0, sticky="ew")

        lbl = tk.Label(linha, text=txt, font=("Segoe UI", 10),
                       bg=bg, fg=C["sel"] if selecionada else C["texto_side"],
                       anchor="w", padx=indent, pady=5)
        lbl.pack(fill="x")

        for w in (linha, lbl):
            w.bind("<Button-1>", lambda e, i=pid: self._abrir_pagina(i))
            w.bind("<Button-3>", lambda e, i=pid: self._menu_pagina(e, i))

        return row + 1

    # ── Área principal ───────────────────────────────────────────────────────

    def _build_main(self):
        self.main = tk.Frame(self.root, bg=C["fundo"])
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(4, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self.label_data = tk.Label(
            self.main, text="", font=("Georgia", 11, "italic"),
            bg=C["fundo"], fg=C["texto_fraco"], anchor="w")
        self.label_data.grid(row=0, column=0, padx=36, pady=(30, 2), sticky="ew")

        tf = tk.Frame(self.main, bg=C["fundo"])
        tf.grid(row=1, column=0, padx=32, sticky="ew")
        tf.grid_columnconfigure(0, weight=1)

        self.titulo_var = tk.StringVar(value="Selecione ou crie uma página")
        self.entry_titulo = tk.Entry(
            tf, textvariable=self.titulo_var,
            font=("Georgia", 22, "bold"),
            bg=C["fundo"], fg=C["texto_fraco"],
            insertbackground=C["cursor"],
            relief="flat", bd=0, highlightthickness=0,
            state="disabled")
        self.entry_titulo.grid(row=0, column=0, sticky="ew")
        self.entry_titulo.bind("<FocusIn>",  lambda e: self.sep.config(bg=C["texto"]))
        self.entry_titulo.bind("<FocusOut>", lambda e: self.sep.config(bg=C["borda"]))

        self.sep = tk.Frame(self.main, height=1, bg=C["borda"])
        self.sep.grid(row=2, column=0, sticky="ew", padx=36, pady=(8, 0))

        hr = tk.Frame(self.main, bg=C["fundo"])
        hr.grid(row=3, column=0, padx=36, pady=(10, 6), sticky="ew")

        tk.Label(hr, text="Humor:", font=("Segoe UI", 9),
                 bg=C["fundo"], fg=C["texto_fraco"]).pack(side="left")

        self.humor_var = tk.StringVar(value=HUMOR_OPCOES[0])
        self.humor_cb = ttk.Combobox(
            hr, textvariable=self.humor_var, values=HUMOR_OPCOES,
            state="disabled", style="Humor.TCombobox",
            width=13, font=("Segoe UI", 9))
        self.humor_cb.pack(side="left", padx=(6, 0))

        # Pasta da página
        tk.Label(hr, text="Pasta:", font=("Segoe UI", 9),
                 bg=C["fundo"], fg=C["texto_fraco"]).pack(side="left", padx=(18, 0))
        self.pasta_var = tk.StringVar(value="Sem pasta")
        self.pasta_cb = ttk.Combobox(
            hr, textvariable=self.pasta_var,
            state="disabled", style="Humor.TCombobox",
            width=14, font=("Segoe UI", 9))
        self.pasta_cb.pack(side="left", padx=(6, 0))

        self.label_palavras = tk.Label(
            hr, text="", font=("Segoe UI", 9),
            bg=C["fundo"], fg=C["texto_fraco"])
        self.label_palavras.pack(side="right")

        txtf = tk.Frame(self.main, bg=C["fundo"])
        txtf.grid(row=4, column=0, padx=36, sticky="nsew")
        txtf.grid_rowconfigure(0, weight=1)
        txtf.grid_columnconfigure(0, weight=1)

        sc = tk.Scrollbar(txtf, bg=C["borda"], troughcolor=C["fundo"],
                          activebackground="#aaaaaa", relief="flat", bd=0)
        sc.grid(row=0, column=1, sticky="ns")

        self.texto = tk.Text(
            txtf, font=("Georgia", 12),
            bg=C["area"], fg=C["texto"],
            insertbackground=C["cursor"],
            relief="flat", bd=0, padx=20, pady=16,
            wrap="word", yscrollcommand=sc.set,
            highlightthickness=1,
            highlightbackground=C["borda"],
            highlightcolor=C["texto"],
            state="disabled",
            spacing1=3, spacing3=3)
        self.texto.grid(row=0, column=0, sticky="nsew")
        sc.config(command=self.texto.yview)
        self.texto.bind("<KeyRelease>", self._atualizar_contador)

        rodape = tk.Frame(self.main, bg=C["fundo"])
        rodape.grid(row=5, column=0, padx=36, pady=14, sticky="ew")

        self.btn_salvar = self._btn(
            rodape, "Salvar página", self._salvar_pagina,
            C["btn_pri_fg"], C["btn_pri"])
        self.btn_salvar.pack(side="right")
        self.btn_salvar.config(state="disabled")

        self.label_status = tk.Label(
            rodape, text="", font=("Segoe UI", 9, "italic"),
            bg=C["fundo"], fg=C["sucesso"])
        self.label_status.pack(side="right", padx=14)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _btn(self, parent, texto, cmd, fg, bg):
        return tk.Button(
            parent, text=texto, command=cmd,
            bg=bg, fg=fg, font=("Segoe UI", 10),
            relief="flat", bd=0, padx=14, pady=8,
            cursor="hand2",
            activebackground="#333333",
            activeforeground=fg)

    def _habilitar(self, on=True):
        st = "normal" if on else "disabled"
        self.texto.config(state=st)
        self.humor_cb.config(state="readonly" if on else "disabled")
        self.pasta_cb.config(state="readonly" if on else "disabled")
        self.btn_salvar.config(state=st)
        self.entry_titulo.config(
            state=st, fg=C["texto"] if on else C["texto_fraco"])

    def _atualizar_contador(self, _=None):
        txt = self.texto.get("1.0", "end-1c")
        n = len(txt.split()) if txt.strip() else 0
        self.label_palavras.config(text=f"{n} palavras")

    def _atualizar_pasta_cb(self):
        nomes = ["Sem pasta"] + [p["nome"] for p in self.pastas]
        self.pasta_cb.config(values=nomes)

    def _flash(self, msg, cor=None):
        self.label_status.config(text=msg, fg=cor or C["sucesso"])
        self.root.after(2400, lambda: self.label_status.config(text=""))

    def _salvar_todos(self):
        salvar_dados({"pastas": self.pastas, "paginas": self.paginas})

    def _toggle_pasta(self, pid):
        if pid in self.expandidas:
            self.expandidas.discard(pid)
        else:
            self.expandidas.add(pid)
        self._redesenhar_arvore()

    # ── Ações — pastas ───────────────────────────────────────────────────────

    def _nova_pasta(self):
        nome = simpledialog.askstring(
            "Nova Pasta", "Nome da pasta:", parent=self.root)
        if not nome or not nome.strip():
            return
        nova = {"id": _novo_id(), "nome": nome.strip()}
        self.pastas.append(nova)
        self.expandidas.add(nova["id"])
        self._salvar_todos()
        self._atualizar_pasta_cb()
        self._redesenhar_arvore()

    def _renomear_pasta(self, pid):
        pasta = next((p for p in self.pastas if p["id"] == pid), None)
        if not pasta:
            return
        novo = simpledialog.askstring(
            "Renomear Pasta", "Novo nome:", initialvalue=pasta["nome"],
            parent=self.root)
        if not novo or not novo.strip():
            return
        pasta["nome"] = novo.strip()
        self._salvar_todos()
        self._atualizar_pasta_cb()
        self._redesenhar_arvore()

    def _excluir_pasta(self, pid):
        pasta = next((p for p in self.pastas if p["id"] == pid), None)
        if not pasta:
            return
        n = sum(1 for p in self.paginas if p.get("pasta_id") == pid)
        msg = f"Excluir a pasta \"{pasta['nome']}\"?"
        if n:
            msg += f"\n\nAs {n} página(s) dentro dela ficarão sem pasta."
        if not messagebox.askyesno("Confirmar", msg):
            return
        for p in self.paginas:
            if p.get("pasta_id") == pid:
                p["pasta_id"] = None
        self.pastas = [p for p in self.pastas if p["id"] != pid]
        self.expandidas.discard(pid)
        self._salvar_todos()
        self._atualizar_pasta_cb()
        self._redesenhar_arvore()

    # ── Ações — páginas ──────────────────────────────────────────────────────

    def _nova_pagina(self):
        self.pagina_atual_id = None
        agora = datetime.now()
        self.label_data.config(
            text=agora.strftime("%A, %d de %B de %Y — %H:%M").capitalize())
        self._habilitar(True)
        self._atualizar_pasta_cb()
        self.titulo_var.set("")
        self.texto.delete("1.0", "end")
        self.humor_var.set(HUMOR_OPCOES[0])
        self.pasta_var.set("Sem pasta")
        self._atualizar_contador()
        self._redesenhar_arvore()
        self.entry_titulo.focus()

    def _abrir_pagina(self, pid):
        p = next((x for x in self.paginas if x["id"] == pid), None)
        if not p:
            return
        self.pagina_atual_id = pid
        dt = datetime.fromisoformat(p["data"])
        self.label_data.config(
            text=dt.strftime("%A, %d de %B de %Y — %H:%M").capitalize())
        self._habilitar(True)
        self._atualizar_pasta_cb()
        self.titulo_var.set(p.get("titulo", ""))
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", p.get("texto", ""))
        self.humor_var.set(p.get("humor", HUMOR_OPCOES[0]))
        # Pasta atual
        pasta_id = p.get("pasta_id")
        if pasta_id:
            pasta = next((x for x in self.pastas if x["id"] == pasta_id), None)
            self.pasta_var.set(pasta["nome"] if pasta else "Sem pasta")
        else:
            self.pasta_var.set("Sem pasta")
        self._atualizar_contador()
        self._redesenhar_arvore()

    def _salvar_pagina(self):
        conteudo = self.texto.get("1.0", "end-1c").strip()
        if not conteudo:
            messagebox.showwarning("Atenção", "Escreva algo antes de salvar!")
            return

        titulo   = self.titulo_var.get().strip()
        humor    = self.humor_var.get()
        pasta_nome = self.pasta_var.get()
        pasta_id = None
        if pasta_nome != "Sem pasta":
            pasta = next((x for x in self.pastas if x["nome"] == pasta_nome), None)
            if pasta:
                pasta_id = pasta["id"]

        if self.pagina_atual_id:
            p = next((x for x in self.paginas if x["id"] == self.pagina_atual_id), None)
            if p:
                p.update({"titulo": titulo, "texto": conteudo,
                          "humor": humor, "pasta_id": pasta_id})
        else:
            nova = {
                "id":       _novo_id(),
                "data":     datetime.now().isoformat(),
                "titulo":   titulo,
                "texto":    conteudo,
                "humor":    humor,
                "pasta_id": pasta_id,
            }
            self.paginas.append(nova)
            self.pagina_atual_id = nova["id"]
            if pasta_id:
                self.expandidas.add(pasta_id)

        self._salvar_todos()
        self._redesenhar_arvore()
        self._flash("✓ Página salva")

    def _menu_pagina(self, event, pid):
        """Menu de contexto ao clicar com botão direito numa página."""
        menu = tk.Menu(self.root, tearoff=0, bg=C["sidebar2"],
                       fg=C["texto_side"], activebackground="#333333",
                       activeforeground="white", relief="flat", bd=0)
        menu.add_command(label="✏️  Abrir",
                         command=lambda: self._abrir_pagina(pid))
        menu.add_separator()
        menu.add_command(label="📁  Mover para pasta...",
                         command=lambda: self._mover_pagina(pid))
        menu.add_separator()
        menu.add_command(label="🗑  Excluir",
                         command=lambda: self._excluir_pagina(pid))
        menu.tk_popup(event.x_root, event.y_root)

    def _mover_pagina(self, pid):
        p = next((x for x in self.paginas if x["id"] == pid), None)
        if not p:
            return
        opcoes = ["Sem pasta"] + [x["nome"] for x in self.pastas]
        win = tk.Toplevel(self.root)
        win.title("Mover para pasta")
        win.geometry("300x160")
        win.configure(bg=C["fundo"])
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Escolha a pasta de destino:",
                 font=("Segoe UI", 11), bg=C["fundo"], fg=C["texto"]).pack(pady=(20, 8))

        var = tk.StringVar(value="Sem pasta")
        cb = ttk.Combobox(win, textvariable=var, values=opcoes,
                          state="readonly", style="Humor.TCombobox",
                          width=20, font=("Segoe UI", 10))
        cb.pack(pady=4)

        def confirmar():
            nome = var.get()
            if nome == "Sem pasta":
                p["pasta_id"] = None
            else:
                pasta = next((x for x in self.pastas if x["nome"] == nome), None)
                p["pasta_id"] = pasta["id"] if pasta else None
                if pasta:
                    self.expandidas.add(pasta["id"])
            self._salvar_todos()
            self._redesenhar_arvore()
            win.destroy()

        self._btn(win, "Mover", confirmar,
                  C["btn_pri_fg"], C["btn_pri"]).pack(pady=12)

    def _excluir_pagina(self, pid=None):
        if pid is None:
            pid = self.pagina_atual_id
        if not pid:
            messagebox.showinfo("Atenção", "Nenhuma página selecionada.")
            return
        p = next((x for x in self.paginas if x["id"] == pid), None)
        nome = p.get("titulo") or "esta página" if p else "esta página"
        if not messagebox.askyesno("Confirmar", f"Excluir \"{nome}\" permanentemente?"):
            return
        self.paginas = [x for x in self.paginas if x["id"] != pid]
        if self.pagina_atual_id == pid:
            self.pagina_atual_id = None
            self._habilitar(False)
            self.titulo_var.set("Selecione ou crie uma página")
            self.texto.delete("1.0", "end")
            self.label_data.config(text="")
            self._atualizar_contador()
        self._salvar_todos()
        self._redesenhar_arvore()

    def _excluir_selecionado(self):
        """Botão excluir genérico da sidebar — decide o que excluir."""
        if hasattr(self, "sel_tipo") and self.sel_tipo == "pasta":
            self._excluir_pasta(self.sel_id)
            self.sel_tipo = None
        elif self.pagina_atual_id:
            self._excluir_pagina(self.pagina_atual_id)
        else:
            messagebox.showinfo("Atenção",
                                "Selecione uma página ou pasta para excluir.\n"
                                "Clique numa pasta para selecioná-la.")


if __name__ == "__main__":
    root = tk.Tk()
    app = DiarioApp(root)
    root.mainloop()