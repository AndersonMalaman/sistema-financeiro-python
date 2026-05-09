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

# --- CONFIGURAÇÃO DE CAMINHOS ---
DIRETORIO_DB = r"C:\Users\Anderson Malaman\OneDrive\Sistema\DB"
CAMINHO_DB = os.path.join(DIRETORIO_DB, "financas_residenciais.db")
DIRETORIO_APP = r"C:\Users\Anderson Malaman\OneDrive\Sistema\Aplicacao"

for pasta in [DIRETORIO_DB, DIRETORIO_APP]:
    if not os.path.exists(pasta): os.makedirs(pasta)

def conectar_db():
    conn = sqlite3.connect(CAMINHO_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS transacoes 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, descricao TEXT, valor REAL, tipo TEXT, categoria TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS lembretes_vencimento 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, vencimento TEXT, descricao TEXT, 
                       mes_referencia INTEGER, ano_referencia INTEGER, tipo TEXT, 
                       status TEXT DEFAULT 'Pendente', data_pagamento TEXT)''')
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
        self.tab_lembretes = self.tabview.add(" Planejamento de Contas ")

        self.configurar_aba_fluxo()
        self.configurar_aba_lembretes()
        self.atualizar_tabela_fluxo()
        self.atualizar_tabela_lembretes()

    # ==========================================
    # ABA 1: EXTRATO REAL (Resumo Profissional)
    # ==========================================
    def configurar_aba_fluxo(self):
        frame = ctk.CTkFrame(self.tab_fluxo)
        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text="Data:").grid(row=0, column=0, padx=5)
        self.ent_data_f = ctk.CTkEntry(frame, width=110); self.ent_data_f.insert(0, datetime.date.today().strftime("%d/%m/%Y")); self.ent_data_f.grid(row=0, column=1, padx=5, pady=10)
        
        ctk.CTkLabel(frame, text="Descrição:").grid(row=0, column=2, padx=5)
        self.ent_desc_f = ctk.CTkEntry(frame, width=250); self.ent_desc_f.grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(frame, text="Valor R$:").grid(row=0, column=4, padx=5)
        self.ent_valor_f = ctk.CTkEntry(frame, width=100); self.ent_valor_f.grid(row=0, column=5, padx=5)

        self.combo_tipo = ctk.CTkComboBox(frame, values=["Receita", "Despesa", "Investimento"], width=110, command=self.atualizar_categorias)
        self.combo_tipo.set("Despesa"); self.combo_tipo.grid(row=1, column=1, padx=5, pady=10)
        
        self.combo_cat = ctk.CTkComboBox(frame, values=["Contas Fixas", "Lazer", "Outros"], width=250)
        self.combo_cat.grid(row=1, column=3, padx=5)

        ctk.CTkButton(frame, text="💾 Salvar Manual", fg_color="#2ecc71", command=self.salvar_fluxo).grid(row=1, column=4, columnspan=2)

        self.tree_fluxo = ttk.Treeview(self.tab_fluxo, columns=("ID", "Data", "Tipo", "Categoria", "Desc", "Valor"), show="headings", selectmode="extended")
        for col in ("ID", "Data", "Tipo", "Categoria", "Desc", "Valor"): self.tree_fluxo.heading(col, text=col)
        self.tree_fluxo.pack(fill="both", expand=True, padx=10, pady=5)

        self.frame_resumo = ctk.CTkFrame(self.tab_fluxo, fg_color="#1c1c1c")
        self.frame_resumo.pack(fill="x", padx=10, pady=5)
        self.lbl_receitas = ctk.CTkLabel(self.frame_resumo, text="Entradas: R$ 0.00", text_color="#2ecc71", font=("Arial", 14, "bold")); self.lbl_receitas.pack(side="left", padx=15, pady=10)
        self.lbl_despesas = ctk.CTkLabel(self.frame_resumo, text="Saídas: R$ 0.00", text_color="#e74c3c", font=("Arial", 14, "bold")); self.lbl_despesas.pack(side="left", padx=15)
        self.lbl_saldo = ctk.CTkLabel(self.frame_resumo, text="SALDO: R$ 0.00", font=("Arial", 16, "bold")); self.lbl_saldo.pack(side="right", padx=20)

    # ==========================================
    # ABA 2: PLANEJAMENTO (A MÁGICA DA MIGRAÇÃO)
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

        ctk.CTkButton(frame, text="🔔 Agendar", command=self.salvar_lembrete).grid(row=0, column=6, padx=10)

        filt_bar = ctk.CTkFrame(self.tab_lembretes, fg_color="transparent")
        filt_bar.pack(fill="x", padx=10, pady=5)
        self.combo_mes = ctk.CTkComboBox(filt_bar, values=[str(i) for i in range(1, 13)], width=80); self.combo_mes.set(str(datetime.date.today().month)); self.combo_mes.pack(side="left", padx=5)
        ctk.CTkButton(filt_bar, text="🔍 Ver", width=80, command=self.atualizar_tabela_lembretes).pack(side="left")

        self.tree_lemb = ttk.Treeview(self.tab_lembretes, columns=("ID", "Vencimento", "Descrição", "Tipo", "Status"), show="headings", selectmode="extended")
        for col in ("ID", "Vencimento", "Descrição", "Tipo", "Status"): self.tree_lemb.heading(col, text=col)
        self.tree_lemb.pack(fill="both", expand=True, padx=10, pady=5)

        btn_l = ctk.CTkFrame(self.tab_lembretes, fg_color="transparent")
        btn_l.pack(pady=10)
        ctk.CTkButton(btn_l, text="☑ Marcar Pago e Lançar no Caixa", fg_color="#27ae60", hover_color="#1e8449", command=self.alternar_status_e_migrar).pack(side="left", padx=5)
        ctk.CTkButton(btn_l, text="🗑️ Excluir", fg_color="#e74c3c", command=self.excluir_lembrete).pack(side="left", padx=5)
        ctk.CTkButton(btn_l, text="🖨️ PDF", fg_color="#8e44ad", command=self.gerar_pdf_lembretes).pack(side="right", padx=5)

    # --- FUNÇÃO MESTRE DE MIGRAÇÃO ---
    def alternar_status_e_migrar(self):
        items = self.tree_lemb.selection()
        if not items: return
        
        cursor = self.conn.cursor()
        hoje = datetime.date.today().strftime("%d/%m/%Y")

        for i in items:
            dados = self.tree_lemb.item(i)['values']
            id_l, venc, desc, tipo_l, status_atual = dados

            if "Pendente" in status_atual:
                # 1. Pergunta o valor real pago (pode ser diferente do planejado)
                dialogo = ctk.CTkInputDialog(text=f"Qual o valor real pago para '{desc}'?", title="Confirmar Pagamento")
                valor_pago = dialogo.get_input()
                
                if valor_pago:
                    try:
                        valor_num = float(valor_pago.replace(',', '.'))
                        # Atualiza Lembrete
                        cursor.execute("UPDATE lembretes_vencimento SET status='Pago', data_pagamento=? WHERE id=?", (hoje, id_l))
                        
                        # LANÇA AUTOMATICAMENTE NO EXTRATO REAL
                        cursor.execute("INSERT INTO transacoes (data, descricao, valor, tipo, categoria) VALUES (?, ?, ?, ?, ?)", 
                                       (hoje, f"PAGTO: {desc}", -valor_num, "Despesa", "Contas Fixas"))
                        
                        messagebox.showinfo("Sucesso", f"'{desc}' pago e lançado no extrato!")
                    except:
                        messagebox.showerror("Erro", "Valor inválido. Use apenas números.")
            else:
                # Se desmarcar o pago, apenas volta o status (não apaga do extrato por segurança)
                cursor.execute("UPDATE lembretes_vencimento SET status='Pendente', data_pagamento=NULL WHERE id=?", (id_l,))

        self.conn.commit()
        self.atualizar_tabela_lembretes()
        self.atualizar_tabela_fluxo()

    # --- RESTANTE DAS FUNÇÕES (PADRONIZADAS v12) ---
    def atualizar_categorias(self, escolha):
        if escolha == "Receita": self.combo_cat.configure(values=["Salário", "Proventos", "Vendas"])
        elif escolha == "Investimento": self.combo_cat.configure(values=["Ações", "Cripto", "CDB"])
        else: self.combo_cat.configure(values=["Contas Fixas", "Alimentação", "Transporte", "Lazer"])

    def salvar_fluxo(self):
        try:
            d, ds, v = self.ent_data_f.get(), self.ent_desc_f.get(), abs(float(self.ent_valor_f.get().replace(',', '.')))
            tipo, cat = self.combo_tipo.get(), self.combo_cat.get()
            valor_final = v if tipo == "Receita" else -v
            self.conn.cursor().execute("INSERT INTO transacoes (data, descricao, valor, tipo, categoria) VALUES (?, ?, ?, ?, ?)", (d, ds, valor_final, tipo, cat))
            self.conn.commit(); self.atualizar_tabela_fluxo()
        except: messagebox.showerror("Erro", "Dados inválidos")

    def atualizar_tabela_fluxo(self):
        for row in self.tree_fluxo.get_children(): self.tree_fluxo.delete(row)
        cursor = self.conn.cursor(); cursor.execute("SELECT * FROM transacoes ORDER BY id DESC")
        rows = cursor.fetchall(); t_rec = t_desp = t_inv = 0.0
        for r in rows:
            self.tree_fluxo.insert("", "end", values=(r[0], r[1], r[4], r[5], r[2], f"R$ {abs(r[3]):.2f}"))
            if r[4] == "Receita": t_rec += abs(r[3])
            elif r[4] == "Despesa": t_desp += abs(r[3])
            else: t_inv += abs(r[3])
        self.lbl_receitas.configure(text=f"Entradas: R$ {t_rec:.2f}"); self.lbl_despesas.configure(text=f"Saídas: R$ {t_desp + t_inv:.2f}")
        self.lbl_saldo.configure(text=f"SALDO: R$ {t_rec - t_desp - t_inv:.2f}")

    def salvar_lembrete(self):
        v, ds, t = self.ent_venc.get(), self.ent_desc_l.get(), self.tipo_var.get()
        try:
            data_obj = datetime.datetime.strptime(v, "%d/%m/%Y"); cursor = self.conn.cursor()
            if t == "Mensal":
                for m in range(data_obj.month, 13): cursor.execute("INSERT INTO lembretes_vencimento (vencimento, descricao, mes_referencia, ano_referencia, tipo) VALUES (?, ?, ?, ?, ?)", (f"{data_obj.day:02d}/{m:02d}/{data_obj.year}", ds, m, data_obj.year, t))
            else: cursor.execute("INSERT INTO lembretes_vencimento (vencimento, descricao, mes_referencia, ano_referencia, tipo) VALUES (?, ?, ?, ?, ?)", (v, ds, data_obj.month, data_obj.year, t))
            self.conn.commit(); self.atualizar_tabela_lembretes()
        except: messagebox.showerror("Erro", "Data inválida")

    def atualizar_tabela_lembretes(self):
        for row in self.tree_lemb.get_children(): self.tree_lemb.delete(row)
        mes = self.combo_mes.get(); cursor = self.conn.cursor(); cursor.execute("SELECT id, vencimento, descricao, tipo, status FROM lembretes_vencimento WHERE mes_referencia = ? ORDER BY id", (mes,))
        for r in cursor.fetchall(): self.tree_lemb.insert("", "end", values=(r[0], r[1], r[2], r[3], "☑ Pago" if r[4] == "Pago" else "☐ Pendente"))

    def excluir_lembrete(self):
        items = self.tree_lemb.selection()
        for i in items: self.conn.cursor().execute("DELETE FROM lembretes_vencimento WHERE id=?", (self.tree_lemb.item(i)['values'][0],))
        self.conn.commit(); self.atualizar_tabela_lembretes()

    def gerar_pdf_lembretes(self):
        mes = self.combo_mes.get(); caminho = os.path.join(DIRETORIO_APP, f"Lembretes_{mes}.pdf"); c = canvas.Canvas(caminho, pagesize=A4)
        c.setFont("Helvetica-Bold", 16); c.drawString(100, 800, f"CONTAS MÊS {mes}"); y = 760
        cursor = self.conn.cursor(); cursor.execute("SELECT vencimento, descricao, status, data_pagamento FROM lembretes_vencimento WHERE mes_referencia = ?", (mes,))
        for v, d, st, dp in cursor.fetchall():
            txt = f"[{v}] - {d} (PAGO EM: {dp})" if st == "Pago" else f"[{v}] - {d} [PENDENTE]"
            c.drawString(100, y, txt); y -= 25
        c.save(); messagebox.showinfo("PDF", "Gerado!")

if __name__ == "__main__":
    AppFinancas().mainloop()