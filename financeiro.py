# =========================================================
# GESTÃO FINANCEIRA PRO v13.4
# COMPLETO + TRANSFERÊNCIA AUTOMÁTICA
# Anderson Malaman
# =========================================================

import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import datetime
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# =========================================================
# CONFIGURAÇÕES
# =========================================================

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# =========================================================
# DIRETÓRIOS
# =========================================================

BASE_DIR = Path.home() / "OneDrive" / "Sistema"

DIRETORIO_DB = BASE_DIR / "DB"
DIRETORIO_APP = BASE_DIR / "Aplicacao"

CAMINHO_DB = DIRETORIO_DB / "financas_residenciais.db"

DIRETORIO_DB.mkdir(parents=True, exist_ok=True)
DIRETORIO_APP.mkdir(parents=True, exist_ok=True)

# =========================================================
# CONSTANTES
# =========================================================

TIPO_RECEITA = "Receita"
TIPO_DESPESA = "Despesa"
TIPO_INVESTIMENTO = "Investimento"

# =========================================================
# CATEGORIAS
# =========================================================

CATEGORIAS_RECEITA = [
    "Salário",
    "Dividendos",
    "Vendas",
    "Restituição",
    "Outras Receitas"
]

CATEGORIAS_DESPESA = [
    "Contas Fixas",
    "Alimentação",
    "Lazer",
    "Transporte",
    "Saúde",
    "Outros"
]

CATEGORIAS_INVESTIMENTO = [
    "Ações",
    "Fundos Imobiliários",
    "Tesouro Direto",
    "Criptomoedas",
    "Reserva Emergência"
]

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_hoje():
    return datetime.date.today().strftime("%d/%m/%Y")


def converter_valor(valor: str) -> float:

    if not valor:
        raise ValueError("Valor vazio")

    valor = (
        valor.upper()
        .replace("R$", "")
        .replace(" ", "")
        .replace(",", ".")
    )

    return float(valor)

# =========================================================
# BANCO DE DADOS
# =========================================================

