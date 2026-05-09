import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import os
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- CONFIGURAÇÃO DE DESIGN ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- CONFIGURAÇÃO DE CAMINHOS NO ONEDRIVE ---
DIRETORIO_DB = r"C:\Users\Anderson Malaman\OneDrive\Sistema\DB"
CAMINHO_DB = os.path.join(DIRETORIO_DB, "financas_residenciais.db")
DIRETORIO_APP = r"C:\Users\Anderson Malaman\OneDrive\Sistema\Aplicacao"

for pasta in [DIRETORIO_DB, DIRETORIO_APP]:
    if not os.path.exists(pasta):
        os.makedirs(pasta)

def conectar_db():
    conn = sqlite3.connect(CAMINHO_DB)
    cursor = conn.cursor()
    # Tabela Transacoes (Atualizada com Tipo e Categoria)
    cursor.execute('''CREATE TABLE IF NOT EXISTS transacoes 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, descricao TEXT, valor REAL, tipo TEXT, categoria TEXT)''')
    
    # Tabela Lembretes
    cursor.execute('''CREATE TABLE IF NOT EXISTS lembretes_vencimento 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, vencimento TEXT, descricao TEXT, 
                       mes_referencia INTEGER, ano_referencia INTEGER, tipo TEXT, 
                       status TEXT DEFAULT 'Pendente', data_pagamento TEXT)''')
    
    # Atualizações de Banco Antigo (Migração de Dados)
    try: cursor.execute("ALTER TABLE transacoes ADD COLUMN tipo TEXT DEFAULT 'Despesa'")
    except: pass
    try: cursor.execute("ALTER TABLE transacoes ADD COLUMN categoria TEXT DEFAULT 'Geral'")
    except: pass

    try: cursor.execute("ALTER TABLE lembretes_vencimento ADD COLUMN mes_referencia INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE lembretes_vencimento ADD COLUMN ano_referencia INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE lembretes_vencimento ADD COLUMN tipo TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE lembretes_vencimento ADD COLUMN status TEXT DEFAULT 'Pendente'")
    except: pass
    try: cursor.execute("ALTER TABLE lembretes_vencimento ADD COLUMN data_pagamento TEXT")
    except: pass
    
    conn.commit()
    return conn

