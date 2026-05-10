#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestão Financeira PRO - Versão Melhorada
Requisitos: customtkinter, reportlab, python-dateutil
Instalação: pip install customtkinter reportlab python-dateutil
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import datetime
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from dateutil import parser as dateparser
from decimal import Decimal, InvalidOperation
import logging
import csv
import sys

# ---------------------------
# Configuração básica
# ---------------------------

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = Path.home() / "OneDrive" / "Sistema"
DIRETORIO_DB = BASE_DIR / "DB"
DIRETORIO_APP = BASE_DIR / "Aplicacao"
CAMINHO_DB = DIRETORIO_DB / "financas_residenciais.db"

DIRETORIO_DB.mkdir(parents=True, exist_ok=True)
DIRETORIO_APP.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("gestao_financeira")

# Constantes
TIPO_RECEITA = "Receita"
TIPO_DESPESA = "Despesa"
TIPO_INVESTIMENTO = "Investimento"

CATEGORIAS_RECEITA = ["Salário", "Dividendos", "Vendas", "Restituição", "Outras Receitas"]
CATEGORIAS_DESPESA = ["Contas Fixas", "Alimentação", "Lazer", "Transporte", "Saúde", "Outros"]
CATEGORIAS_INVESTIMENTO = ["Ações", "Fundos Imobiliários", "Tesouro Direto", "Criptomoedas", "Reserva Emergência"]

# ---------------------------
# Utilitários
# ---------------------------

def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def data_hoje():
    return datetime.date.today().strftime("%d/%m/%Y")

def converter_valor(valor: str) -> float:
    """Converte strings como 'R$ 1.234,56' ou '1234.56' para float com validação."""
    if not valor or not str(valor).strip():
        raise ValueError("Valor vazio")
    s = str(valor).strip()
    s = s.replace("R$", "").replace(" ", "")
    # Normaliza: se houver apenas uma vírgula e nenhum ponto, trata vírgula como separador decimal
    if s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(".", "").replace(",", ".")
    else:
        # remove separadores de milhar comuns
        s = s.replace(",", "")
    try:
        return float(Decimal(s))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Formato de valor inválido: {valor}") from e

def parse_data(s: str) -> str:
    """Tenta parsear data em dd/mm/YYYY ou formatos flexíveis; retorna dd/mm/YYYY."""
    if not s or not str(s).strip():
        raise ValueError("Data vazia")
    s = str(s).strip()
    try:
        dt = datetime.datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        try:
            dt = dateparser.parse(s, dayfirst=True).date()
        except Exception as e:
            raise ValueError("Data inválida. Use dd/mm/aaaa.") from e
    return dt.strftime("%d/%m/%Y")

def criar_lembretes_mensais(conn, data_obj: datetime.date, descricao: str, meses: int = 12):
    """Cria lembretes mensais a partir da data_obj por 'meses' meses (inclui ano seguinte)."""
    day = data_obj.day
    start_month = data_obj.month
    start_year = data_obj.year
    for i in range(meses):
        m = (start_month + i - 1) % 12 + 1
        y = start_year + (start_month + i - 1) // 12
        venc = f"{day:02d}/{m:02d}/{y}"
        conn.execute("""
            INSERT INTO lembretes_vencimento
            (vencimento, descricao, mes_referencia, ano_referencia, tipo)
            VALUES (?, ?, ?, ?, ?)
        """, (venc, descricao, m, y, "Mensal"))

# ---------------------------
# Banco de dados
# ---------------------------

