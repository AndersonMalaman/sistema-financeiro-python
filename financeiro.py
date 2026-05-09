# --- FUNÇÃO MESTRE DE MIGRAÇÃO (V13.1 - COM AVISOS) ---
    def alternar_status_e_migrar(self):
        items = self.tree_lemb.selection()
        
        # 1. Verifica se o usuário selecionou alguma conta
        if not items: 
            messagebox.showwarning("Aviso", "Por favor, selecione uma conta na tabela primeiro!")
            return
        
        cursor = self.conn.cursor()
        hoje = datetime.date.today().strftime("%d/%m/%Y")
        sucesso = 0

        for i in items:
            dados = self.tree_lemb.item(i)['values']
            id_l, venc, desc, tipo_l, status_atual = dados

            if "Pendente" in status_atual:
                # 2. Pergunta o valor real pago
                dialogo = ctk.CTkInputDialog(text=f"Qual o valor real pago para '{desc}'? (Ex: 150.50)", title="Confirmar Pagamento")
                valor_pago = dialogo.get_input()
                
                # 3. Se o usuário digitou um valor e clicou em OK
                if valor_pago:
                    try:
                        # Limpa o texto caso o usuário digite "R$" ou vírgula
                        valor_limpo = valor_pago.replace('R$', '').strip().replace(',', '.')
                        valor_num = float(valor_limpo)
                        
                        # Atualiza Lembrete para Pago
                        cursor.execute("UPDATE lembretes_vencimento SET status='Pago', data_pagamento=? WHERE id=?", (hoje, id_l))
                        
                        # Lança no Extrato Real como negativo (Despesa)
                        cursor.execute("INSERT INTO transacoes (data, descricao, valor, tipo, categoria) VALUES (?, ?, ?, ?, ?)", 
                                       (hoje, f"PAGTO: {desc}", -abs(valor_num), "Despesa", "Contas Fixas"))
                        sucesso += 1
                        
                    except Exception as e:
                        messagebox.showerror("Erro de Digitação", f"O valor '{valor_pago}' é inválido. Use apenas números!")
            else:
                # Se já estava pago e o usuário clicou de novo, volta para Pendente
                cursor.execute("UPDATE lembretes_vencimento SET status='Pendente', data_pagamento=NULL WHERE id=?", (id_l,))
                sucesso += 1

        self.conn.commit()
        self.atualizar_tabela_lembretes()
        self.atualizar_tabela_fluxo()
        
        if sucesso > 0:
            messagebox.showinfo("Sucesso", "Operação concluída e saldo do Extrato atualizado!")