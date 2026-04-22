import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json, os, uuid, calendar
from datetime import datetime
from collections import defaultdict

ARQUIVO = os.path.join(os.path.expanduser("~"), "meu_diario.json")

HUMOR_OPCOES = ["😊 Feliz", "😌 Tranquilo", "😐 Neutro", "😔 Triste",
                "😤 Irritado", "😴 Cansado", "🤩 Animado"]

# Valor numérico de cada humor (para o gráfico de linha)
HUMOR_VALOR = {
    "😊 Feliz":     5,
    "🤩 Animado":   6,
    "😌 Tranquilo": 4,
    "😐 Neutro":    3,
    "😴 Cansado":   2,
    "😔 Triste":    1,
    "😤 Irritado":  1,
}

MESES_PT = ["Jan","Fev","Mar","Abr","Mai","Jun",
            "Jul","Ago","Set","Out","Nov","Dez"]

C = {
    "fundo":       "#f5f4f0",
    "sidebar":     "#111111",
    "sidebar2":    "#1c1c1c",
    "titulo_app":  "#ffffff",
    "texto_side":  "#cccccc",
    "texto_fraco": "#888888",
    "pasta_fg":    "#ffffff",
    "sel":         "#ffffff",
    "area":        "#ffffff",
    "borda":       "#d8d5ce",
    "texto":       "#1a1a1a",
    "cursor":      "#111111",
    "btn_pri":     "#111111",
    "btn_pri_fg":  "#ffffff",
    "sucesso":     "#2d6a4f",
    "aba_ativa":   "#1a1a1a",
    "aba_inativa": "#888888",
}

def _novo_id():
    return str(uuid.uuid4())[:8]

def carregar_dados():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list):
            return {"pastas": [], "paginas": dados}
        return dados
    return {"pastas": [], "paginas": []}

def salvar_dados(dados):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────

class DiarioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diário")
        self.root.geometry("1020x720")
        self.root.configure(bg=C["fundo"])
        self.root.resizable(True, True)

        dados = carregar_dados()
        self.pastas  = dados.get("pastas", [])
        self.paginas = dados.get("paginas", [])
        for p in self.paginas:
            if "id"       not in p: p["id"]       = _novo_id()
            if "pasta_id" not in p: p["pasta_id"] = None

        self.expandidas      = set()
        self.pagina_atual_id = None
        self.sel_tipo        = None
        self.sel_id          = None

        self._estilos()
        self._build_layout()
        self._redesenhar_arvore()

    # ── Estilos ──────────────────────────────────────────────────────────────

    def _estilos(self):
        s = ttk.Style()
        s.theme_use("clam")
        for nome in ("Humor.TCombobox", "Pasta.TCombobox"):
            s.configure(nome,
                fieldbackground=C["area"], background=C["area"],
                foreground=C["texto"], selectbackground=C["borda"],
                selectforeground=C["texto"], relief="flat", bordercolor=C["borda"])
            s.map(nome,
                fieldbackground=[("readonly", C["area"])],
                foreground=[("readonly", C["texto"])],
                bordercolor=[("focus", C["texto"])])

    # ── Layout raiz ──────────────────────────────────────────────────────────

    def _build_layout(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ═════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═════════════════════════════════════════════════════════════════════════

    def _build_sidebar(self):
        self.sb = tk.Frame(self.root, bg=C["sidebar"], width=250)
        self.sb.grid(row=0, column=0, sticky="nsew")
        self.sb.grid_propagate(False)
        self.sb.grid_rowconfigure(2, weight=1)
        self.sb.grid_columnconfigure(0, weight=1)

        cab = tk.Frame(self.sb, bg=C["sidebar"])
        cab.grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 0))
        tk.Label(cab, text="✦", font=("Georgia", 20),
                 bg=C["sidebar"], fg=C["titulo_app"]).pack(side="left", padx=(0, 8))
        tk.Label(cab, text="Diário", font=("Georgia", 17, "bold"),
                 bg=C["sidebar"], fg=C["titulo_app"]).pack(side="left")

        tk.Frame(self.sb, height=1, bg="#2a2a2a").grid(
            row=1, column=0, sticky="ew", padx=20, pady=14)

        # Área de árvore
        outer = tk.Frame(self.sb, bg=C["sidebar"])
        outer.grid(row=2, column=0, sticky="nsew")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(outer, bg=C["sidebar"], highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        sc = tk.Scrollbar(outer, orient="vertical", bg=C["sidebar"],
                          troughcolor=C["sidebar"], activebackground="#444",
                          relief="flat", bd=0, command=self.canvas.yview)
        sc.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=sc.set)

        self.tree_frame = tk.Frame(self.canvas, bg=C["sidebar"])
        self._cw = self.canvas.create_window((0, 0), window=self.tree_frame, anchor="nw")
        self.tree_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self._cw, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Botões
        bf = tk.Frame(self.sb, bg=C["sidebar"])
        bf.grid(row=3, column=0, sticky="ew", padx=14, pady=12)
        bf.grid_columnconfigure(0, weight=1)
        bf.grid_columnconfigure(1, weight=1)

        self._btn(bf, "＋ Pasta",  self._nova_pasta,
                  C["btn_pri_fg"], "#2a2a2a").grid(
            row=0, column=0, sticky="ew", padx=(0,4), pady=(0,6))
        self._btn(bf, "＋ Página", self._nova_pagina,
                  C["btn_pri_fg"], C["btn_pri"]).grid(
            row=0, column=1, sticky="ew", padx=(4,0), pady=(0,6))
        self._btn(bf, "🗑  Excluir selecionado", self._excluir_selecionado,
                  "#bb3333", "#2a1a1a").grid(
            row=1, column=0, columnspan=2, sticky="ew")

    # ── Árvore ───────────────────────────────────────────────────────────────

    def _redesenhar_arvore(self):
        for w in self.tree_frame.winfo_children():
            w.destroy()
        row = 0
        soltas = [p for p in self.paginas if not p.get("pasta_id")]
        if soltas:
            row = self._render_grupo_sem_pasta(row, soltas)
        for pasta in self.pastas:
            row = self._render_pasta(row, pasta)
        self.tree_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_grupo_sem_pasta(self, row, paginas):
        pid = "__sem_pasta__"
        exp = pid in self.expandidas
        seta = "▾" if exp else "▸"
        linha = tk.Frame(self.tree_frame, bg=C["sidebar"], cursor="hand2")
        linha.grid(row=row, column=0, sticky="ew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        lbl = tk.Label(linha, text=f"  {seta}  📂  Sem pasta",
                       font=("Segoe UI", 10), bg=C["sidebar"],
                       fg=C["texto_fraco"], anchor="w", padx=4, pady=5)
        lbl.pack(fill="x")
        for w in (linha, lbl):
            w.bind("<Button-1>", lambda e, i=pid: self._toggle_pasta(i))
        row += 1
        if exp:
            for p in paginas:
                row = self._render_pagina_item(row, p, indent=24)
        return row

    def _render_pasta(self, row, pasta):
        pid = pasta["id"]
        exp = pid in self.expandidas
        pgs = [p for p in self.paginas if p.get("pasta_id") == pid]
        sel = self.sel_tipo == "pasta" and self.sel_id == pid
        bg  = "#2a2a2a" if sel else C["sidebar"]
        seta = "▾" if exp else "▸"

        linha = tk.Frame(self.tree_frame, bg=bg, cursor="hand2")
        linha.grid(row=row, column=0, sticky="ew")
        lbl = tk.Label(linha, text=f"  {seta}  🗂  {pasta['nome']}  ({len(pgs)})",
                       font=("Segoe UI", 10, "bold"), bg=bg,
                       fg=C["pasta_fg"], anchor="w", padx=4, pady=6)
        lbl.pack(fill="x")

        def click_pasta(e, i=pid):
            self.sel_tipo, self.sel_id = "pasta", i
            self._toggle_pasta(i)
        linha.bind("<Button-1>", click_pasta)
        lbl.bind("<Button-1>", click_pasta)

        ren = tk.Label(linha, text="✎", font=("Segoe UI", 10),
                       bg=bg, fg=C["texto_fraco"], cursor="hand2", padx=6)
        ren.place(relx=1.0, rely=0.5, anchor="e", x=-8)
        ren.bind("<Button-1>", lambda e, i=pid: self._renomear_pasta(i))

        row += 1
        if exp:
            for p in pgs:
                row = self._render_pagina_item(row, p, indent=28)
        return row

    def _render_pagina_item(self, row, pagina, indent=16):
        pid = pagina["id"]
        sel = self.pagina_atual_id == pid
        bg  = "#333333" if sel else C["sidebar"]
        titulo = pagina.get("titulo") or datetime.fromisoformat(
            pagina["data"]).strftime("%d/%m/%Y")
        humor = pagina.get("humor", "")
        emoji = humor.split()[0] if humor else "·"

        linha = tk.Frame(self.tree_frame, bg=bg, cursor="hand2")
        linha.grid(row=row, column=0, sticky="ew")
        lbl = tk.Label(linha, text=f"{emoji}  {titulo[:26]}",
                       font=("Segoe UI", 10), bg=bg,
                       fg=C["sel"] if sel else C["texto_side"],
                       anchor="w", padx=indent, pady=5)
        lbl.pack(fill="x")
        for w in (linha, lbl):
            w.bind("<Button-1>", lambda e, i=pid: self._abrir_pagina(i))
            w.bind("<Button-3>", lambda e, i=pid: self._menu_pagina(e, i))
        return row + 1

    # ═════════════════════════════════════════════════════════════════════════
    # ÁREA PRINCIPAL
    # ═════════════════════════════════════════════════════════════════════════

    def _build_main(self):
        self.main = tk.Frame(self.root, bg=C["fundo"])
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        # ── Tab bar ──────────────────────────────────────────────
        tabbar = tk.Frame(self.main, bg=C["fundo"])
        tabbar.grid(row=0, column=0, sticky="ew", padx=36, pady=(18, 0))

        self._aba = tk.StringVar(value="diario")

        self._tab_btns = {}
        for txt, val in [("✦  Diário", "diario"), ("◉  Histórico de Humor", "humor")]:
            b = tk.Button(tabbar, text=txt,
                          command=lambda v=val: self._trocar_aba(v),
                          font=("Segoe UI", 10), relief="flat", bd=0,
                          padx=18, pady=6, cursor="hand2",
                          bg=C["fundo"], activebackground=C["fundo"])
            b.pack(side="left")
            self._tab_btns[val] = b

        tk.Frame(self.main, height=1, bg=C["borda"]).grid(
            row=0, column=0, sticky="sew", padx=36)

        # ── Painel diário ─────────────────────────────────────────
        self.painel_diario = tk.Frame(self.main, bg=C["fundo"])
        self.painel_diario.grid(row=1, column=0, sticky="nsew")
        self.painel_diario.grid_rowconfigure(3, weight=1)
        self.painel_diario.grid_columnconfigure(0, weight=1)
        self._build_painel_diario()

        # ── Painel humor ──────────────────────────────────────────
        self.painel_humor = tk.Frame(self.main, bg=C["fundo"])
        self.painel_humor.grid(row=1, column=0, sticky="nsew")
        self.painel_humor.grid_rowconfigure(1, weight=1)
        self.painel_humor.grid_columnconfigure(0, weight=1)
        self._build_painel_humor()

        self._trocar_aba("diario")

    def _trocar_aba(self, aba):
        self._aba.set(aba)
        if aba == "diario":
            self.painel_humor.grid_remove()
            self.painel_diario.grid()
        else:
            self.painel_diario.grid_remove()
            self.painel_humor.grid()
            self._atualizar_humor()
        for val, btn in self._tab_btns.items():
            ativo = val == aba
            btn.config(fg=C["aba_ativa"] if ativo else C["aba_inativa"],
                       font=("Segoe UI", 10, "bold" if ativo else "normal"))

    # ── Painel Diário ─────────────────────────────────────────────────────────

    def _build_painel_diario(self):
        p = self.painel_diario

        self.label_data = tk.Label(p, text="", font=("Georgia", 11, "italic"),
                                   bg=C["fundo"], fg=C["texto_fraco"], anchor="w")
        self.label_data.grid(row=0, column=0, padx=36, pady=(28, 2), sticky="ew")

        tf = tk.Frame(p, bg=C["fundo"])
        tf.grid(row=1, column=0, padx=32, sticky="ew")
        tf.grid_columnconfigure(0, weight=1)

        self.titulo_var = tk.StringVar(value="Selecione ou crie uma página")
        self.entry_titulo = tk.Entry(tf, textvariable=self.titulo_var,
                                     font=("Georgia", 22, "bold"),
                                     bg=C["fundo"], fg=C["texto_fraco"],
                                     insertbackground=C["cursor"],
                                     relief="flat", bd=0, highlightthickness=0,
                                     state="disabled")
        self.entry_titulo.grid(row=0, column=0, sticky="ew")
        self.entry_titulo.bind("<FocusIn>",  lambda e: self.sep.config(bg=C["texto"]))
        self.entry_titulo.bind("<FocusOut>", lambda e: self.sep.config(bg=C["borda"]))

        self.sep = tk.Frame(p, height=1, bg=C["borda"])
        self.sep.grid(row=2, column=0, sticky="ew", padx=36, pady=(8, 0))

        # Barra de metadados
        hr = tk.Frame(p, bg=C["fundo"])
        hr.grid(row=2, column=0, padx=36, pady=(14, 6), sticky="ew")

        tk.Label(hr, text="Humor:", font=("Segoe UI", 9),
                 bg=C["fundo"], fg=C["texto_fraco"]).pack(side="left")
        self.humor_var = tk.StringVar(value=HUMOR_OPCOES[0])
        self.humor_cb = ttk.Combobox(hr, textvariable=self.humor_var,
                                     values=HUMOR_OPCOES, state="disabled",
                                     style="Humor.TCombobox", width=13,
                                     font=("Segoe UI", 9))
        self.humor_cb.pack(side="left", padx=(6, 0))

        tk.Label(hr, text="Pasta:", font=("Segoe UI", 9),
                 bg=C["fundo"], fg=C["texto_fraco"]).pack(side="left", padx=(18, 0))
        self.pasta_var = tk.StringVar(value="Sem pasta")
        self.pasta_cb = ttk.Combobox(hr, textvariable=self.pasta_var,
                                     state="disabled", style="Pasta.TCombobox",
                                     width=14, font=("Segoe UI", 9))
        self.pasta_cb.pack(side="left", padx=(6, 0))

        self.label_palavras = tk.Label(hr, text="", font=("Segoe UI", 9),
                                       bg=C["fundo"], fg=C["texto_fraco"])
        self.label_palavras.pack(side="right")

        # Área de texto
        txtf = tk.Frame(p, bg=C["fundo"])
        txtf.grid(row=3, column=0, padx=36, sticky="nsew")
        txtf.grid_rowconfigure(0, weight=1)
        txtf.grid_columnconfigure(0, weight=1)

        sc = tk.Scrollbar(txtf, bg=C["borda"], troughcolor=C["fundo"],
                          activebackground="#aaa", relief="flat", bd=0)
        sc.grid(row=0, column=1, sticky="ns")
        self.texto = tk.Text(txtf, font=("Georgia", 12),
                             bg=C["area"], fg=C["texto"],
                             insertbackground=C["cursor"],
                             relief="flat", bd=0, padx=20, pady=16,
                             wrap="word", yscrollcommand=sc.set,
                             highlightthickness=1,
                             highlightbackground=C["borda"],
                             highlightcolor=C["texto"],
                             state="disabled", spacing1=3, spacing3=3)
        self.texto.grid(row=0, column=0, sticky="nsew")
        sc.config(command=self.texto.yview)
        self.texto.bind("<KeyRelease>", self._atualizar_contador)

        # Rodapé
        rodape = tk.Frame(p, bg=C["fundo"])
        rodape.grid(row=4, column=0, padx=36, pady=14, sticky="ew")
        self.btn_salvar = self._btn(rodape, "Salvar página", self._salvar_pagina,
                                    C["btn_pri_fg"], C["btn_pri"])
        self.btn_salvar.pack(side="right")
        self.btn_salvar.config(state="disabled")
        self.label_status = tk.Label(rodape, text="", font=("Segoe UI", 9, "italic"),
                                     bg=C["fundo"], fg=C["sucesso"])
        self.label_status.pack(side="right", padx=14)

    # ── Painel Histórico de Humor ─────────────────────────────────────────────

    def _build_painel_humor(self):
        p = self.painel_humor

        # Cabeçalho + filtro de ano
        cab = tk.Frame(p, bg=C["fundo"])
        cab.grid(row=0, column=0, sticky="ew", padx=36, pady=(28, 0))

        tk.Label(cab, text="Histórico de Humor", font=("Georgia", 20, "bold"),
                 bg=C["fundo"], fg=C["texto"]).pack(side="left")

        self.ano_var = tk.StringVar()
        self.ano_cb  = ttk.Combobox(cab, textvariable=self.ano_var,
                                    state="readonly", style="Humor.TCombobox",
                                    width=6, font=("Segoe UI", 10))
        self.ano_cb.pack(side="right")
        tk.Label(cab, text="Ano:", font=("Segoe UI", 10),
                 bg=C["fundo"], fg=C["texto_fraco"]).pack(side="right", padx=(0, 6))
        self.ano_cb.bind("<<ComboboxSelected>>", lambda e: self._atualizar_humor())

        tk.Frame(p, height=1, bg=C["borda"]).grid(
            row=0, column=0, sticky="sew", padx=36)

        # Área com scroll
        outer = tk.Frame(p, bg=C["fundo"])
        outer.grid(row=1, column=0, sticky="nsew", padx=0)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self.humor_canvas = tk.Canvas(outer, bg=C["fundo"],
                                      highlightthickness=0, bd=0)
        self.humor_canvas.grid(row=0, column=0, sticky="nsew")

        sc2 = tk.Scrollbar(outer, orient="vertical", bg=C["borda"],
                           troughcolor=C["fundo"], activebackground="#aaa",
                           relief="flat", bd=0, command=self.humor_canvas.yview)
        sc2.grid(row=0, column=1, sticky="ns")
        self.humor_canvas.configure(yscrollcommand=sc2.set)

        self.humor_inner = tk.Frame(self.humor_canvas, bg=C["fundo"])
        self._hcw = self.humor_canvas.create_window(
            (0, 0), window=self.humor_inner, anchor="nw")
        self.humor_inner.bind("<Configure>",
            lambda e: self.humor_canvas.configure(
                scrollregion=self.humor_canvas.bbox("all")))
        self.humor_canvas.bind("<Configure>",
            lambda e: self.humor_canvas.itemconfig(self._hcw, width=e.width))

    def _atualizar_humor(self):
        # Popula anos disponíveis
        anos = sorted({datetime.fromisoformat(p["data"]).year
                       for p in self.paginas if p.get("humor")}, reverse=True)
        if not anos:
            anos = [datetime.now().year]
        self.ano_cb.config(values=[str(a) for a in anos])
        if not self.ano_var.get() or int(self.ano_var.get()) not in anos:
            self.ano_var.set(str(anos[0]))

        ano = int(self.ano_var.get())

        # Agrupa por mês
        por_mes = defaultdict(list)  # mes(1-12) -> lista de valores
        entradas_por_mes = defaultdict(list)  # mes -> lista de (dia, humor, titulo)
        for pg in self.paginas:
            if not pg.get("humor"):
                continue
            dt = datetime.fromisoformat(pg["data"])
            if dt.year != ano:
                continue
            val = HUMOR_VALOR.get(pg["humor"], 3)
            por_mes[dt.month].append(val)
            entradas_por_mes[dt.month].append((dt.day, pg.get("humor",""), pg.get("titulo","") or dt.strftime("%d/%m")))

        # Limpa inner
        for w in self.humor_inner.winfo_children():
            w.destroy()

        # ── Gráfico de linha mensal ───────────────────────────────
        self.humor_inner.update_idletasks()
        cw = max(self.humor_canvas.winfo_width(), 600)

        graph_h = 200
        pad_l, pad_r, pad_t, pad_b = 60, 30, 20, 40

        gc = tk.Canvas(self.humor_inner, bg=C["area"], height=graph_h,
                       highlightthickness=1, highlightbackground=C["borda"],
                       bd=0)
        gc.grid(row=0, column=0, sticky="ew", padx=36, pady=(20, 6))
        self.humor_inner.grid_columnconfigure(0, weight=1)
        gc.update_idletasks()

        def desenhar_grafico(event=None):
            gc.delete("all")
            W = gc.winfo_width()
            if W < 10:
                W = cw - 72

            # Grade horizontal
            for i, label in enumerate(["Baixo","","Médio","","Alto"]):
                y = pad_t + (4 - i) * (graph_h - pad_t - pad_b) / 4
                gc.create_line(pad_l, y, W - pad_r, y,
                               fill=C["borda"], dash=(4, 4))
                if label:
                    gc.create_text(pad_l - 8, y, text=label,
                                   font=("Segoe UI", 8), fill=C["texto_fraco"],
                                   anchor="e")

            # Pontos e linha
            meses_com_dados = [m for m in range(1, 13) if por_mes[m]]
            pontos = []
            step = (W - pad_l - pad_r) / 11

            for m in range(1, 13):
                x = pad_l + (m - 1) * step
                label_m = MESES_PT[m - 1]
                gc.create_text(x, graph_h - pad_b + 14, text=label_m,
                               font=("Segoe UI", 8), fill=C["texto_fraco"])
                if por_mes[m]:
                    media = sum(por_mes[m]) / len(por_mes[m])
                    y = pad_t + (6 - media) * (graph_h - pad_t - pad_b) / 5
                    pontos.append((x, y, m, media))

            # Linha de conexão
            if len(pontos) >= 2:
                for i in range(len(pontos) - 1):
                    x1, y1, _, _ = pontos[i]
                    x2, y2, _, _ = pontos[i + 1]
                    gc.create_line(x1, y1, x2, y2, fill=C["texto"], width=2)

            # Pontos
            for x, y, mes, media in pontos:
                r = 5
                gc.create_oval(x-r, y-r, x+r, y+r,
                               fill=C["texto"], outline=C["area"], width=2)
                emoji_humor = _emoji_para_valor(media)
                gc.create_text(x, y - 16, text=emoji_humor,
                               font=("Segoe UI Emoji", 11))

        gc.bind("<Configure>", lambda e: desenhar_grafico())
        self.humor_inner.after(50, desenhar_grafico)

        # ── Legenda de humores no ano ─────────────────────────────
        contagem = defaultdict(int)
        for pg in self.paginas:
            if not pg.get("humor"): continue
            if datetime.fromisoformat(pg["data"]).year != ano: continue
            contagem[pg["humor"]] += 1

        if contagem:
            leg_frame = tk.Frame(self.humor_inner, bg=C["fundo"])
            leg_frame.grid(row=1, column=0, sticky="ew", padx=36, pady=(4, 16))

            tk.Label(leg_frame, text=f"Resumo de {ano}",
                     font=("Georgia", 13, "bold"),
                     bg=C["fundo"], fg=C["texto"]).grid(
                row=0, column=0, columnspan=7, sticky="w", pady=(0, 8))

            total = sum(contagem.values())
            col = 0
            for humor, n in sorted(contagem.items(), key=lambda x: -x[1]):
                emoji = humor.split()[0]
                nome  = " ".join(humor.split()[1:])
                pct   = round(100 * n / total)
                box = tk.Frame(leg_frame, bg=C["area"],
                               highlightthickness=1,
                               highlightbackground=C["borda"])
                box.grid(row=1, column=col, padx=(0, 8), pady=2, sticky="n")
                tk.Label(box, text=emoji, font=("Segoe UI Emoji", 20),
                         bg=C["area"]).pack(padx=14, pady=(10, 2))
                tk.Label(box, text=nome, font=("Segoe UI", 9),
                         bg=C["area"], fg=C["texto_fraco"]).pack()
                tk.Label(box, text=f"{n}x  ({pct}%)",
                         font=("Segoe UI", 9, "bold"),
                         bg=C["area"], fg=C["texto"]).pack(pady=(2, 10))
                col += 1

        # ── Calendário por mês ────────────────────────────────────
        tk.Frame(self.humor_inner, height=1, bg=C["borda"]).grid(
            row=2, column=0, sticky="ew", padx=36, pady=(0, 16))

        tk.Label(self.humor_inner, text=f"Calendário de {ano}",
                 font=("Georgia", 13, "bold"),
                 bg=C["fundo"], fg=C["texto"]).grid(
            row=3, column=0, sticky="w", padx=36, pady=(0, 10))

        cal_frame = tk.Frame(self.humor_inner, bg=C["fundo"])
        cal_frame.grid(row=4, column=0, sticky="ew", padx=36, pady=(0, 30))

        for mi, mes_nome in enumerate(MESES_PT):
            mes = mi + 1
            col_frame = tk.Frame(cal_frame, bg=C["fundo"])
            col_frame.grid(row=mi // 4, column=mi % 4, padx=8, pady=8, sticky="n")

            tk.Label(col_frame, text=mes_nome, font=("Segoe UI", 9, "bold"),
                     bg=C["fundo"], fg=C["texto"]).grid(
                row=0, column=0, columnspan=7, sticky="w")

            # Dias da semana
            for di, d in enumerate(["S","T","Q","Q","S","S","D"]):
                tk.Label(col_frame, text=d, font=("Segoe UI", 7),
                         bg=C["fundo"], fg=C["texto_fraco"],
                         width=3).grid(row=1, column=di)

            # Entradas deste mês indexadas por dia
            dias_humor = {}
            for (dia, humor, titulo) in entradas_por_mes[mes]:
                dias_humor[dia] = (humor.split()[0] if humor else "·", titulo)

            primeiro_dia, num_dias = calendar.monthrange(ano, mes)
            # domingo = 6 em Python, mas queremos seg=0 ... dom=6
            offset = primeiro_dia  # 0=seg

            dia_atual = 1
            for semana in range(6):
                for wd in range(7):
                    pos = semana * 7 + wd
                    if pos < offset or dia_atual > num_dias:
                        tk.Label(col_frame, text="", width=3,
                                 bg=C["fundo"]).grid(row=semana+2, column=wd)
                    else:
                        emoji, titulo = dias_humor.get(dia_atual, ("", ""))
                        if emoji:
                            cell = tk.Label(col_frame, text=emoji,
                                            font=("Segoe UI Emoji", 9),
                                            bg=C["fundo"], cursor="hand2",
                                            width=2)
                            tt = titulo or f"Dia {dia_atual}"
                            cell.bind("<Enter>",
                                lambda e, t=tt, em=emoji: self._tooltip_show(e, f"{em} {t}"))
                            cell.bind("<Leave>", self._tooltip_hide)
                        else:
                            cell = tk.Label(col_frame,
                                            text=str(dia_atual),
                                            font=("Segoe UI", 7),
                                            bg=C["fundo"],
                                            fg=C["texto_fraco"], width=3)
                        cell.grid(row=semana+2, column=wd)
                        dia_atual += 1
                if dia_atual > num_dias:
                    break

        self.humor_canvas.update_idletasks()
        self.humor_canvas.configure(scrollregion=self.humor_canvas.bbox("all"))

    # ── Tooltip simples ───────────────────────────────────────────────────────

    def _tooltip_show(self, event, texto):
        self._tip = tk.Toplevel(self.root)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{event.x_root+12}+{event.y_root-28}")
        tk.Label(self._tip, text=texto, font=("Segoe UI", 9),
                 bg=C["texto"], fg=C["area"], padx=8, pady=4).pack()

    def _tooltip_hide(self, event=None):
        if hasattr(self, "_tip") and self._tip:
            try: self._tip.destroy()
            except: pass

    # ═════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════════

    def _btn(self, parent, texto, cmd, fg, bg):
        return tk.Button(parent, text=texto, command=cmd,
                         bg=bg, fg=fg, font=("Segoe UI", 10),
                         relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                         activebackground="#333333", activeforeground=fg)

    def _habilitar(self, on=True):
        st = "normal" if on else "disabled"
        self.texto.config(state=st)
        self.humor_cb.config(state="readonly" if on else "disabled")
        self.pasta_cb.config(state="readonly" if on else "disabled")
        self.btn_salvar.config(state=st)
        self.entry_titulo.config(state=st,
                                 fg=C["texto"] if on else C["texto_fraco"])

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
        if pid in self.expandidas: self.expandidas.discard(pid)
        else: self.expandidas.add(pid)
        self._redesenhar_arvore()

    # ═════════════════════════════════════════════════════════════════════════
    # AÇÕES — PASTAS
    # ═════════════════════════════════════════════════════════════════════════

    def _nova_pasta(self):
        nome = simpledialog.askstring("Nova Pasta", "Nome da pasta:", parent=self.root)
        if not nome or not nome.strip(): return
        nova = {"id": _novo_id(), "nome": nome.strip()}
        self.pastas.append(nova)
        self.expandidas.add(nova["id"])
        self._salvar_todos()
        self._atualizar_pasta_cb()
        self._redesenhar_arvore()

    def _renomear_pasta(self, pid):
        pasta = next((p for p in self.pastas if p["id"] == pid), None)
        if not pasta: return
        novo = simpledialog.askstring("Renomear", "Novo nome:",
                                      initialvalue=pasta["nome"], parent=self.root)
        if not novo or not novo.strip(): return
        pasta["nome"] = novo.strip()
        self._salvar_todos(); self._atualizar_pasta_cb(); self._redesenhar_arvore()

    def _excluir_pasta(self, pid):
        pasta = next((p for p in self.pastas if p["id"] == pid), None)
        if not pasta: return
        n = sum(1 for p in self.paginas if p.get("pasta_id") == pid)
        msg = f"Excluir a pasta \"{pasta['nome']}\"?"
        if n: msg += f"\n\nAs {n} página(s) ficarão sem pasta."
        if not messagebox.askyesno("Confirmar", msg): return
        for p in self.paginas:
            if p.get("pasta_id") == pid: p["pasta_id"] = None
        self.pastas = [p for p in self.pastas if p["id"] != pid]
        self.expandidas.discard(pid)
        self._salvar_todos(); self._atualizar_pasta_cb(); self._redesenhar_arvore()

    # ═════════════════════════════════════════════════════════════════════════
    # AÇÕES — PÁGINAS
    # ═════════════════════════════════════════════════════════════════════════

    def _nova_pagina(self):
        self.pagina_atual_id = None
        self._trocar_aba("diario")
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
        pg = next((x for x in self.paginas if x["id"] == pid), None)
        if not pg: return
        self.pagina_atual_id = pid
        self._trocar_aba("diario")
        dt = datetime.fromisoformat(pg["data"])
        self.label_data.config(
            text=dt.strftime("%A, %d de %B de %Y — %H:%M").capitalize())
        self._habilitar(True)
        self._atualizar_pasta_cb()
        self.titulo_var.set(pg.get("titulo", ""))
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", pg.get("texto", ""))
        self.humor_var.set(pg.get("humor", HUMOR_OPCOES[0]))
        pasta_id = pg.get("pasta_id")
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
        titulo     = self.titulo_var.get().strip()
        humor      = self.humor_var.get()
        pasta_nome = self.pasta_var.get()
        pasta_id   = None
        if pasta_nome != "Sem pasta":
            pasta = next((x for x in self.pastas if x["nome"] == pasta_nome), None)
            if pasta: pasta_id = pasta["id"]

        if self.pagina_atual_id:
            pg = next((x for x in self.paginas if x["id"] == self.pagina_atual_id), None)
            if pg: pg.update({"titulo": titulo, "texto": conteudo,
                               "humor": humor, "pasta_id": pasta_id})
        else:
            nova = {"id": _novo_id(), "data": datetime.now().isoformat(),
                    "titulo": titulo, "texto": conteudo,
                    "humor": humor, "pasta_id": pasta_id}
            self.paginas.append(nova)
            self.pagina_atual_id = nova["id"]
            if pasta_id: self.expandidas.add(pasta_id)

        self._salvar_todos()
        self._redesenhar_arvore()
        self._flash("✓ Página salva")

    def _menu_pagina(self, event, pid):
        menu = tk.Menu(self.root, tearoff=0, bg=C["sidebar2"],
                       fg=C["texto_side"], activebackground="#333",
                       activeforeground="white", relief="flat", bd=0)
        menu.add_command(label="✏️  Abrir", command=lambda: self._abrir_pagina(pid))
        menu.add_separator()
        menu.add_command(label="📁  Mover para pasta...",
                         command=lambda: self._mover_pagina(pid))
        menu.add_separator()
        menu.add_command(label="🗑  Excluir", command=lambda: self._excluir_pagina(pid))
        menu.tk_popup(event.x_root, event.y_root)

    def _mover_pagina(self, pid):
        pg = next((x for x in self.paginas if x["id"] == pid), None)
        if not pg: return
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
        ttk.Combobox(win, textvariable=var, values=opcoes,
                     state="readonly", style="Humor.TCombobox",
                     width=20, font=("Segoe UI", 10)).pack(pady=4)
        def confirmar():
            nome = var.get()
            pg["pasta_id"] = None
            if nome != "Sem pasta":
                pasta = next((x for x in self.pastas if x["nome"] == nome), None)
                if pasta:
                    pg["pasta_id"] = pasta["id"]
                    self.expandidas.add(pasta["id"])
            self._salvar_todos(); self._redesenhar_arvore(); win.destroy()
        self._btn(win, "Mover", confirmar, C["btn_pri_fg"], C["btn_pri"]).pack(pady=12)

    def _excluir_pagina(self, pid=None):
        if pid is None: pid = self.pagina_atual_id
        if not pid:
            messagebox.showinfo("Atenção", "Nenhuma página selecionada.")
            return
        pg = next((x for x in self.paginas if x["id"] == pid), None)
        nome = (pg.get("titulo") or "esta página") if pg else "esta página"
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
        self._salvar_todos(); self._redesenhar_arvore()

    def _excluir_selecionado(self):
        if self.sel_tipo == "pasta":
            self._excluir_pasta(self.sel_id)
            self.sel_tipo = None
        elif self.pagina_atual_id:
            self._excluir_pagina(self.pagina_atual_id)
        else:
            messagebox.showinfo("Atenção",
                "Selecione uma página ou clique em uma pasta para excluir.")


# ── Utilitários ──────────────────────────────────────────────────────────────

def _emoji_para_valor(v):
    if v >= 5.5: return "🤩"
    if v >= 4.5: return "😊"
    if v >= 3.5: return "😌"
    if v >= 2.5: return "😐"
    if v >= 1.5: return "😴"
    return "😔"


if __name__ == "__main__":
    root = tk.Tk()
    app = DiarioApp(root)
    root.mainloop()
