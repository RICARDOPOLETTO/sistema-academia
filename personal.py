import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
# Importa a biblioteca para conectar com planilhas Google (Streamlit nativo)
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Controle de Mensalidades & Agenda", layout="wide")

# Link da sua planilha do Google Sheets (Substitua pelo seu link real aqui dentro das aspas)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1NGUhDzszsu4gmooYNNCqnwtDY8y2vx9cs6Izwo0gMo4/edit?gid=889713852#gid=889713852"

# Conexão com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Erro ao conectar com o Google Drive. Certifique-se de configurar os acessos corretamente.")

# Funções para ler e salvar os dados no Google Drive
def ler_alunos():
    try:
        return conn.read(spreadsheet=URL_PLANILHA, worksheet="alunos", ttl="0")
    except:
        return pd.DataFrame(columns=["id", "nome", "telefone", "responsavel", "modalidade", "valor", "status"])

def ler_agendamentos():
    try:
        return conn.read(spreadsheet=URL_PLANILHA, worksheet="agendamentos", ttl="0")
    except:
        return pd.DataFrame(columns=["id", "aluno_id", "dia_semana", "horario"])

def salvar_dados(df_alunos, df_agendamentos):
    # Atualiza as duas abas no Google Sheets
    conn.update(spreadsheet=URL_PLANILHA, worksheet="alunos", data=df_alunos)
    conn.update(spreadsheet=URL_PLANILHA, worksheet="agendamentos", data=df_agendamentos)

# Configurações de horários e dias
def gerar_grade_horarios():
    horarios = []
    atual = datetime.strptime("05:30", "%H:%M")
    fim = datetime.strptime("19:00", "%H:%M")
    while atual <= fim:
        horarios.append(atual.strftime("%H:%M"))
        atual += timedelta(minutes=30)
    return horarios

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
HORARIOS_PERMITIDOS = gerar_grade_horarios()

st.title("🏊‍♂️ Sistema Avançado de Mensalidades e Agenda (Nuvem)")
st.markdown("---")

aba_cadastro, aba_agenda, aba_financeiro = st.tabs(["📝 Cadastro de Alunos", "📅 Agenda & Horários Vagos", "💰 Buscar, Editar & Pagamentos"])

# Carrega os dados direto da nuvem
df_alunos = ler_alunos()
df_agendamentos = ler_agendamentos()

# Garante que os IDs sejam tratados numericamente
if not df_alunos.empty:
    df_alunos["id"] = df_alunos["id"].astype(int)
if not df_agendamentos.empty:
    df_agendamentos["aluno_id"] = df_agendamentos["aluno_id"].astype(int)