def conectar_db():

    conn = sqlite3.connect(CAMINHO_DB)

    conn.row_factory = sqlite3.Row

    with conn:

        cursor = conn.cursor()

        # =================================================
        # TRANSAÇÕES
        # =================================================

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

        # =================================================
        # PLANEJAMENTO
        # =================================================

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

        # =================================================
        # HISTÓRICO
        # =================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_pagamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT,
                vencimento TEXT,
                data_pagamento TEXT,
                valor REAL
            )
        """)

    return conn

# =========================================================
# APP
# =========================================================

class AppFinancas(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title("Gestão Financeira PRO v13.4")
        self.geometry("1300x900")

        self.conn = conectar_db()

        self.configurar_estilo()

        self.criar_tabs()

        self.configurar_aba_fluxo()

        self.configurar_aba_lembretes()

        self.configurar_aba_historico()

        self.atualizar_tabela_fluxo()

        self.atualizar_tabela_lembretes()

        self.atualizar_tabela_historico()

    # =====================================================
    # ESTILO
    # =====================================================

    def configurar_estilo(self):

        style = ttk.Style()

        style.theme_use("default")

        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            rowheight=30,
            fieldbackground="#2b2b2b",
            borderwidth=0
        )

        style.map(
            "Treeview",
            background=[("selected", "#1f538d")]
        )

        style.configure(
            "Treeview.Heading",
            background="#1f538d",
            foreground="white",
            relief="flat",
            font=("Arial", 10, "bold")
        )

    # =====================================================
    # TABS
    # =====================================================

    def criar_tabs(self):

        self.tabview = ctk.CTkTabview(self)

        self.tabview.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )

        self.tab_fluxo = self.tabview.add(" Extrato de Caixa ")

        self.tab_lembretes = self.tabview.add(" Planejamento ")

        self.tab_historico = self.tabview.add(" Histórico ")

    # =====================================================
    # ABA EXTRATO
    # =====================================================

    def configurar_aba_fluxo(self):

        frame = ctk.CTkFrame(self.tab_fluxo)

        frame.pack(fill="x", padx=10, pady=10)

        # DATA

        ctk.CTkLabel(frame, text="Data").grid(row=0, column=0)

        self.ent_data_f = ctk.CTkEntry(frame, width=120)

        self.ent_data_f.insert(0, data_hoje())

        self.ent_data_f.grid(row=0, column=1, padx=5)

        # DESCRIÇÃO

        ctk.CTkLabel(frame, text="Descrição").grid(row=0, column=2)

        self.ent_desc_f = ctk.CTkEntry(frame, width=300)

        self.ent_desc_f.grid(row=0, column=3, padx=5)

        # VALOR

        ctk.CTkLabel(frame, text="Valor").grid(row=0, column=4)

        self.ent_valor_f = ctk.CTkEntry(frame, width=120)

        self.ent_valor_f.grid(row=0, column=5)

        # NATUREZA

        ctk.CTkLabel(frame, text="Natureza").grid(row=1, column=0)

        self.combo_tipo = ctk.CTkComboBox(
            frame,
            values=[
                TIPO_RECEITA,
                TIPO_DESPESA,
                TIPO_INVESTIMENTO
            ],
            command=self.atualizar_categorias
        )

        self.combo_tipo.set(TIPO_DESPESA)

        self.combo_tipo.grid(row=1, column=1, pady=10)

        # CATEGORIA

        ctk.CTkLabel(frame, text="Categoria").grid(row=1, column=2)

        self.combo_cat = ctk.CTkComboBox(
            frame,
            values=CATEGORIAS_DESPESA,
            width=300
        )

        self.combo_cat.set(CATEGORIAS_DESPESA[0])

        self.combo_cat.grid(row=1, column=3)

        # BOTÃO

        ctk.CTkButton(
            frame,
            text="💾 Salvar",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            command=self.salvar_fluxo
        ).grid(row=1, column=5)

        # TABELA

        colunas = (
            "ID",
            "Data",
            "Tipo",
            "Categoria",
            "Descrição",
            "Valor"
        )

        self.tree_fluxo = ttk.Treeview(
            self.tab_fluxo,
            columns=colunas,
            show="headings",
            selectmode="extended"
        )

        for col in colunas:
            self.tree_fluxo.heading(col, text=col)

        self.tree_fluxo.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # RESUMO

        resumo = ctk.CTkFrame(self.tab_fluxo)

        resumo.pack(fill="x", padx=10, pady=5)

        self.lbl_receitas = ctk.CTkLabel(
            resumo,
            text="Entradas: R$ 0,00",
            text_color="#2ecc71",
            font=("Arial", 14, "bold")
        )

        self.lbl_receitas.pack(side="left", padx=20)

        self.lbl_despesas = ctk.CTkLabel(
            resumo,
            text="Saídas: R$ 0,00",
            text_color="#e74c3c",
            font=("Arial", 14, "bold")
        )

        self.lbl_despesas.pack(side="left", padx=20)

        self.lbl_invest = ctk.CTkLabel(
            resumo,
            text="Investimentos: R$ 0,00",
            text_color="#3498db",
            font=("Arial", 14, "bold")
        )

        self.lbl_invest.pack(side="left", padx=20)

        self.lbl_saldo = ctk.CTkLabel(
            resumo,
            text="SALDO: R$ 0,00",
            font=("Arial", 16, "bold")
        )

        self.lbl_saldo.pack(side="right", padx=20)

        # BOTÕES

        barra = ctk.CTkFrame(
            self.tab_fluxo,
            fg_color="transparent"
        )

        barra.pack(fill="x", padx=10)

        ctk.CTkButton(
            barra,
            text="🗑️ Excluir",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self.excluir_fluxo
        ).pack(side="left")

    # =====================================================
    # CATEGORIAS
    # =====================================================

    def atualizar_categorias(self, escolha):

        if escolha == TIPO_RECEITA:

            self.combo_cat.configure(
                values=CATEGORIAS_RECEITA
            )

            self.combo_cat.set(
                CATEGORIAS_RECEITA[0]
            )

        elif escolha == TIPO_INVESTIMENTO:

            self.combo_cat.configure(
                values=CATEGORIAS_INVESTIMENTO
            )

            self.combo_cat.set(
                CATEGORIAS_INVESTIMENTO[0]
            )

        else:

            self.combo_cat.configure(
                values=CATEGORIAS_DESPESA
            )

            self.combo_cat.set(
                CATEGORIAS_DESPESA[0]
            )

    # =====================================================
    # SALVAR EXTRATO
    # =====================================================

    def salvar_fluxo(self):

        try:

            data = self.ent_data_f.get().strip()

            descricao = self.ent_desc_f.get().strip()

            tipo = self.combo_tipo.get()

            categoria = self.combo_cat.get()

            valor = converter_valor(
                self.ent_valor_f.get()
            )

            valor_db = (
                valor
                if tipo == TIPO_RECEITA
                else -abs(valor)
            )

            with self.conn:

                self.conn.execute("""
                    INSERT INTO transacoes
                    (
                        data,
                        descricao,
                        valor,
                        tipo,
                        categoria
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    data,
                    descricao,
                    valor_db,
                    tipo,
                    categoria
                ))

            self.ent_desc_f.delete(0, "end")

            self.ent_valor_f.delete(0, "end")

            self.atualizar_tabela_fluxo()

            messagebox.showinfo(
                "Sucesso",
                "Lançamento salvo."
            )

        except Exception as e:

            messagebox.showerror(
                "Erro",
                str(e)
            )

    # =====================================================
    # TABELA EXTRATO
    # =====================================================

    def atualizar_tabela_fluxo(self):

        self.tree_fluxo.delete(
            *self.tree_fluxo.get_children()
        )

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT *
            FROM transacoes
            ORDER BY id DESC
        """)

        total_receitas = 0
        total_despesas = 0
        total_invest = 0
        saldo = 0

        for row in cursor.fetchall():

            valor = row["valor"]

            self.tree_fluxo.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["data"],
                    row["tipo"],
                    row["categoria"],
                    row["descricao"],
                    moeda(abs(valor))
                )
            )

            if row["tipo"] == TIPO_RECEITA:

                total_receitas += abs(valor)

                saldo += abs(valor)

            elif row["tipo"] == TIPO_DESPESA:

                total_despesas += abs(valor)

                saldo -= abs(valor)

            else:

                total_invest += abs(valor)

                saldo -= abs(valor)

        self.lbl_receitas.configure(
            text=f"Entradas: {moeda(total_receitas)}"
        )

        self.lbl_despesas.configure(
            text=f"Saídas: {moeda(total_despesas)}"
        )

        self.lbl_invest.configure(
            text=f"Investimentos: {moeda(total_invest)}"
        )

        self.lbl_saldo.configure(
            text=f"SALDO: {moeda(saldo)}",
            text_color=(
                "#2ecc71"
                if saldo >= 0
                else "#e74c3c"
            )
        )

    # =====================================================
    # EXCLUIR EXTRATO
    # =====================================================

    def excluir_fluxo(self):

        itens = self.tree_fluxo.selection()

        if not itens:
            return

        confirmar = messagebox.askyesno(
            "Confirmação",
            "Deseja excluir os lançamentos?"
        )

        if not confirmar:
            return

        with self.conn:

            for item in itens:

                item_id = self.tree_fluxo.item(item)["values"][0]

                self.conn.execute("""
                    DELETE FROM transacoes
                    WHERE id=?
                """, (item_id,))

        self.atualizar_tabela_fluxo()

    # =====================================================
    # ABA PLANEJAMENTO
    # =====================================================

    def configurar_aba_lembretes(self):

        frame = ctk.CTkFrame(self.tab_lembretes)

        frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame, text="Vencimento").grid(row=0, column=0)

        self.ent_venc = ctk.CTkEntry(frame, width=120)

        self.ent_venc.insert(0, data_hoje())

        self.ent_venc.grid(row=0, column=1)

        ctk.CTkLabel(frame, text="Descrição").grid(row=0, column=2)

        self.ent_desc_l = ctk.CTkEntry(frame, width=300)

        self.ent_desc_l.grid(row=0, column=3, padx=5)

        self.tipo_var = ctk.StringVar(value="Esporádica")

        ctk.CTkRadioButton(
            frame,
            text="Mensal",
            variable=self.tipo_var,
            value="Mensal"
        ).grid(row=0, column=4)

        ctk.CTkRadioButton(
            frame,
            text="Esporádica",
            variable=self.tipo_var,
            value="Esporádica"
        ).grid(row=0, column=5)

        ctk.CTkButton(
            frame,
            text="🔔 Agendar",
            command=self.salvar_lembrete
        ).grid(row=0, column=6, padx=10)

        # FILTRO

        filtro = ctk.CTkFrame(
            self.tab_lembretes,
            fg_color="transparent"
        )

        filtro.pack(fill="x", padx=10)

        ctk.CTkLabel(
            filtro,
            text="Mês"
        ).pack(side="left")

        self.combo_mes = ctk.CTkComboBox(
            filtro,
            values=[str(i) for i in range(1, 13)],
            width=80
        )

        self.combo_mes.set(
            str(datetime.date.today().month)
        )

        self.combo_mes.pack(side="left", padx=5)

        ctk.CTkButton(
            filtro,
            text="🔍 Ver",
            command=self.atualizar_tabela_lembretes
        ).pack(side="left")

        # TABELA

        colunas = (
            "ID",
            "Vencimento",
            "Descrição",
            "Tipo"
        )

        self.tree_lemb = ttk.Treeview(
            self.tab_lembretes,
            columns=colunas,
            show="headings",
            selectmode="extended"
        )

        for col in colunas:
            self.tree_lemb.heading(col, text=col)

        self.tree_lemb.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # BOTÕES

        barra = ctk.CTkFrame(
            self.tab_lembretes,
            fg_color="transparent"
        )

        barra.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            barra,
            text="☑ Pagar Conta",
            fg_color="#27ae60",
            hover_color="#1e8449",
            command=self.pagar_conta
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            barra,
            text="🗑️ Excluir",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self.excluir_lembrete
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            barra,
            text="🖨️ PDF",
            fg_color="#8e44ad",
            command=self.gerar_pdf_lembretes
        ).pack(side="right", padx=5)

    # =====================================================
    # SALVAR LEMBRETE
    # =====================================================

    def salvar_lembrete(self):

        try:

            vencimento = self.ent_venc.get().strip()

            descricao = self.ent_desc_l.get().strip()

            tipo = self.tipo_var.get()

            data_obj = datetime.datetime.strptime(
                vencimento,
                "%d/%m/%Y"
            )

            with self.conn:

                if tipo == "Mensal":

                    for mes in range(data_obj.month, 13):

                        self.conn.execute("""
                            INSERT INTO lembretes_vencimento
                            (
                                vencimento,
                                descricao,
                                mes_referencia,
                                ano_referencia,
                                tipo
                            )
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            f"{data_obj.day:02d}/{mes:02d}/{data_obj.year}",
                            descricao,
                            mes,
                            data_obj.year,
                            tipo
                        ))

                else:

                    self.conn.execute("""
                        INSERT INTO lembretes_vencimento
                        (
                            vencimento,
                            descricao,
                            mes_referencia,
                            ano_referencia,
                            tipo
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        vencimento,
                        descricao,
                        data_obj.month,
                        data_obj.year,
                        tipo
                    ))

            self.ent_desc_l.delete(0, "end")

            self.atualizar_tabela_lembretes()

            messagebox.showinfo(
                "Sucesso",
                "Conta planejada."
            )

        except Exception as e:

            messagebox.showerror(
                "Erro",
                str(e)
            )

    # =====================================================
    # TABELA PLANEJAMENTO
    # =====================================================

    def atualizar_tabela_lembretes(self):

        self.tree_lemb.delete(
            *self.tree_lemb.get_children()
        )

        mes = self.combo_mes.get()

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT *
            FROM lembretes_vencimento
            WHERE mes_referencia = ?
            ORDER BY vencimento
        """, (mes,))

        for row in cursor.fetchall():

            self.tree_lemb.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["vencimento"],
                    row["descricao"],
                    row["tipo"]
                )
            )

    # =====================================================
    # PAGAR CONTA
    # =====================================================

    def pagar_conta(self):

        itens = self.tree_lemb.selection()

        if not itens:

            messagebox.showwarning(
                "Aviso",
                "Selecione uma conta."
            )

            return

        sucesso = 0

        with self.conn:

            for item in itens:

                dados = self.tree_lemb.item(item)["values"]

                id_lembrete = dados[0]
                vencimento = dados[1]
                descricao = dados[2]

                dialogo = ctk.CTkInputDialog(
                    text=f"Valor pago para:\n{descricao}",
                    title="Pagamento"
                )

                valor = dialogo.get_input()

                if not valor:
                    continue

                try:

                    valor = converter_valor(valor)

                except:

                    messagebox.showerror(
                        "Erro",
                        "Valor inválido."
                    )

                    continue

                data_pagamento = data_hoje()

                # =========================================
                # LANÇA NO EXTRATO
                # =========================================

                self.conn.execute("""
                    INSERT INTO transacoes
                    (
                        data,
                        descricao,
                        valor,
                        tipo,
                        categoria
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    data_pagamento,
                    f"PAGTO: {descricao}",
                    -abs(valor),
                    TIPO_DESPESA,
                    "Contas Fixas"
                ))

                # =========================================
                # SALVA HISTÓRICO
                # =========================================

                self.conn.execute("""
                    INSERT INTO historico_pagamentos
                    (
                        descricao,
                        vencimento,
                        data_pagamento,
                        valor
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    descricao,
                    vencimento,
                    data_pagamento,
                    valor
                ))

                # =========================================
                # REMOVE DO PLANEJAMENTO
                # =========================================

                self.conn.execute("""
                    DELETE FROM lembretes_vencimento
                    WHERE id=?
                """, (id_lembrete,))

                sucesso += 1

        self.atualizar_tabela_lembretes()

        self.atualizar_tabela_fluxo()

        self.atualizar_tabela_historico()

        messagebox.showinfo(
            "Sucesso",
            f"{sucesso} conta(s) transferida(s) para o Extrato."
        )

    # =====================================================
    # EXCLUIR LEMBRETE
    # =====================================================

    def excluir_lembrete(self):

        itens = self.tree_lemb.selection()

        if not itens:
            return

        confirmar = messagebox.askyesno(
            "Confirmação",
            "Deseja excluir?"
        )

        if not confirmar:
            return

        with self.conn:

            for item in itens:

                item_id = self.tree_lemb.item(item)["values"][0]

                self.conn.execute("""
                    DELETE FROM lembretes_vencimento
                    WHERE id=?
                """, (item_id,))

        self.atualizar_tabela_lembretes()

    # =====================================================
    # HISTÓRICO
    # =====================================================

    def configurar_aba_historico(self):

        colunas = (
            "ID",
            "Descrição",
            "Vencimento",
            "Pagamento",
            "Valor"
        )

        self.tree_hist = ttk.Treeview(
            self.tab_historico,
            columns=colunas,
            show="headings"
        )

        for col in colunas:
            self.tree_hist.heading(col, text=col)

        self.tree_hist.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

    # =====================================================
    # TABELA HISTÓRICO
    # =====================================================

    def atualizar_tabela_historico(self):

        self.tree_hist.delete(
            *self.tree_hist.get_children()
        )

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT *
            FROM historico_pagamentos
            ORDER BY id DESC
        """)

        for row in cursor.fetchall():

            self.tree_hist.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["descricao"],
                    row["vencimento"],
                    row["data_pagamento"],
                    moeda(row["valor"])
                )
            )

    # =====================================================
    # PDF
    # =====================================================

    def gerar_pdf_lembretes(self):

        mes = self.combo_mes.get()

        caminho_pdf = (
            DIRETORIO_APP /
            f"Planejamento_Mes_{mes}.pdf"
        )

        pdf = canvas.Canvas(
            str(caminho_pdf),
            pagesize=A4
        )

        pdf.setFont("Helvetica-Bold", 18)

        pdf.drawString(
            80,
            800,
            f"PLANEJAMENTO FINANCEIRO - MÊS {mes}"
        )

        pdf.setFont("Helvetica", 11)

        y = 760

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT *
            FROM lembretes_vencimento
            WHERE mes_referencia = ?
            ORDER BY vencimento
        """, (mes,))

        for row in cursor.fetchall():

            texto = (
                f"[{row['vencimento']}] "
                f"{row['descricao']}"
            )

            pdf.drawString(80, y, texto)

            y -= 25

            if y < 50:

                pdf.showPage()

                pdf.setFont("Helvetica", 11)

                y = 800

        pdf.save()

        messagebox.showinfo(
            "PDF Gerado",
            f"Arquivo salvo em:\n{caminho_pdf}"
        )

# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":

    app = AppFinancas()

    app.mainloop()