class AppFinancas(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gestão Financeira PRO - Anderson Malaman")
        self.geometry("1200x850")
        
        self.conn = conectar_db()
        self.ids_edicao_fluxo = []
        self.ids_edicao_lembrete = []

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=30, fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", relief="flat", font=("Arial", 10, "bold"))

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        self.tab_fluxo = self.tabview.add(" Extrato de Caixa Real ")
        self.tab_lembretes = self.tabview.add(" Planejamento de Contas (Lembretes) ")

        self.configurar_aba_fluxo()
        self.configurar_aba_lembretes()
        self.atualizar_tabela_fluxo()
        self.atualizar_tabela_lembretes()

    # ==========================================
    # ABA 1: FLUXO DE CAIXA (NOVO VISUAL PROFISSIONAL)
    # ==========================================
    def configurar_aba_fluxo(self):
        frame = ctk.CTkFrame(self.tab_fluxo)
        frame.pack(fill="x", padx=10, pady=10)

        # Linha 1: Dados básicos
        ctk.CTkLabel(frame, text="Data:").grid(row=0, column=0, padx=5, pady=10)
        self.ent_data_f = ctk.CTkEntry(frame, width=110)
        self.ent_data_f.insert(0, datetime.date.today().strftime("%d/%m/%Y"))
        self.ent_data_f.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(frame, text="Descrição:").grid(row=0, column=2, padx=5)
        self.ent_desc_f = ctk.CTkEntry(frame, width=250)
        self.ent_desc_f.grid(row=0, column=3, padx=5)

        ctk.CTkLabel(frame, text="Valor R$:").grid(row=0, column=4, padx=5)
        self.ent_valor_f = ctk.CTkEntry(frame, width=100)
        self.ent_valor_f.grid(row=0, column=5, padx=5)

        # Linha 2: Classificação Profissional
        ctk.CTkLabel(frame, text="Natureza:").grid(row=1, column=0, padx=5, pady=10)
        self.combo_tipo = ctk.CTkComboBox(frame, values=["Receita", "Despesa", "Investimento"], width=110, command=self.atualizar_categorias)
        self.combo_tipo.set("Despesa")
        self.combo_tipo.grid(row=1, column=1, padx=5)

        ctk.CTkLabel(frame, text="Categoria:").grid(row=1, column=2, padx=5)
        self.combo_cat = ctk.CTkComboBox(frame, values=["Contas Fixas", "Alimentação", "Lazer", "Transporte", "Saúde", "Outros"], width=250)
        self.combo_cat.grid(row=1, column=3, padx=5)

        ctk.CTkButton(frame, text="💾 Salvar Lançamento", fg_color="#2ecc71", hover_color="#27ae60", width=150, command=self.salvar_fluxo).grid(row=1, column=4, columnspan=2, padx=10)

        # Tabela com as Novas Colunas
        self.tree_fluxo = ttk.Treeview(self.tab_fluxo, columns=("ID", "Data", "Tipo", "Categoria", "Desc", "Valor"), show="headings", selectmode="extended")
        for col in ("ID", "Data", "Tipo", "Categoria", "Desc", "Valor"): self.tree_fluxo.heading(col, text=col)
        self.tree_fluxo.column("ID", width=40); self.tree_fluxo.column("Data", width=80); self.tree_fluxo.column("Tipo", width=100); self.tree_fluxo.column("Categoria", width=120); self.tree_fluxo.column("Valor", width=100)
        self.tree_fluxo.pack(fill="both", expand=True, padx=10, pady=5)

        # Painel de Resumo Profissional
        self.frame_resumo = ctk.CTkFrame(self.tab_fluxo, fg_color="#1c1c1c")
        self.frame_resumo.pack(fill="x", padx=10, pady=5)
        self.lbl_receitas = ctk.CTkLabel(self.frame_resumo, text="Entradas: R$ 0.00", text_color="#2ecc71", font=("Arial", 14, "bold"))
        self.lbl_receitas.pack(side="left", padx=15, pady=10)
        self.lbl_despesas = ctk.CTkLabel(self.frame_resumo, text="Saídas: R$ 0.00", text_color="#e74c3c", font=("Arial", 14, "bold"))
        self.lbl_despesas.pack(side="left", padx=15)
        self.lbl_invest = ctk.CTkLabel(self.frame_resumo, text="Investido: R$ 0.00", text_color="#3498db", font=("Arial", 14, "bold"))
        self.lbl_invest.pack(side="left", padx=15)
        self.lbl_saldo = ctk.CTkLabel(self.frame_resumo, text="SALDO CONTA: R$ 0.00", font=("Arial", 16, "bold"))
        self.lbl_saldo.pack(side="right", padx=20)

        # Botões de Ação
        btn_bar = ctk.CTkFrame(self.tab_fluxo, fg_color="transparent")
        btn_bar.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_bar, text="✏️ Editar", fg_color="#f39c12", width=120, command=self.preparar_edicao_fluxo).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="🗑️ Excluir", fg_color="#e74c3c", width=120, command=self.excluir_fluxo).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="📊 Excel", fg_color="#107c41", width=120, command=self.exportar_excel_fluxo).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="🖨️ PDF Balanço", fg_color="#c0392b", width=120, command=self.gerar_pdf_fluxo).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="⚠️ ZERAR BANCO", bg_color="transparent", fg_color="black", text_color="yellow", width=120, command=self.resetar_banco).pack(side="right", padx=5)

    def atualizar_categorias(self, escolha):
        """Muda as opções de categoria dependendo se é Receita, Despesa ou Investimento"""
        if escolha == "Receita":
            self.combo_cat.configure(values=["Salário", "Proventos/Dividendos", "Vendas", "Restituição", "Outras Receitas"])
            self.combo_cat.set("Salário")
        elif escolha == "Investimento":
            self.combo_cat.configure(values=["Ações", "Fundos Imobiliários", "Tesouro Direto", "CDB/LCI/LCA", "Criptomoedas", "Reserva de Emergência"])
            self.combo_cat.set("Ações")
        else: # Despesa
            self.combo_cat.configure(values=["Contas Fixas", "Alimentação", "Lazer", "Transporte", "Saúde", "Educação", "Moradia", "Outros"])
            self.combo_cat.set("Contas Fixas")

    # ==========================================
    # ABA 2: PLANEJAMENTO (LEMBRETES - Mantido igual a v11)
    # ==========================================
    def configurar_aba_lembretes(self):
        frame = ctk.CTkFrame(self.tab_lembretes)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text="Data:").grid(row=0, column=0, padx=5)
        self.ent_venc = ctk.CTkEntry(frame, width=110); self.ent_venc.insert(0, datetime.date.today().strftime("%d/%m/%Y")); self.ent_venc.grid(row=0, column=1, padx=5, pady=10)

        ctk.CTkLabel(frame, text="Descrição:").grid(row=0, column=2, padx=5)
        self.ent_desc_l = ctk.CTkEntry(frame, width=280); self.ent_desc_l.grid(row=0, column=3, padx=5)

        self.tipo_var = ctk.StringVar(value="Esporádica")
        ctk.CTkRadioButton(frame, text="Mensal", variable=self.tipo_var, value="Mensal").grid(row=0, column=4, padx=5)
        ctk.CTkRadioButton(frame, text="Esporádica", variable=self.tipo_var, value="Esporádica").grid(row=0, column=5, padx=5)

        ctk.CTkButton(frame, text="🔔 Agendar", command=self.salvar_lembrete, width=100).grid(row=0, column=6, padx=10)

        filt_bar = ctk.CTkFrame(self.tab_lembretes, fg_color="transparent")
        filt_bar.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(filt_bar, text="Filtrar Mês:").pack(side="left", padx=5)
        self.combo_mes = ctk.CTkComboBox(filt_bar, values=[str(i) for i in range(1, 13)], width=80); self.combo_mes.set(str(datetime.date.today().month)); self.combo_mes.pack(side="left", padx=5)
        ctk.CTkButton(filt_bar, text="🔍 Ver", width=80, command=self.atualizar_tabela_lembretes).pack(side="left")

        self.tree_lemb = ttk.Treeview(self.tab_lembretes, columns=("ID", "Vencimento", "Descrição", "Tipo", "Status"), show="headings", selectmode="extended")
        for col in ("ID", "Vencimento", "Descrição", "Tipo", "Status"): self.tree_lemb.heading(col, text=col)
        self.tree_lemb.column("ID", width=40); self.tree_lemb.column("Vencimento", width=100); self.tree_lemb.column("Status", width=120)
        self.tree_lemb.pack(fill="both", expand=True, padx=10, pady=5)

        btn_l = ctk.CTkFrame(self.tab_lembretes, fg_color="transparent")
        btn_l.pack(pady=10)
        ctk.CTkButton(btn_l, text="☑ Marcar Pago / Pendente", fg_color="#27ae60", command=self.alternar_status_pagamento).pack(side="left", padx=5)
        ctk.CTkButton(btn_l, text="✏️ Editar", fg_color="#f39c12", command=self.preparar_edicao_lembrete).pack(side="left", padx=5)
        ctk.CTkButton(btn_l, text="🗑️ Excluir", fg_color="#e74c3c", command=self.excluir_lembrete).pack(side="left", padx=5)
        ctk.CTkButton(btn_l, text="🖨️ PDF Lembretes", fg_color="#8e44ad", command=self.gerar_pdf_lembretes).pack(side="right", padx=5)

    # --- LÓGICAS DO FLUXO PROFISSIONAL ---
    def salvar_fluxo(self):
        try:
            d = self.ent_data_f.get()
            ds = self.ent_desc_f.get()
            tipo = self.combo_tipo.get()
            cat = self.combo_cat.get()
            v = abs(float(self.ent_valor_f.get().replace(',', '.'))) # Pega valor sempre positivo

            # Inteligência: Se é Saída ou Investimento, salva como negativo no banco pra facilitar a conta do saldo real
            valor_bd = v if tipo == "Receita" else -v

            cursor = self.conn.cursor()
            if self.ids_edicao_fluxo:
                for idx in self.ids_edicao_fluxo: 
                    cursor.execute("UPDATE transacoes SET data=?, descricao=?, valor=?, tipo=?, categoria=? WHERE id=?", (d, ds, valor_bd, tipo, cat, idx))
                self.ids_edicao_fluxo = []
            else:
                cursor.execute("INSERT INTO transacoes (data, descricao, valor, tipo, categoria) VALUES (?, ?, ?, ?, ?)", (d, ds, valor_bd, tipo, cat))
            
            self.conn.commit()
            self.atualizar_tabela_fluxo()
            self.ent_desc_f.delete(0, 'end'); self.ent_valor_f.delete(0, 'end')
        except Exception as e: messagebox.showerror("Erro", "Verifique o valor ou os campos!")

    def atualizar_tabela_fluxo(self):
        for row in self.tree_fluxo.get_children(): self.tree_fluxo.delete(row)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, data, tipo, categoria, descricao, valor FROM transacoes ORDER BY id DESC")
        rows = cursor.fetchall()
        
        tot_rec = tot_desp = tot_inv = saldo_conta = 0.0

        for r in rows:
            id_val, data, tipo, cat, desc, valor = r
            
            # Formatação na Tabela (Mostra o número absoluto)
            valor_formatado = f"R$ {abs(valor):.2f}"
            self.tree_fluxo.insert("", "end", values=(id_val, data, tipo, cat, desc, valor_formatado))

            # Cálculos do Balanço
            if tipo == "Receita":
                tot_rec += abs(valor)
                saldo_conta += abs(valor)
            elif tipo == "Despesa":
                tot_desp += abs(valor)
                saldo_conta -= abs(valor)
            elif tipo == "Investimento":
                tot_inv += abs(valor)
                saldo_conta -= abs(valor)

        # Atualiza os painéis visuais
        self.lbl_receitas.configure(text=f"Entradas: R$ {tot_rec:.2f}")
        self.lbl_despesas.configure(text=f"Saídas: R$ {tot_desp:.2f}")
        self.lbl_invest.configure(text=f"Investido: R$ {tot_inv:.2f}")
        self.lbl_saldo.configure(text=f"SALDO CONTA: R$ {saldo_conta:.2f}", text_color="#2ecc71" if saldo_conta >= 0 else "#e74c3c")

    def preparar_edicao_fluxo(self):
        items = self.tree_fluxo.selection()
        if not items: return
        self.ids_edicao_fluxo = [self.tree_fluxo.item(i)['values'][0] for i in items]
        v = self.tree_fluxo.item(items[0])['values'] # Pega a primeira linha
        self.ent_data_f.delete(0, 'end'); self.ent_data_f.insert(0, v[1])
        self.combo_tipo.set(v[2])
        self.atualizar_categorias(v[2])
        self.combo_cat.set(v[3])
        self.ent_desc_f.delete(0, 'end'); self.ent_desc_f.insert(0, v[4])
        
        # Tira o R$ pra editar o número limpo
        valor_limpo = str(v[5]).replace("R$ ", "")
        self.ent_valor_f.delete(0, 'end'); self.ent_valor_f.insert(0, valor_limpo)

    def excluir_fluxo(self):
        items = self.tree_fluxo.selection()
        if items and messagebox.askyesno("Excluir", f"Apagar {len(items)} registros?"):
            for i in items: self.conn.cursor().execute("DELETE FROM transacoes WHERE id=?", (self.tree_fluxo.item(i)['values'][0],))
            self.conn.commit(); self.atualizar_tabela_fluxo()

    def exportar_excel_fluxo(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT data, tipo, categoria, descricao, valor FROM transacoes")
        df = pd.DataFrame(cursor.fetchall(), columns=["Data", "Natureza", "Categoria", "Descrição", "Valor Real"])
        caminho = os.path.join(DIRETORIO_APP, "Balanco_Financeiro_PRO.xlsx")
        df.to_excel(caminho, index=False); messagebox.showinfo("Excel", f"Salvo com sucesso em: {caminho}")

    # --- NOVO PDF: BALANÇO FINANCEIRO DO CAIXA REAL ---
    def gerar_pdf_fluxo(self):
        caminho = os.path.join(DIRETORIO_APP, f"Relatorio_Fluxo_{datetime.date.today().strftime('%d_%m_%Y')}.pdf")
        c = canvas.Canvas(caminho, pagesize=A4)
        c.setFont("Helvetica-Bold", 16); c.drawString(50, 800, "BALANÇO FINANCEIRO - EXTRATO REAL")
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT data, tipo, categoria, descricao, valor FROM transacoes ORDER BY id ASC")
        registros = cursor.fetchall()
        
        tot_rec = tot_desp = tot_inv = 0.0
        
        y = 760
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "DATA")
        c.drawString(120, y, "NATUREZA")
        c.drawString(220, y, "CATEGORIA")
        c.drawString(350, y, "DESCRIÇÃO")
        c.drawString(500, y, "VALOR")
        c.line(50, y-5, 550, y-5)
        
        y -= 20
        c.setFont("Helvetica", 10)
        for d, t, cat, desc, v in registros:
            if t == "Receita": tot_rec += abs(v)
            elif t == "Despesa": tot_desp += abs(v)
            elif t == "Investimento": tot_inv += abs(v)
            
            c.drawString(50, y, str(d))
            c.drawString(120, y, str(t))
            c.drawString(220, y, str(cat)[:18])
            c.drawString(350, y, str(desc)[:20])
            c.drawString(500, y, f"R$ {abs(v):.2f}")
            
            y -= 15
            if y < 100:
                c.showPage(); c.setFont("Helvetica", 10); y = 800
                
        # Rodapé com Resumo Financeiro
        c.line(50, y-10, 550, y-10)
        y -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "RESUMO GERAL:")
        c.setFont("Helvetica", 11)
        c.drawString(50, y-20, f"Total de Entradas (Receitas/Proventos): R$ {tot_rec:.2f}")
        c.drawString(50, y-40, f"Total de Saídas (Despesas/Gastos): R$ {tot_desp:.2f}")
        c.drawString(50, y-60, f"Total de Investimentos (Aportes): R$ {tot_inv:.2f}")
        
        saldo = tot_rec - tot_desp - tot_inv
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y-85, f"SALDO EM CONTA: R$ {saldo:.2f}")

        c.save(); messagebox.showinfo("PDF Gerado", f"Balanço Financeiro gerado em:\n{caminho}")

    # --- FUNÇÕES DE LEMBRETE (Mantidas intactas da v11) ---
    def alternar_status_pagamento(self):
        items = self.tree_lemb.selection()
        if not items: return
        cursor = self.conn.cursor(); hoje = datetime.date.today().strftime("%d/%m/%Y")
        for i in items:
            id_l = self.tree_lemb.item(i)['values'][0]
            status_atual = self.tree_lemb.item(i)['values'][4]
            if "Pendente" in status_atual: cursor.execute("UPDATE lembretes_vencimento SET status='Pago', data_pagamento=? WHERE id=?", (hoje, id_l))
            else: cursor.execute("UPDATE lembretes_vencimento SET status='Pendente', data_pagamento=NULL WHERE id=?", (id_l,))
        self.conn.commit(); self.atualizar_tabela_lembretes()

    def salvar_lembrete(self):
        v, ds, t = self.ent_venc.get(), self.ent_desc_l.get(), self.tipo_var.get()
        if not v or not ds: return
        try:
            data_obj = datetime.datetime.strptime(v, "%d/%m/%Y")
            cursor = self.conn.cursor()
            if self.ids_edicao_lembrete:
                if len(self.ids_edicao_lembrete) == 1:
                    id_l = self.ids_edicao_lembrete[0]
                    cursor.execute("SELECT descricao, mes_referencia, ano_referencia, tipo FROM lembretes_vencimento WHERE id=?", (id_l,))
                    res = cursor.fetchone()
                    if res and res[3] == "Mensal":
                        old_desc, mes_ref, ano_ref, old_tipo = res
                        resp = messagebox.askyesnocancel("Editar Série", "SIM = Replicar para os próximos meses.\nNÃO = Apenas este mês.")
                        if resp is True:
                            cursor.execute("DELETE FROM lembretes_vencimento WHERE descricao=? AND mes_referencia>=? AND ano_referencia=?", (old_desc, mes_ref, ano_ref))
                            for m in range(mes_ref, 13): cursor.execute("INSERT INTO lembretes_vencimento (vencimento, descricao, mes_referencia, ano_referencia, tipo) VALUES (?, ?, ?, ?, ?)", (f"{data_obj.day:02d}/{m:02d}/{data_obj.year}", ds, m, data_obj.year, t))
                        elif resp is False: cursor.execute("UPDATE lembretes_vencimento SET vencimento=?, descricao=?, tipo=? WHERE id=?", (v, ds, t, id_l))
                        else: return
                    else: cursor.execute("UPDATE lembretes_vencimento SET vencimento=?, descricao=?, tipo=? WHERE id=?", (v, ds, t, id_l))
                else:
                    for idx in self.ids_edicao_lembrete: cursor.execute("UPDATE lembretes_vencimento SET vencimento=?, descricao=?, tipo=? WHERE id=?", (v, ds, t, idx))
                self.ids_edicao_lembrete = []
            else:
                if t == "Mensal":
                    for m in range(data_obj.month, 13): cursor.execute("INSERT INTO lembretes_vencimento (vencimento, descricao, mes_referencia, ano_referencia, tipo) VALUES (?, ?, ?, ?, ?)", (f"{data_obj.day:02d}/{m:02d}/{data_obj.year}", ds, m, data_obj.year, t))
                else: cursor.execute("INSERT INTO lembretes_vencimento (vencimento, descricao, mes_referencia, ano_referencia, tipo) VALUES (?, ?, ?, ?, ?)", (v, ds, data_obj.month, data_obj.year, t))
            self.conn.commit(); self.atualizar_tabela_lembretes(); self.ent_desc_l.delete(0, 'end')
        except: messagebox.showerror("Erro", "Data inválida!")

    def excluir_lembrete(self):
        items = self.tree_lemb.selection()
        if not items: return
        cursor = self.conn.cursor()
        for i in items:
            id_l = self.tree_lemb.item(i)['values'][0]
            cursor.execute("SELECT descricao, mes_referencia, ano_referencia, tipo FROM lembretes_vencimento WHERE id=?", (id_l,))
            res = cursor.fetchone()
            if res and res[3] == "Mensal":
                resp = messagebox.askyesnocancel("Excluir Conta", "SIM = Apagar este mês e o futuro.\nNÃO = Apagar SÓ este.")
                if resp is True: cursor.execute("DELETE FROM lembretes_vencimento WHERE descricao=? AND mes_referencia>=? AND ano_referencia=?", (res[0], res[1], res[2]))
                elif resp is False: cursor.execute("DELETE FROM lembretes_vencimento WHERE id=?", (id_l,))
                else: continue
            else: cursor.execute("DELETE FROM lembretes_vencimento WHERE id=?", (id_l,))
        self.conn.commit(); self.atualizar_tabela_lembretes()

    def preparar_edicao_lembrete(self):
        items = self.tree_lemb.selection()
        if not items: return
        self.ids_edicao_lembrete = [self.tree_lemb.item(i)['values'][0] for i in items]
        v = self.tree_lemb.item(items[0])['values']
        self.ent_venc.delete(0, 'end'); self.ent_venc.insert(0, v[1])
        self.ent_desc_l.delete(0, 'end'); self.ent_desc_l.insert(0, v[2])
        self.tipo_var.set(v[3] if v[3] else "Esporádica")

    def atualizar_tabela_lembretes(self):
        for row in self.tree_lemb.get_children(): self.tree_lemb.delete(row)
        mes = self.combo_mes.get()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, vencimento, descricao, tipo, status FROM lembretes_vencimento WHERE mes_referencia = ? ORDER BY substr(vencimento,1,2) ASC", (mes,))
        for r in cursor.fetchall():
            status_icone = "☑ Pago" if r[4] == "Pago" else "☐ Pendente"
            self.tree_lemb.insert("", "end", values=(r[0], r[1], r[2], r[3], status_icone))

    def gerar_pdf_lembretes(self):
        mes = self.combo_mes.get()
        caminho = os.path.join(DIRETORIO_APP, f"Lembretes_Mes_{mes}.pdf")
        c = canvas.Canvas(caminho, pagesize=A4)
        c.setFont("Helvetica-Bold", 16); c.drawString(100, 800, f"CONTAS DO MÊS {mes}")
        y = 760
        cursor = self.conn.cursor(); cursor.execute("SELECT vencimento, descricao, status, data_pagamento FROM lembretes_vencimento WHERE mes_referencia = ? ORDER BY substr(vencimento,1,2)", (mes,))
        for v, d, st, dp in cursor.fetchall():
            texto = f"[{v}] - {d}   --->   (PAGO EM: {dp})" if st == "Pago" else f"[{v}] - {d}   --->   [PENDENTE]"
            c.drawString(100, y, texto); y -= 25
            if y < 50: c.showPage(); y = 800
        c.save(); messagebox.showinfo("PDF", f"Relatório do Mês {mes} gerado com os pagamentos!")

    def resetar_banco(self):
        if messagebox.askyesno("⚠️ ZERAR", "Apagar TUDO?"):
            self.conn.cursor().execute("DELETE FROM transacoes"); self.conn.cursor().execute("DELETE FROM lembretes_vencimento")
            self.conn.commit(); self.atualizar_tabela_fluxo(); self.atualizar_tabela_lembretes()

if __name__ == "__main__":
    app = AppFinancas()
    app.mainloop()