def conectar_db():
    conn = sqlite3.connect(str(CAMINHO_DB), timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                tipo TEXT NOT NULL,
                categoria TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lembretes_vencimento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vencimento TEXT NOT NULL,
                descricao TEXT NOT NULL,
                mes_referencia INTEGER NOT NULL,
                ano_referencia INTEGER NOT NULL,
                tipo TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_pagamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT,
                vencimento TEXT,
                data_pagamento TEXT,
                valor REAL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lembretes_mes ON lembretes_vencimento(mes_referencia);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transacoes_tipo ON transacoes(tipo);")
    return conn

# ---------------------------
# Aplicação
# ---------------------------

class AppFinancas(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gestão Financeira PRO v13.4 - Melhorado")
        self.geometry("1200x800")
        self.conn = conectar_db()
        self.configurar_estilo()
        self.criar_tabs()
        self.configurar_aba_fluxo()
        self.configurar_aba_lembretes()
        self.configurar_aba_historico()
        self.atualizar_tabela_fluxo()
        self.atualizar_tabela_lembretes()
        self.atualizar_tabela_historico()
        # Atalhos
        self.bind_all("<Delete>", lambda e: self.excluir_fluxo())
        self.bind_all("<Control-s>", lambda e: self.salvar_fluxo())

    # Estilo
    def configurar_estilo(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=28, fieldbackground="#2b2b2b", borderwidth=0)
        style.map("Treeview", background=[("selected", "#1f538d")])
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", relief="flat", font=("Arial", 10, "bold"))

    # Tabs
    def criar_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=8)
        self.tab_fluxo = self.tabview.add(" Extrato de Caixa ")
        self.tab_lembretes = self.tabview.add(" Planejamento ")
        self.tab_historico = self.tabview.add(" Histórico ")

    # Aba Extrato
    def configurar_aba_fluxo(self):
        frame = ctk.CTkFrame(self.tab_fluxo)
        frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(frame, text="Data").grid(row=0, column=0)
        self.ent_data_f = ctk.CTkEntry(frame, width=120)
        self.ent_data_f.insert(0, data_hoje())
        self.ent_data_f.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(frame, text="Descrição").grid(row=0, column=2)
        self.ent_desc_f = ctk.CTkEntry(frame, width=320)
        self.ent_desc_f.grid(row=0, column=3, padx=5)
        ctk.CTkLabel(frame, text="Valor").grid(row=0, column=4)
        self.ent_valor_f = ctk.CTkEntry(frame, width=120)
        self.ent_valor_f.grid(row=0, column=5)
        ctk.CTkLabel(frame, text="Natureza").grid(row=1, column=0)
        self.combo_tipo = ctk.CTkComboBox(frame, values=[TIPO_RECEITA, TIPO_DESPESA, TIPO_INVESTIMENTO], command=self.atualizar_categorias)
        self.combo_tipo.set(TIPO_DESPESA)
        self.combo_tipo.grid(row=1, column=1, pady=8)
        ctk.CTkLabel(frame, text="Categoria").grid(row=1, column=2)
        self.combo_cat = ctk.CTkComboBox(frame, values=CATEGORIAS_DESPESA, width=320)
        self.combo_cat.set(CATEGORIAS_DESPESA[0])
        self.combo_cat.grid(row=1, column=3)
        ctk.CTkButton(frame, text="💾 Salvar", fg_color="#2ecc71", hover_color="#27ae60", command=self.salvar_fluxo).grid(row=1, column=5)
        # Tabela
        colunas = ("ID", "Data", "Tipo", "Categoria", "Descrição", "Valor")
        self.tree_fluxo = ttk.Treeview(self.tab_fluxo, columns=colunas, show="headings", selectmode="extended")
        for col in colunas:
            self.tree_fluxo.heading(col, text=col)
        # Ajuste de colunas
        self.tree_fluxo.column("ID", width=50, anchor="center")
        self.tree_fluxo.column("Data", width=100, anchor="center")
        self.tree_fluxo.column("Tipo", width=110, anchor="center")
        self.tree_fluxo.column("Categoria", width=160, anchor="w")
        self.tree_fluxo.column("Descrição", width=420, anchor="w")
        self.tree_fluxo.column("Valor", width=140, anchor="e")
        self.tree_fluxo.pack(fill="both", expand=True, padx=10, pady=10)
        # Resumo
        resumo = ctk.CTkFrame(self.tab_fluxo)
        resumo.pack(fill="x", padx=10, pady=5)
        self.lbl_receitas = ctk.CTkLabel(resumo, text="Entradas: R$ 0,00", text_color="#2ecc71", font=("Arial", 14, "bold"))
        self.lbl_receitas.pack(side="left", padx=20)
        self.lbl_despesas = ctk.CTkLabel(resumo, text="Saídas: R$ 0,00", text_color="#e74c3c", font=("Arial", 14, "bold"))
        self.lbl_despesas.pack(side="left", padx=20)
        self.lbl_invest = ctk.CTkLabel(resumo, text="Investimentos: R$ 0,00", text_color="#3498db", font=("Arial", 14, "bold"))
        self.lbl_invest.pack(side="left", padx=20)
        self.lbl_saldo = ctk.CTkLabel(resumo, text="SALDO: R$ 0,00", font=("Arial", 16, "bold"))
        self.lbl_saldo.pack(side="right", padx=20)
        # Barra de botões
        barra = ctk.CTkFrame(self.tab_fluxo, fg_color="transparent")
        barra.pack(fill="x", padx=10)
        ctk.CTkButton(barra, text="🗑️ Excluir", fg_color="#e74c3c", hover_color="#c0392b", command=self.excluir_fluxo).pack(side="left")
        ctk.CTkButton(barra, text="📤 Exportar CSV", fg_color="#2980b9", command=self.exportar_transacoes_csv).pack(side="left", padx=6)

    def atualizar_categorias(self, escolha):
        if escolha == TIPO_RECEITA:
            self.combo_cat.configure(values=CATEGORIAS_RECEITA)
            self.combo_cat.set(CATEGORIAS_RECEITA[0])
        elif escolha == TIPO_INVESTIMENTO:
            self.combo_cat.configure(values=CATEGORIAS_INVESTIMENTO)
            self.combo_cat.set(CATEGORIAS_INVESTIMENTO[0])
        else:
            self.combo_cat.configure(values=CATEGORIAS_DESPESA)
            self.combo_cat.set(CATEGORIAS_DESPESA[0])

    def salvar_fluxo(self):
        try:
            data = parse_data(self.ent_data_f.get().strip())
            descricao = self.ent_desc_f.get().strip()
            if not descricao:
                raise ValueError("Descrição vazia.")
            tipo = self.combo_tipo.get()
            categoria = self.combo_cat.get()
            valor = converter_valor(self.ent_valor_f.get())
            valor_db = valor if tipo == TIPO_RECEITA else -abs(valor)
            with self.conn:
                self.conn.execute("""
                    INSERT INTO transacoes (data, descricao, valor, tipo, categoria)
                    VALUES (?, ?, ?, ?, ?)
                """, (data, descricao, valor_db, tipo, categoria))
            self.ent_desc_f.delete(0, "end")
            self.ent_valor_f.delete(0, "end")
            self.atualizar_tabela_fluxo()
            messagebox.showinfo("Sucesso", "Lançamento salvo.")
        except Exception as e:
            logger.exception("Erro ao salvar fluxo")
            messagebox.showerror("Erro", str(e))

    def atualizar_tabela_fluxo(self):
        self.tree_fluxo.delete(*self.tree_fluxo.get_children())
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transacoes ORDER BY id DESC")
        total_receitas = total_despesas = total_invest = saldo = 0.0
        for row in cursor.fetchall():
            valor = row["valor"]
            self.tree_fluxo.insert("", "end", values=(row["id"], row["data"], row["tipo"], row["categoria"], row["descricao"], moeda(abs(valor))))
            if row["tipo"] == TIPO_RECEITA:
                total_receitas += abs(valor)
                saldo += abs(valor)
            elif row["tipo"] == TIPO_DESPESA:
                total_despesas += abs(valor)
                saldo -= abs(valor)
            else:
                total_invest += abs(valor)
                saldo -= abs(valor)
        self.lbl_receitas.configure(text=f"Entradas: {moeda(total_receitas)}")
        self.lbl_despesas.configure(text=f"Saídas: {moeda(total_despesas)}")
        self.lbl_invest.configure(text=f"Investimentos: {moeda(total_invest)}")
        self.lbl_saldo.configure(text=f"SALDO: {moeda(saldo)}", text_color=("#2ecc71" if saldo >= 0 else "#e74c3c"))

    def excluir_fluxo(self):
        itens = self.tree_fluxo.selection()
        if not itens:
            return
        confirmar = messagebox.askyesno("Confirmação", "Deseja excluir os lançamentos selecionados?")
        if not confirmar:
            return
        try:
            with self.conn:
                for item in itens:
                    item_id = self.tree_fluxo.item(item)["values"][0]
                    self.conn.execute("DELETE FROM transacoes WHERE id=?", (item_id,))
            self.atualizar_tabela_fluxo()
        except Exception:
            logger.exception("Erro ao excluir lançamentos")
            messagebox.showerror("Erro", "Falha ao excluir lançamentos.")

    # Aba Planejamento
    def configurar_aba_lembretes(self):
        frame = ctk.CTkFrame(self.tab_lembretes)
        frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(frame, text="Vencimento").grid(row=0, column=0)
        self.ent_venc = ctk.CTkEntry(frame, width=120)
        self.ent_venc.insert(0, data_hoje())
        self.ent_venc.grid(row=0, column=1)
        ctk.CTkLabel(frame, text="Descrição").grid(row=0, column=2)
        self.ent_desc_l = ctk.CTkEntry(frame, width=320)
        self.ent_desc_l.grid(row=0, column=3, padx=5)
        self.tipo_var = ctk.StringVar(value="Esporádica")
        ctk.CTkRadioButton(frame, text="Mensal", variable=self.tipo_var, value="Mensal").grid(row=0, column=4)
        ctk.CTkRadioButton(frame, text="Esporádica", variable=self.tipo_var, value="Esporádica").grid(row=0, column=5)
        ctk.CTkButton(frame, text="🔔 Agendar", command=self.salvar_lembrete).grid(row=0, column=6, padx=10)
        # Filtro
        filtro = ctk.CTkFrame(self.tab_lembretes, fg_color="transparent")
        filtro.pack(fill="x", padx=10)
        ctk.CTkLabel(filtro, text="Mês").pack(side="left")
        self.combo_mes = ctk.CTkComboBox(filtro, values=[str(i) for i in range(1, 13)], width=80)
        self.combo_mes.set(str(datetime.date.today().month))
        self.combo_mes.pack(side="left", padx=5)
        ctk.CTkButton(filtro, text="🔍 Ver", command=self.atualizar_tabela_lembretes).pack(side="left")
        # Tabela
        colunas = ("ID", "Vencimento", "Descrição", "Tipo")
        self.tree_lemb = ttk.Treeview(self.tab_lembretes, columns=colunas, show="headings", selectmode="extended")
        for col in colunas:
            self.tree_lemb.heading(col, text=col)
        self.tree_lemb.column("ID", width=50, anchor="center")
        self.tree_lemb.column("Vencimento", width=120, anchor="center")
        self.tree_lemb.column("Descrição", width=600, anchor="w")
        self.tree_lemb.column("Tipo", width=120, anchor="center")
        self.tree_lemb.pack(fill="both", expand=True, padx=10, pady=10)
        # Botões
        barra = ctk.CTkFrame(self.tab_lembretes, fg_color="transparent")
        barra.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(barra, text="☑ Pagar Conta", fg_color="#27ae60", hover_color="#1e8449", command=self.pagar_conta).pack(side="left", padx=5)
        ctk.CTkButton(barra, text="🗑️ Excluir", fg_color="#e74c3c", hover_color="#c0392b", command=self.excluir_lembrete).pack(side="left", padx=5)
        ctk.CTkButton(barra, text="🖨️ PDF", fg_color="#8e44ad", command=self.gerar_pdf_lembretes).pack(side="right", padx=5)

    def salvar_lembrete(self):
        try:
            vencimento_raw = self.ent_venc.get().strip()
            vencimento = parse_data(vencimento_raw)
            descricao = self.ent_desc_l.get().strip()
            if not descricao:
                raise ValueError("Descrição vazia.")
            tipo = self.tipo_var.get()
            data_obj = datetime.datetime.strptime(vencimento, "%d/%m/%Y").date()
            with self.conn:
                if tipo == "Mensal":
                    # cria 12 meses por padrão (pode ser parametrizado)
                    criar_lembretes_mensais(self.conn, data_obj, descricao, meses=12)
                else:
                    self.conn.execute("""
                        INSERT INTO lembretes_vencimento (vencimento, descricao, mes_referencia, ano_referencia, tipo)
                        VALUES (?, ?, ?, ?, ?)
                    """, (vencimento, descricao, data_obj.month, data_obj.year, tipo))
            self.ent_desc_l.delete(0, "end")
            self.atualizar_tabela_lembretes()
            messagebox.showinfo("Sucesso", "Conta planejada.")
        except Exception as e:
            logger.exception("Erro ao salvar lembrete")
            messagebox.showerror("Erro", str(e))

    def atualizar_tabela_lembretes(self):
        self.tree_lemb.delete(*self.tree_lemb.get_children())
        try:
            mes = int(self.combo_mes.get())
        except Exception:
            mes = datetime.date.today().month
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM lembretes_vencimento WHERE mes_referencia = ? ORDER BY vencimento", (mes,))
        for row in cursor.fetchall():
            self.tree_lemb.insert("", "end", values=(row["id"], row["vencimento"], row["descricao"], row["tipo"]))

    def pagar_conta(self):
        itens = self.tree_lemb.selection()
        if not itens:
            messagebox.showwarning("Aviso", "Selecione uma conta.")
            return
        sucesso = 0
        try:
            with self.conn:
                for item in itens:
                    dados = self.tree_lemb.item(item)["values"]
                    id_lembrete, vencimento, descricao = dados[0], dados[1], dados[2]
                    dialogo = ctk.CTkInputDialog(text=f"Valor pago para:\n{descricao}", title="Pagamento")
                    valor_raw = dialogo.get_input()
                    if not valor_raw:
                        continue
                    try:
                        valor = converter_valor(valor_raw)
                    except Exception:
                        messagebox.showerror("Erro", "Valor inválido.")
                        continue
                    data_pagamento = data_hoje()
                    # Lança no extrato
                    self.conn.execute("""
                        INSERT INTO transacoes (data, descricao, valor, tipo, categoria)
                        VALUES (?, ?, ?, ?, ?)
                    """, (data_pagamento, f"PAGTO: {descricao}", -abs(valor), TIPO_DESPESA, "Contas Fixas"))
                    # Salva histórico
                    self.conn.execute("""
                        INSERT INTO historico_pagamentos (descricao, vencimento, data_pagamento, valor)
                        VALUES (?, ?, ?, ?)
                    """, (descricao, vencimento, data_pagamento, valor))
                    # Remove do planejamento
                    self.conn.execute("DELETE FROM lembretes_vencimento WHERE id=?", (id_lembrete,))
                    sucesso += 1
            self.atualizar_tabela_lembretes()
            self.atualizar_tabela_fluxo()
            self.atualizar_tabela_historico()
            messagebox.showinfo("Sucesso", f"{sucesso} conta(s) transferida(s) para o Extrato.")
        except Exception:
            logger.exception("Erro ao pagar conta")
            messagebox.showerror("Erro", "Falha ao processar pagamento.")

    def excluir_lembrete(self):
        itens = self.tree_lemb.selection()
        if not itens:
            return
        confirmar = messagebox.askyesno("Confirmação", "Deseja excluir?")
        if not confirmar:
            return
        try:
            with self.conn:
                for item in itens:
                    item_id = self.tree_lemb.item(item)["values"][0]
                    self.conn.execute("DELETE FROM lembretes_vencimento WHERE id=?", (item_id,))
            self.atualizar_tabela_lembretes()
        except Exception:
            logger.exception("Erro ao excluir lembrete")
            messagebox.showerror("Erro", "Falha ao excluir lembrete.")

    # Aba Histórico
    def configurar_aba_historico(self):
        colunas = ("ID", "Descrição", "Vencimento", "Pagamento", "Valor")
        self.tree_hist = ttk.Treeview(self.tab_historico, columns=colunas, show="headings")
        for col in colunas:
            self.tree_hist.heading(col, text=col)
        self.tree_hist.column("ID", width=50, anchor="center")
        self.tree_hist.column("Descrição", width=520, anchor="w")
        self.tree_hist.column("Vencimento", width=120, anchor="center")
        self.tree_hist.column("Pagamento", width=120, anchor="center")
        self.tree_hist.column("Valor", width=140, anchor="e")
        self.tree_hist.pack(fill="both", expand=True, padx=10, pady=10)

    def atualizar_tabela_historico(self):
        self.tree_hist.delete(*self.tree_hist.get_children())
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM historico_pagamentos ORDER BY id DESC")
        for row in cursor.fetchall():
            self.tree_hist.insert("", "end", values=(row["id"], row["descricao"], row["vencimento"], row["data_pagamento"], moeda(row["valor"])))

    # PDF e Export
    def gerar_pdf_lembretes(self):
        try:
            mes = int(self.combo_mes.get())
        except Exception:
            mes = datetime.date.today().month
        caminho_pdf = DIRETORIO_APP / f"Planejamento_Mes_{mes}.pdf"
        pdf = canvas.Canvas(str(caminho_pdf), pagesize=A4)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(80, 800, f"PLANEJAMENTO FINANCEIRO - MÊS {mes}")
        pdf.setFont("Helvetica", 11)
        y = 760
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM lembretes_vencimento WHERE mes_referencia = ? ORDER BY vencimento", (mes,))
        for row in cursor.fetchall():
            texto = f"[{row['vencimento']}] {row['descricao']}"
            pdf.drawString(80, y, texto)
            y -= 22
            if y < 60:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = 800
        pdf.save()
        messagebox.showinfo("PDF Gerado", f"Arquivo salvo em:\n{caminho_pdf}")

    def exportar_transacoes_csv(self):
        try:
            caminho = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialdir=str(DIRETORIO_APP))
            if not caminho:
                return
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM transacoes ORDER BY id DESC")
            rows = cursor.fetchall()
            with open(caminho, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "data", "descricao", "valor", "tipo", "categoria"])
                for r in rows:
                    writer.writerow([r["id"], r["data"], r["descricao"], r["valor"], r["tipo"], r["categoria"]])
            messagebox.showinfo("Exportado", f"Transações exportadas para:\n{caminho}")
        except Exception:
            logger.exception("Erro ao exportar CSV")
            messagebox.showerror("Erro", "Falha ao exportar CSV.")

# Execução
if __name__ == "__main__":
    app = AppFinancas()
    app.mainloop()