# ==========================================
# ABA 1: CADASTRO DE ALUNOS
# ==========================================
with aba_cadastro:
    st.header("Cadastrar Novo Aluno e Agendamentos")
    
    with st.form(key="form_cadastro_avancado", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            nome = st.text_input("Nome do Aluno *")
            telefone = st.text_input("Telefone (Opcional)")
            responsavel = st.text_input("Nome do Responsável (Opcional)")
            modalidade = st.selectbox("Modalidade", ["NATAÇÃO", "HIDROGINÁSTICA", "PERSONAL"])
        
        with col_c2:
            valor = st.number_input("Valor da Mensalidade Total (R$)", min_value=0.0, value=200.0, step=10.0)
            status = st.selectbox("Status Inicial de Pagamento", ["Pendente", "Pago"])
            
            st.markdown("**Selecione os Dias e Horários das Aulas:**")
            dias_selecionados = st.multiselect("Dias da Semana", DIAS_SEMANA)
            horarios_selecionados = st.multiselect("Horários das Aulas", HORARIOS_PERMITIDOS)
            
        botao_salvar = st.form_submit_button("Salvar Cadastro Completo")
        
    if botao_salvar:
        if not nome:
            st.error("O nome do aluno é obrigatório!")
        elif not dias_selecionados or not horarios_selecionados:
            st.error("Por favor, selecione pelo menos um Dia e um Horário!")
        else:
            # Gerar novo ID do aluno
            novo_id = 1 if df_alunos.empty else int(df_alunos["id"].max() + 1)
            
            # Adicionar novo aluno
            novo_aluno = pd.DataFrame([{
                "id": novo_id, "nome": nome, "telefone": telefone, 
                "responsavel": responsavel, "modalidade": modalidade, 
                "valor": valor, "status": status
            }])
            df_alunos = pd.concat([df_alunos, novo_aluno], ignore_index=True)
            
            # Adicionar agendamentos
            novos_agendamentos = []
            id_agend = 1 if df_agendamentos.empty else int(df_agendamentos["id"].max() + 1)
            
            for dia in dias_selecionados:
                for hora in horarios_selecionados:
                    novos_agendamentos.append({
                        "id": id_agend, "aluno_id": novo_id, "dia_semana": dia, "horario": hora
                    })
                    id_agend += 1
            
            if novos_agendamentos:
                df_agendamentos = pd.concat([df_agendamentos, pd.DataFrame(novos_agendamentos)], ignore_index=True)
            
            salvar_dados(df_alunos, df_agendamentos)
            st.success(f"Aluno {nome} cadastrado com sucesso!")
            st.rerun()

# ==========================================
# ABA 2: AGENDA VISUAL & HORÁRIOS VAGOS
# ==========================================
with aba_agenda:
    st.header("Visualização da Grade Semanal")
    
    matriz_agenda = []
    for hora in HORARIOS_PERMITIDOS:
        linha = {"Horário": hora}
        for dia in DIAS_SEMANA:
            if not df_agendamentos.empty and not df_alunos.empty:
                filtro_ag = df_agendamentos[(df_agendamentos["dia_semana"] == dia) & (df_agendamentos["horario"] == hora)]
                filtro_cruzado = df_alunos[df_alunos["id"].isin(filtro_ag["aluno_id"])]
                
                if not filtro_cruzado.empty:
                    nomes = ", ".join(f"{r['nome']} ({r['modalidade']})" for _, r in filtro_cruzado.iterrows())
                    linha[dia] = nomes
                else:
                    linha[dia] = "🟢 VAGO"
            else:
                linha[dia] = "🟢 VAGO"
        matriz_agenda.append(linha)
        
    df_grade_final = pd.DataFrame(matriz_agenda)
    st.dataframe(df_grade_final.set_index("Horário"), use_container_width=True, height=600)

# ==========================================
# ABA 3: BUSCA, EDIÇÃO E PAGAMENTOS
# ==========================================
with aba_financeiro:
    st.header("Gerenciamento Financeiro e Cadastral")
    
    if not df_alunos.empty:
        # Faturamento KPIs
        col_f1, col_f2, col_f3 = st.columns(3)
        total_previsto = df_alunos["valor"].astype(float).sum()
        total_pago = df_alunos[df_alunos["status"] == "Pago"]["valor"].astype(float).sum()
        total_pendente = df_alunos[df_alunos["status"] == "Pendente"]["valor"].astype(float).sum()
        
        col_f1.metric("Faturamento Previsto", f"R$ {total_previsto:,.2f}")
        col_f2.metric("Total Recebido ✅", f"R$ {total_pago:,.2f}")
        col_f3.metric("Total Pendente ⏳", f"R$ {total_pendente:,.2f}")
        st.markdown("---")
        
        busca_nome = st.text_input("🔍 Buscar Aluno por Nome:")
        df_filtrado = df_alunos[df_alunos["nome"].str.contains(busca_nome, case=False, na=False)] if busca_nome else df_alunos
        
        if "aluno_editando_id" not in st.session_state:
            st.session_state.aluno_editando_id = None

        # FORMULÁRIO DE EDIÇÃO
        if st.session_state.aluno_editando_id is not None:
            id_edit = st.session_state.aluno_editando_id
            aluno_dados = df_alunos[df_alunos["id"] == id_edit].iloc[0]
            
            filtro_ag_atuais = df_agendamentos[df_agendamentos["aluno_id"] == id_edit]
            dias_atuais = list(filtro_ag_atuais["dia_semana"].unique()) if not filtro_ag_atuais.empty else []
            horas_atuais = list(filtro_ag_atuais["horario"].unique()) if not filtro_ag_atuais.empty else []
            
            st.markdown(f"### ✏️ Editando Cadastro de: **{aluno_dados['nome']}**")
            with st.form(key="form_edicao"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    novo_nome = st.text_input("Nome do Aluno", value=aluno_dados['nome'])
                    novo_tel = st.text_input("Telefone", value=str(aluno_dados['telefone']) if pd.notna(aluno_dados['telefone']) else "")
                    novo_resp = st.text_input("Responsável", value=str(aluno_dados['responsavel']) if pd.notna(aluno_dados['responsavel']) else "")
                    nova_mod = st.selectbox("Modalidade", ["NATAÇÃO", "HIDROGINÁSTICA", "PERSONAL"], index=["NATAÇÃO", "HIDROGINÁSTICA", "PERSONAL"].index(aluno_dados['modalidade']))
                with col_e2:
                    novo_val = st.number_input("Valor da Mensalidade (R$)", min_value=0.0, value=float(aluno_dados['valor']), step=10.0)
                    novo_status = st.selectbox("Status de Pagamento", ["Pendente", "Pago"], index=["Pendente", "Pago"].index(aluno_dados['status']))
                    novos_dias = st.multiselect("Alterar Dias", DIAS_SEMANA, default=dias_atuais)
                    novos_horarios = st.multiselect("Alterar Horários", HORARIOS_PERMITIDOS, default=horas_atuais)
                
                col_btn_ed1, col_btn_ed2 = st.columns(2)
                if col_btn_ed1.form_submit_button("💾 Salvar Alterações"):
                    if not novo_nome or not novos_dias or not novos_horarios:
                        st.error("Nome, Dias e Horários são obrigatórios!")
                    else:
                        # Atualiza aluno no DataFrame
                        df_alunos.loc[df_alunos["id"] == id_edit, ["nome", "telefone", "responsavel", "modalidade", "valor", "status"]] = [
                            novo_nome, novo_tel, novo_resp, nova_mod, novo_val, novo_status
                        ]
                        
                        # Remove agendamentos antigos
                        df_agendamentos = df_agendamentos[df_agendamentos["aluno_id"] != id_edit]
                        
                        # Insere novos agendamentos
                        id_agend = 1 if df_agendamentos.empty else int(df_agendamentos["id"].max() + 1)
                        novos_ag = []
                        for d in novos_dias:
                            for h in novos_horarios:
                                novos_ag.append({"id": id_agend, "aluno_id": id_edit, "dia_semana": d, "horario": h})
                                id_agend += 1
                        if novos_ag:
                            df_agendamentos = pd.concat([df_agendamentos, pd.DataFrame(novos_ag)], ignore_index=True)
                        
                        salvar_dados(df_alunos, df_agendamentos)
                        st.success("Cadastro atualizado com sucesso!")
                        st.session_state.aluno_editando_id = None
                        st.rerun()
                        
                if col_btn_ed2.form_submit_button("❌ Cancelar Edição"):
                    st.session_state.aluno_editando_id = None
                    st.rerun()
            st.markdown("---")

        # LISTAGEM
        for _, aluno in df_filtrado.iterrows():
            with st.container():
                col_a, col_b, col_c, col_d = st.columns([2, 1, 1, 1.2])
                
                with col_a:
                    st.markdown(f"### **{aluno['nome']}**")
                    st.caption(f"Modalidade: {aluno['modalidade']} | Resp: {aluno['responsavel'] if pd.notna(aluno['responsavel']) else 'Próprio'}")
                
                with col_b:
                    st.markdown(f"**Telefone:**\n{aluno['telefone'] if pd.notna(aluno['telefone']) else 'Não informado'}")
                
                with col_c:
                    cor_status = "green" if aluno['status'] == "Pago" else "red"
                    st.markdown(f"**Mensalidade:** R$ {float(aluno['valor']):.2f}")
                    st.markdown(f"Status: :{cor_status}[**{aluno['status']}**]")
                
                with col_d:
                    novo_status_click = "Pendente" if aluno['status'] == "Pago" else "Pago"
                    if st.button(f"Marcar como {novo_status_click}", key=f"btn_pay_{aluno['id']}"):
                        df_alunos.loc[df_alunos["id"] == aluno['id'], "status"] = novo_status_click
                        salvar_dados(df_alunos, df_agendamentos)
                        st.rerun()
                    
                    if st.button("✏️ Editar Cadastro", key=f"btn_edit_{aluno['id']}"):
                        st.session_state.aluno_editando_id = int(aluno['id'])
                        st.rerun()
                        
                    if st.button("❌ Excluir Aluno", key=f"btn_del_{aluno['id']}"):
                        df_alunos = df_alunos[df_alunos["id"] != aluno['id']]
                        df_agendamentos = df_agendamentos[df_agendamentos["aluno_id"] != aluno['id']]
                        salvar_dados(df_alunos, df_agendamentos)
                        st.warning(f"Aluno removido.")
                        st.rerun()
                st.markdown("---")
    else:
        st.info("Nenhum aluno cadastrado no sistema ainda.")
