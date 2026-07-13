#!/usr/bin/env python
# coding: utf-8

# In[103]:


import requests
import pandas as pd
import matplotlib.pyplot as plt
import time
from datetime import datetime

PORTA_ALVO = 5202 
TEMPO_COLETA_SEGUNDOS = 30
URL_API = "http://localhost:8080/api/json"

historico_dados = []

print(f"📡 Iniciando captura completa na porta {PORTA_ALVO} por {TEMPO_COLETA_SEGUNDOS} segundos...")
print("⚠️ Dispare o iperf3 em outro terminal AGORA: iperf3 -c SEU_IP_REAL -p 5202 -t 30 -4")

for i in range(TEMPO_COLETA_SEGUNDOS):
    try:
        resposta = requests.get(URL_API)
        if resposta.status_code == 200:
            pacote = resposta.json()
            timestamp_atual = pacote.get("timestamp")

            for elemento in pacote.get("dados", []):
                formatado = elemento.get("formatted")

                if formatado:
                    src_port = formatado["key"].get("src_port", 0)
                    dst_port = formatado["key"].get("dst_port", 0)

                    # Lendo TUDO (Os 100%)
                    val = formatado["value"]
                    cwnd = val.get("snd_cwnd", 0)
                    state = val.get("ca_state", 0)

                    if (src_port == PORTA_ALVO or dst_port == PORTA_ALVO) and cwnd > 0:
                        historico_dados.append({
                            "tempo": datetime.fromisoformat(timestamp_atual),
                            "porta_origem": src_port,
                            "porta_destino": dst_port,
                            "cwnd": cwnd,
                            "srtt": val.get("srtt", 0),
                            "retrans": val.get("retransmissions", 0),
                            "ssthresh": val.get("ssthresh", 0) if val.get("ssthresh", 0) < 2000000000 else None,
                            "packets_out": val.get("packets_out", 0),
                            "ca_name": val.get("ca_name", "desconhecido"),
                            "ca_state": val.get("ca_state") # Guardando o estado!
                        })
    except Exception as e:
        pass
    time.sleep(1)

print("✅ Captura concluída! Rode a Célula 2.")


# In[100]:


# Rode isso na sua célula de análise RENO
df_reno = pd.DataFrame(historico_dados)
df_reno.to_csv("dados_reno.csv", index=False)
print("✅ Dados RENO salvos em dados_reno.csv")


# In[105]:


# Rode isso na sua célula de análise CUBIC
df_cubic = pd.DataFrame(historico_dados)
df_cubic.to_csv("dados_cubic.csv", index=False)
print("✅ Dados CUBIC salvos em dados_cubic.csv")


# In[104]:


import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

df = pd.DataFrame(historico_dados)

if not df.empty:
    # 🌟 CONVERSÃO: Transformando SRTT (µs) em RTT (ms) para a exigência do professor
    df['rtt_ms'] = df['srtt'] / 1000.0

    df.sort_values(by='tempo', inplace=True)
    grupos = df.groupby(['porta_origem', 'porta_destino'])

    # Criar um painel com 3 gráficos empilhados
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15))
    fig.suptitle(f"Análise TCP (Visão Limpa) - Porta {PORTA_ALVO}", fontsize=18, fontweight='bold')

    linhas_validas = 0
    cores = plt.cm.tab10.colors

    for idx, ((src, dst), grupo) in enumerate(grupos):

        # 🧹 O FILTRO MÁGICO: Só desenha se a Janela de Congestionamento variou!
        if grupo['cwnd'].max() > grupo['cwnd'].min(): 

            cor = cores[linhas_validas % len(cores)] 

            algoritmo = grupo['ca_name'].mode()[0] if 'ca_name' in grupo.columns else "N/A"
            label_conn = f"{src}->{dst} [{algoritmo.upper()}]"

            # Gráfico 1: Janela de Congestionamento (Cwnd) e Packets Out
            ax1.plot(grupo['tempo'], grupo['cwnd'], marker='o', markersize=6, linewidth=2.5, color=cor, label=f"Cwnd ({label_conn})")

            if 'packets_out' in grupo.columns:
                ax1.plot(grupo['tempo'], grupo['packets_out'], linestyle='--', linewidth=2, color=cor, alpha=0.7, label=f"Packets Out ({label_conn})")

            # Gráfico 2: RTT (AGORA EM MILISSEGUNDOS)
            ax2.plot(grupo['tempo'], grupo['rtt_ms'], marker='s', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"RTT ({label_conn})")

            # Gráfico 3: Retransmissões Acumuladas
            ax3.plot(grupo['tempo'], grupo['retrans'], marker='^', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"Retransmissões ({label_conn})")

            linhas_validas += 1

    if linhas_validas > 0:
        # Define os Títulos dos Eixos Y
        ax1.set_ylabel("Pacotes", fontsize=13, fontweight='bold')
        ax2.set_ylabel("RTT (ms)", fontsize=13, fontweight='bold')
        ax3.set_ylabel("Retransmissões", fontsize=13, fontweight='bold')

        # Aplica a formatação de Grid, Legenda e Eixo X (Tempo)
        for ax in [ax1, ax2, ax3]:
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
            ax.set_xlabel("Tempo da Captura", fontsize=13, fontweight='bold')
            ax.tick_params(axis='x', labelrotation=45)

        plt.tight_layout()

        # 💾 SALVAMENTO AUTOMÁTICO
        nome_arquivo = f"Grafico_TCP_Limpo_RTTms_{datetime.now().strftime('%H%M%S')}.png"
        plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico limpo salvo com sucesso: {nome_arquivo}")

        # Mostra os Gráficos
        plt.show()

        print("\n📊 ESTATÍSTICAS DOS FLUXOS ATIVOS (Com RTT em ms):")
        colunas_stats = ['cwnd', 'rtt_ms', 'retrans']
        if 'packets_out' in df.columns: colunas_stats.append('packets_out')

        df_limpo = df.groupby(['porta_origem', 'porta_destino']).filter(lambda x: x['cwnd'].max() > x['cwnd'].min())
        print(df_limpo[colunas_stats].describe().round(2))

    else:
        print("⚠️ A captura só possui conexões inativas (linhas retas). Tente rodar o iperf3 novamente.")
else:
    print(f"❌ Nenhum tráfego detectado.")


# In[102]:


# CÉLULA: Gráfico Comparativo Acadêmico (CUBIC vs RENO)
import pandas as pd
import matplotlib.pyplot as plt
import os

# Carrega os dados (certifique-se que os CSVs estão na mesma pasta)
df_cubic = pd.read_csv("dados_cubic.csv")
df_reno = pd.read_csv("dados_reno.csv")

# Converter SRTT de microssegundos (us) para milissegundos (ms) para o gráfico
df_cubic['srtt_ms'] = df_cubic['srtt'] / 1000.0
df_reno['srtt_ms'] = df_reno['srtt'] / 1000.0

# Define o tamanho da janela para a Média Móvel (suavização)
WINDOW = 15 

# Médias Móveis - Janela de Congestionamento (Cwnd)
df_cubic['cwnd_ma'] = df_cubic['cwnd'].rolling(window=WINDOW, min_periods=1).mean()
df_reno['cwnd_ma'] = df_reno['cwnd'].rolling(window=WINDOW, min_periods=1).mean()

# Médias Móveis - Latência (RTT)
df_cubic['srtt_ma'] = df_cubic['srtt_ms'].rolling(window=WINDOW, min_periods=1).mean()
df_reno['srtt_ma'] = df_reno['srtt_ms'].rolling(window=WINDOW, min_periods=1).mean()

# Configuração do Estilo Acadêmico
plt.style.use('default')
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 14))
fig.suptitle("Análise Comparativa de Controle de Congestionamento: TCP CUBIC vs TCP RENO", fontsize=18, fontweight='bold')

# Cores e Estilos de Linha (Alto Contraste para Impressão)
# CUBIC: Azul Escuro, Linha Sólida (Padrão)
# RENO: Vermelho Escuro, Linha Tracejada
COLOR_CUBIC = '#003366' 
COLOR_RENO = '#B22222'

# --- 1. GRÁFICO DE JANELA DE CONGESTIONAMENTO (Cwnd) ---
# Dados brutos no fundo (translúcidos)
ax1.plot(df_cubic['cwnd'], drawstyle='steps-post', color=COLOR_CUBIC, alpha=0.2, linewidth=1, linestyle='-')
ax1.plot(df_reno['cwnd'], drawstyle='steps-post', color=COLOR_RENO, alpha=0.2, linewidth=1, linestyle='-')

# Médias Móveis destacadas
ax1.plot(df_cubic['cwnd_ma'], color=COLOR_CUBIC, alpha=1.0, linewidth=2.5, linestyle='-', label=f'CUBIC (Média)')
ax1.plot(df_reno['cwnd_ma'], color=COLOR_RENO, alpha=1.0, linewidth=2.5, linestyle='--', label=f'RENO (Média)')

ax1.set_ylabel("Cwnd (Pacotes)", fontsize=12, fontweight='bold')
ax1.legend(loc='upper left', framealpha=0.9)
ax1.grid(True, linestyle=':', alpha=0.7)

# --- 2. GRÁFICO DE LATÊNCIA (RTT) ---
# Dados brutos no fundo
ax2.plot(df_cubic['srtt_ms'], color=COLOR_CUBIC, alpha=0.2, linewidth=1, linestyle='-')
ax2.plot(df_reno['srtt_ms'], color=COLOR_RENO, alpha=0.2, linewidth=1, linestyle='-')

# Médias Móveis destacadas
ax2.plot(df_cubic['srtt_ma'], color=COLOR_CUBIC, alpha=1.0, linewidth=2.5, linestyle='-', label='CUBIC (Média)')
ax2.plot(df_reno['srtt_ma'], color=COLOR_RENO, alpha=1.0, linewidth=2.5, linestyle='--', label='RENO (Média)')

ax2.set_ylabel("RTT (ms)", fontsize=12, fontweight='bold')
ax2.legend(loc='upper left', framealpha=0.9)
ax2.grid(True, linestyle=':', alpha=0.7)

# --- 3. GRÁFICO DE RETRANSMISSÕES ---
# Retransmissões (Usamos step-post para mostrar saltos discretos)
ax3.plot(df_cubic['retrans'], drawstyle='steps-post', color=COLOR_CUBIC, linewidth=2, linestyle='-', label='CUBIC')
ax3.plot(df_reno['retrans'], drawstyle='steps-post', color=COLOR_RENO, linewidth=2, linestyle='--', label='RENO')

ax3.set_ylabel("Retransmissões", fontsize=12, fontweight='bold')
ax3.set_xlabel("Amostras de Tempo", fontsize=12, fontweight='bold')
ax3.legend(loc='upper left', framealpha=0.9)
ax3.grid(True, linestyle=':', alpha=0.7)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])

# --- 💾 SALVAMENTO NO SUBDIRETÓRIO ---
# Garante que a pasta 'Graficos4' exista
os.makedirs("Graficos4", exist_ok=True)
# nome_arquivo = f"Grafico_TCP_Limpo_RTTms_{datetime.now().strftime('%H%M%S')}.png"
caminho_arquivo = os.path.join("Graficos4", "Comparativo_Academico_Final.png")

plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight')
plt.show()

# --- 📊 ESTATÍSTICAS COMPARATIVAS LEGÍVEIS ---
print("\n" + "="*60)
print("📊 ESTATÍSTICAS COMPARATIVAS: CUBIC vs RENO")
print("="*60)

print("\n🔵 TCP CUBIC:")
print(f" - Janela (Cwnd) Média:   {df_cubic['cwnd'].mean():.2f} pacotes")
print(f" - Janela (Cwnd) Máxima:  {df_cubic['cwnd'].max():.2f} pacotes")
print(f" - RTT Médio:             {df_cubic['srtt_ms'].mean():.2f} ms")
print(f" - Pico de RTT:           {df_cubic['srtt_ms'].max():.2f} ms")
print(f" - Total Retransmissões:  {df_cubic['retrans'].max():.0f}")

print("\n🔴 TCP RENO:")
print(f" - Janela (Cwnd) Média:   {df_reno['cwnd'].mean():.2f} pacotes")
print(f" - Janela (Cwnd) Máxima:  {df_reno['cwnd'].max():.2f} pacotes")
print(f" - RTT Médio:             {df_reno['srtt_ms'].mean():.2f} ms")
print(f" - Pico de RTT:           {df_reno['srtt_ms'].max():.2f} ms")
print(f" - Total Retransmissões:  {df_reno['retrans'].max():.0f}")

print("\n" + "="*60)
print(f"✅ Gráfico comparativo salvo com sucesso em: {caminho_arquivo}")


# In[ ]:


# CÉLULA BÔNUS: Sistema de Alerta Automático de Congestionamento
import pandas as pd

df = pd.DataFrame(historico_dados)

if not df.empty:
    df.sort_values(by='tempo', inplace=True)
    grupos = df.groupby(['porta_origem', 'porta_destino'])

    alertas_encontrados = 0
    print("🚨 SISTEMA DE DETECÇÃO AUTOMÁTICA DE CONGESTIONAMENTO 🚨")
    print("="*65)

    for (src, dst), grupo in grupos:
        # Ignora conexões vazias/inativas
        if grupo['cwnd'].max() == grupo['cwnd'].min():
            continue

        # O "shift(1)" pega o valor da amostra exata do milissegundo anterior
        cwnd_anterior = grupo['cwnd'].shift(1)
        retrans_anterior = grupo['retrans'].shift(1)

        # REGRA DO DESAFIO EXTRA:
        # 1. Cwnd reduziu 50% ou mais (cwnd atual <= 50% do cwnd anterior)
        # 2. Retransmissões aumentaram (retrans atual > retrans anterior)
        condicao_queda_cwnd = grupo['cwnd'] <= (0.5 * cwnd_anterior)
        condicao_aumento_retrans = grupo['retrans'] > retrans_anterior

        # Filtra a tabela para achar os momentos exatos onde a regra foi ativada
        eventos = grupo[condicao_queda_cwnd & condicao_aumento_retrans]

        for index, evento in eventos.iterrows():
            alertas_encontrados += 1
            tempo_fmt = evento['tempo'].strftime('%H:%M:%S.%f')[:-3]
            c_ant = cwnd_anterior.loc[index]
            c_atual = evento['cwnd']
            queda_pct = (1 - (c_atual / c_ant)) * 100

            print(f"⚠️ [ALERTA] Congestionamento Crítico Detectado!")
            print(f"   ⏰ Tempo: {tempo_fmt} | Fluxo: {src} -> {dst}")
            print(f"   📉 Cwnd caiu de {c_ant:.0f} para {c_atual:.0f} pacotes (Redução de {queda_pct:.1f}%)")
            print(f"   📈 Retransmissões subiram para: {evento['retrans']:.0f}")
            print("-" * 65)

    if alertas_encontrados == 0:
        print("✅ Nenhum evento de congestionamento crítico (queda >= 50%) foi detectado.")
        print("   (Lembrete: O CUBIC reduz a janela em 30%. Teste com o TCP RENO + 1% de perda para forçar este alerta!)")
else:
    print("❌ Nenhum dado encontrado na captura.")


# In[74]:


df = pd.DataFrame(historico_dados)

if not df.empty:
    df.sort_values(by='tempo', inplace=True)
    grupos = df.groupby(['porta_origem', 'porta_destino'])

    # Criar um painel com 3 gráficos empilhados
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15))
    fig.suptitle(f"Análise TCP (Visão Limpa) - Porta {PORTA_ALVO}", fontsize=18, fontweight='bold')

    linhas_validas = 0
    cores = plt.cm.tab10.colors

    for idx, ((src, dst), grupo) in enumerate(grupos):

        # O FILTRO: Só desenha se a Janela de Congestionamento variou!
        # Se max == min, significa que é uma conexão fantasma parada.
        if grupo['cwnd'].max() > grupo['cwnd'].min(): 

            # Usamos linhas_validas para as cores ficarem sequenciais e não pularem
            cor = cores[linhas_validas % len(cores)] 

            # Tenta pegar o nome do Algoritmo se ele existir na captura
            algoritmo = grupo['ca_name'].mode()[0] if 'ca_name' in grupo.columns else "N/A"
            label_conn = f"{src}->{dst} [{algoritmo.upper()}]"

            # Gráfico 1: Janela de Congestionamento (Cwnd) e Packets Out
            ax1.plot(grupo['tempo'], grupo['cwnd'], marker='o', markersize=6, linewidth=2.5, color=cor, label=f"Cwnd ({label_conn})")

            if 'packets_out' in grupo.columns:
                ax1.plot(grupo['tempo'], grupo['packets_out'], linestyle='--', linewidth=2, color=cor, alpha=0.7, label=f"Packets Out ({label_conn})")

            # Gráfico 2: RTT (Round Trip Time)
            ax2.plot(grupo['tempo'], grupo['srtt'], marker='s', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"SRTT us ({label_conn})")

            # Gráfico 3: Retransmissões Acumuladas
            ax3.plot(grupo['tempo'], grupo['retrans'], marker='^', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"Retransmissões ({label_conn})")

            linhas_validas += 1

    if linhas_validas > 0:
        # Define os Títulos dos Eixos Y
        ax1.set_ylabel("Pacotes", fontsize=13, fontweight='bold')
        ax2.set_ylabel("SRTT (µs)", fontsize=13, fontweight='bold')
        ax3.set_ylabel("Retransmissões", fontsize=13, fontweight='bold')

        # Aplica a formatação de Grid, Legenda e Eixo X (Tempo)
        for ax in [ax1, ax2, ax3]:
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
            ax.set_xlabel("Tempo da Captura", fontsize=13, fontweight='bold')
            ax.tick_params(axis='x', labelrotation=45)

        plt.tight_layout()

        # 💾 Salva com um nome diferente para você ter as duas versões!
        nome_arquivo = f"Grafico_TCP_Limpo_{datetime.now().strftime('%H%M%S')}.png"
        plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico limpo salvo com sucesso: {nome_arquivo}")

        # Mostra os Gráficos
        plt.show()

        print("\n📊 ESTATÍSTICAS DOS FLUXOS ATIVOS:")
        colunas_stats = ['cwnd', 'srtt', 'retrans']
        if 'packets_out' in df.columns: colunas_stats.append('packets_out')
        # Mostra estatísticas apenas dos grupos que passaram no filtro
        df_limpo = df.groupby(['porta_origem', 'porta_destino']).filter(lambda x: x['cwnd'].max() > x['cwnd'].min())
        print(df_limpo[colunas_stats].describe().round(2))

    else:
        print("⚠️ A captura só possui conexões inativas (linhas retas). Tente rodar o iperf3 novamente.")
else:
    print(f"❌ Nenhum tráfego detectado.")


# In[56]:


df = pd.DataFrame(historico_dados)

if not df.empty:
    df.sort_values(by='tempo', inplace=True)
    grupos = df.groupby(['porta_origem', 'porta_destino'])

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15))
    fig.suptitle(f"Análise TCP RENO (Visão Limpa) - Porta {PORTA_ALVO}", fontsize=18, fontweight='bold', color='darkred')

    linhas_validas = 0
    cores = plt.cm.tab10.colors

    for idx, ((src, dst), grupo) in enumerate(grupos):
        # 1º Filtro: Apenas conexões com variação (remove fantasmas)
        if grupo['cwnd'].max() > grupo['cwnd'].min(): 

            algoritmo = grupo['ca_name'].mode()[0] if 'ca_name' in grupo.columns else "N/A"

            # 2º Filtro: Desenha APENAS se for RENO
            if algoritmo.lower() == 'reno':
                cor = cores[linhas_validas % len(cores)] 
                label_conn = f"{src}->{dst} [RENO]"

                ax1.plot(grupo['tempo'], grupo['cwnd'], marker='o', markersize=6, linewidth=2.5, color=cor, label=f"Cwnd ({label_conn})")
                if 'packets_out' in grupo.columns:
                    ax1.plot(grupo['tempo'], grupo['packets_out'], linestyle='--', linewidth=2, color=cor, alpha=0.7, label=f"Packets Out ({label_conn})")

                ax2.plot(grupo['tempo'], grupo['srtt'], marker='s', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"SRTT us ({label_conn})")
                ax3.plot(grupo['tempo'], grupo['retrans'], marker='^', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"Retransmissões ({label_conn})")
                linhas_validas += 1

    if linhas_validas > 0:
        ax1.set_ylabel("Pacotes", fontsize=13, fontweight='bold')
        ax2.set_ylabel("SRTT (µs)", fontsize=13, fontweight='bold')
        ax3.set_ylabel("Retransmissões", fontsize=13, fontweight='bold')

        for ax in [ax1, ax2, ax3]:
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
            ax.set_xlabel("Tempo da Captura", fontsize=13, fontweight='bold')
            ax.tick_params(axis='x', labelrotation=45)

        plt.tight_layout()
        nome_arquivo = f"Grafico_TCP_RENO_{datetime.now().strftime('%H%M%S')}.png"
        plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico RENO salvo com sucesso: {nome_arquivo}")
        plt.show()
    else:
        print("⚠️ Nenhum fluxo RENO ativo encontrado nesta captura.")
else:
    print(f"❌ Nenhum tráfego detectado.")


# In[57]:


df = pd.DataFrame(historico_dados)

if not df.empty:
    df.sort_values(by='tempo', inplace=True)
    grupos = df.groupby(['porta_origem', 'porta_destino'])

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15))
    fig.suptitle(f"Análise 100% TCP - Porta {PORTA_ALVO}", fontsize=18, fontweight='bold')

    linhas_validas = 0
    cores = plt.cm.tab10.colors

    for idx, ((src, dst), grupo) in enumerate(grupos):
        if grupo['cwnd'].max() >= 10:  # Filtro corrigido (sem o nunique)
            cor = cores[idx % len(cores)]

            # Pega o nome do Algoritmo (Reno, Cubic, etc)
            algoritmo = grupo['ca_name'].mode()[0] if not grupo['ca_name'].empty else "N/A"
            label_conn = f"{src}->{dst} [{algoritmo.upper()}]"

            # Gráfico 1: Cwnd e Packets Out
            ax1.plot(grupo['tempo'], grupo['cwnd'], marker='o', markersize=5, linewidth=2.5, color=cor, label=f"Cwnd ({label_conn})")
            ax1.plot(grupo['tempo'], grupo['packets_out'], linestyle='--', linewidth=2, color=cor, alpha=0.7, label=f"Packets Out ({label_conn})")

            ax2.plot(grupo['tempo'], grupo['srtt'], marker='s', markersize=5, linewidth=2.5, color=cor, label=f"SRTT us ({label_conn})")
            ax3.plot(grupo['tempo'], grupo['retrans'], marker='^', markersize=5, linewidth=2.5, color=cor, label=f"Retrans ({label_conn})")

            linhas_validas += 1

    if linhas_validas > 0:
        ax1.set_ylabel("Pacotes", fontsize=13, fontweight='bold')
        ax2.set_ylabel("SRTT (µs)", fontsize=13, fontweight='bold')
        ax3.set_ylabel("Retransmissões", fontsize=13, fontweight='bold')

        for ax in [ax1, ax2, ax3]:
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
            ax.set_xlabel("Tempo da Captura", fontsize=13, fontweight='bold')
            ax.tick_params(axis='x', labelrotation=45)

        plt.tight_layout()
        nome_arquivo = f"Grafico_TCP_{datetime.now().strftime('%H%M%S')}.png"
        plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico salvo: {nome_arquivo}")
        plt.show()

        print("\n📊 ESTATÍSTICAS DOS ALGORITMOS:")
        print(df[['cwnd', 'packets_out', 'srtt', 'retrans', 'ca_name']].describe(include='all').round(2))
    else:
        print("⚠️ Sem fluxos ativos.")
else:
    print(f"❌ Nenhum tráfego detectado.")


# In[58]:


df = pd.DataFrame(historico_dados)

if not df.empty:
    df.sort_values(by='tempo', inplace=True)
    grupos = df.groupby(['porta_origem', 'porta_destino'])

    # Dicionário de Tradução do Linux (O que o professor pediu no Bônus)
    dicionario_estado = {
        0: '0 - Open (Normal)', 
        1: '1 - Disorder (Alerta)', 
        2: '2 - CWR (Redução)', 
        3: '3 - Recovery (Recuperação)', 
        4: '4 - Loss (Perda Total)'
    }

    # Criar uma nova coluna no DataFrame com os nomes traduzidos
    df['nome_estado'] = df['ca_state'].map(dicionario_estado)

    fig, ax = plt.subplots(figsize=(14, 4))
    fig.suptitle(f"Máquina de Estados de Congestionamento (icsk_ca_state)", fontsize=16, fontweight='bold', color='purple')

    linhas_validas = 0
    cores = plt.cm.tab10.colors

    for idx, ((src, dst), grupo) in enumerate(grupos):
        # Filtramos apenas o tráfego real do iperf (cwnd > 10 e variou)
        if grupo['cwnd'].max() >= 10 and grupo['cwnd'].max() > grupo['cwnd'].min(): 
            cor = cores[linhas_validas % len(cores)]
            label_conn = f"{src} -> {dst}"

            # Gráfico de Degraus (Step) é ideal para mostrar mudanças de estado
            ax.step(grupo['tempo'], grupo['nome_estado'], where='post', marker='o', linewidth=2.5, color=cor, label=label_conn)
            linhas_validas += 1

    if linhas_validas > 0:
        ax.set_ylabel("Estado TCP", fontsize=13, fontweight='bold')
        ax.set_xlabel("Tempo da Captura", fontsize=13, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))

        # Ordenar o eixo Y para fazer sentido (Open no topo, Loss no fundo)
        ordem_y = ['0 - Open (Normal)', '1 - Disorder (Alerta)', '2 - CWR (Redução)', '3 - Recovery (Recuperação)', '4 - Loss (Perda Total)']
        # Filtra a ordem apenas para os estados que realmente apareceram + o Open
        estados_presentes = df['nome_estado'].dropna().unique().tolist()
        estados_y = [est for est in ordem_y if est in estados_presentes or est == '0 - Open (Normal)']
        ax.set_yticks(estados_y)
        ax.set_yticklabels(estados_y)

        plt.xticks(rotation=45)
        plt.tight_layout()

        # Salva o gráfico do Bônus!
        nome_arquivo = f"Grafico_TCP_Estados_{datetime.now().strftime('%H%M%S')}.png"
        plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
        plt.show()

        # Resumo Estatístico do Bônus
        print("\n📊 ESTATÍSTICA DE ESTADOS (BÔNUS PARTE 2):")
        resumo_estados = df['nome_estado'].value_counts().reset_index()
        resumo_estados.columns = ['Estado de Congestionamento', 'Frequência (Msgs capturadas)']
        print(resumo_estados.to_string(index=False))
        print(f"✅ Gráfico salvo com sucesso: {nome_arquivo}")
    else:
        print("⚠️ Sem fluxos ativos. Rode o iperf3.")
else:
    print(f"❌ Nenhum tráfego detectado.")


# In[55]:


df = pd.DataFrame(historico_dados)

if not df.empty:
    df.sort_values(by='tempo', inplace=True)
    grupos = df.groupby(['porta_origem', 'porta_destino'])

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 15))
    fig.suptitle(f"Análise TCP CUBIC (Visão Limpa) - Porta {PORTA_ALVO}", fontsize=18, fontweight='bold', color='darkblue')

    linhas_validas = 0
    cores = plt.cm.tab10.colors

    for idx, ((src, dst), grupo) in enumerate(grupos):
        # 1º Filtro: Apenas conexões com variação (remove fantasmas)
        if grupo['cwnd'].max() > grupo['cwnd'].min(): 

            algoritmo = grupo['ca_name'].mode()[0] if 'ca_name' in grupo.columns else "N/A"

            # 2º Filtro: Desenha APENAS se for CUBIC
            if algoritmo.lower() == 'cubic':
                cor = cores[linhas_validas % len(cores)] 
                label_conn = f"{src}->{dst} [CUBIC]"

                ax1.plot(grupo['tempo'], grupo['cwnd'], marker='o', markersize=6, linewidth=2.5, color=cor, label=f"Cwnd ({label_conn})")
                if 'packets_out' in grupo.columns:
                    ax1.plot(grupo['tempo'], grupo['packets_out'], linestyle='--', linewidth=2, color=cor, alpha=0.7, label=f"Packets Out ({label_conn})")

                ax2.plot(grupo['tempo'], grupo['srtt'], marker='s', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"SRTT us ({label_conn})")
                ax3.plot(grupo['tempo'], grupo['retrans'], marker='^', markersize=6, linewidth=2.5, linestyle='-', color=cor, label=f"Retransmissões ({label_conn})")
                linhas_validas += 1

    if linhas_validas > 0:
        ax1.set_ylabel("Pacotes", fontsize=13, fontweight='bold')
        ax2.set_ylabel("SRTT (µs)", fontsize=13, fontweight='bold')
        ax3.set_ylabel("Retransmissões", fontsize=13, fontweight='bold')

        for ax in [ax1, ax2, ax3]:
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
            ax.set_xlabel("Tempo da Captura", fontsize=13, fontweight='bold')
            ax.tick_params(axis='x', labelrotation=45)

        plt.tight_layout()
        nome_arquivo = f"Grafico_TCP_CUBIC_{datetime.now().strftime('%H%M%S')}.png"
        plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
        print(f"✅ Gráfico CUBIC salvo com sucesso: {nome_arquivo}")
        plt.show()
    else:
        print("⚠️ Nenhum fluxo CUBIC ativo encontrado nesta captura.")
else:
    print(f"❌ Nenhum tráfego detectado.")


# In[65]:


# CÉLULA: Gráfico Comparativo Acadêmico (CUBIC vs RENO)
import pandas as pd
import matplotlib.pyplot as plt

# Carrega os dados (certifique-se que os CSVs estão na mesma pasta)
df_cubic = pd.read_csv("dados_cubic.csv")
df_reno = pd.read_csv("dados_reno.csv")

# Converter SRTT de microssegundos (us) para milissegundos (ms) para o gráfico
df_cubic['srtt_ms'] = df_cubic['srtt'] / 1000.0
df_reno['srtt_ms'] = df_reno['srtt'] / 1000.0

# Define o tamanho da janela para a Média Móvel (suavização)
WINDOW = 15 

# Médias Móveis - Janela de Congestionamento (Cwnd)
df_cubic['cwnd_ma'] = df_cubic['cwnd'].rolling(window=WINDOW, min_periods=1).mean()
df_reno['cwnd_ma'] = df_reno['cwnd'].rolling(window=WINDOW, min_periods=1).mean()

# Médias Móveis - Latência (RTT)
df_cubic['srtt_ma'] = df_cubic['srtt_ms'].rolling(window=WINDOW, min_periods=1).mean()
df_reno['srtt_ma'] = df_reno['srtt_ms'].rolling(window=WINDOW, min_periods=1).mean()

# Configuração do Estilo Acadêmico
plt.style.use('default')
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 14))
fig.suptitle("Análise Comparativa de Controle de Congestionamento: TCP CUBIC vs TCP RENO", fontsize=18, fontweight='bold')

# Cores e Estilos de Linha (Alto Contraste para Impressão)
# CUBIC: Azul Escuro, Linha Sólida (Padrão)
# RENO: Vermelho Escuro, Linha Tracejada
COLOR_CUBIC = '#003366' 
COLOR_RENO = '#B22222'

# --- 1. GRÁFICO DE JANELA DE CONGESTIONAMENTO (Cwnd) ---
# Dados brutos no fundo (translúcidos)
ax1.plot(df_cubic['cwnd'], drawstyle='steps-post', color=COLOR_CUBIC, alpha=0.2, linewidth=1, linestyle='-')
ax1.plot(df_reno['cwnd'], drawstyle='steps-post', color=COLOR_RENO, alpha=0.2, linewidth=1, linestyle='-')

# Médias Móveis destacadas
ax1.plot(df_cubic['cwnd_ma'], color=COLOR_CUBIC, alpha=1.0, linewidth=2.5, linestyle='-', label=f'CUBIC (Média)')
ax1.plot(df_reno['cwnd_ma'], color=COLOR_RENO, alpha=1.0, linewidth=2.5, linestyle='--', label=f'RENO (Média)')

ax1.set_ylabel("Cwnd (Pacotes)", fontsize=12, fontweight='bold')
ax1.legend(loc='upper left', framealpha=0.9)
ax1.grid(True, linestyle=':', alpha=0.7)

# --- 2. GRÁFICO DE LATÊNCIA (RTT) ---
# Dados brutos no fundo
ax2.plot(df_cubic['srtt_ms'], color=COLOR_CUBIC, alpha=0.2, linewidth=1, linestyle='-')
ax2.plot(df_reno['srtt_ms'], color=COLOR_RENO, alpha=0.2, linewidth=1, linestyle='-')

# Médias Móveis destacadas
ax2.plot(df_cubic['srtt_ma'], color=COLOR_CUBIC, alpha=1.0, linewidth=2.5, linestyle='-', label='CUBIC (Média)')
ax2.plot(df_reno['srtt_ma'], color=COLOR_RENO, alpha=1.0, linewidth=2.5, linestyle='--', label='RENO (Média)')

ax2.set_ylabel("RTT (ms)", fontsize=12, fontweight='bold')
ax2.legend(loc='upper left', framealpha=0.9)
ax2.grid(True, linestyle=':', alpha=0.7)

# --- 3. GRÁFICO DE RETRANSMISSÕES ---
# Retransmissões (Usamos step-post para mostrar saltos discretos)
ax3.plot(df_cubic['retrans'], drawstyle='steps-post', color=COLOR_CUBIC, linewidth=2, linestyle='-', label='CUBIC')
ax3.plot(df_reno['retrans'], drawstyle='steps-post', color=COLOR_RENO, linewidth=2, linestyle='--', label='RENO')

ax3.set_ylabel("Retransmissões", fontsize=12, fontweight='bold')
ax3.set_xlabel("Amostras de Tempo", fontsize=12, fontweight='bold')
ax3.legend(loc='upper left', framealpha=0.9)
ax3.grid(True, linestyle=':', alpha=0.7)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
plt.savefig("Comparativo_Academico_Final.png", dpi=300, bbox_inches='tight')
plt.show()


# In[62]:


import pandas as pd
import matplotlib.pyplot as plt

# Carrega os dados exportados
df_cubic = pd.read_csv("dados_cubic.csv")
df_reno = pd.read_csv("dados_reno.csv")

# Prepara a figura comparativa
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
fig.suptitle("Comparativo TCP: Cubic vs Reno", fontsize=16, fontweight='bold')

# Plotar Cwnd
ax1.plot(df_cubic['cwnd'], label='CUBIC', color='blue', alpha=0.7)
ax1.plot(df_reno['cwnd'], label='RENO', color='red', alpha=0.7)
ax1.set_ylabel("Janela de Congestionamento (Cwnd)")
ax1.legend()
ax1.grid(True, linestyle='--')

# Plotar Retransmissões
ax2.plot(df_cubic['retrans'], label='CUBIC', color='blue')
ax2.plot(df_reno['retrans'], label='RENO', color='red')
ax2.set_ylabel("Retransmissões Acumuladas")
ax2.set_xlabel("Amostras de Tempo")
ax2.legend()
ax2.grid(True, linestyle='--')

plt.tight_layout()
plt.savefig("Comparativo_Final.png")
plt.show()


# In[63]:


# CÉLULA: Gráfico Comparativo Avançado (CUBIC vs RENO)
import pandas as pd
import matplotlib.pyplot as plt

# Carrega os dados (certifique-se que os CSVs estão na mesma pasta)
df_cubic = pd.read_csv("dados_cubic.csv")
df_reno = pd.read_csv("dados_reno.csv")

# Prepara a figura com 3 subplots: Cwnd, Throughput Estimado, Retransmissões
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 14))
fig.suptitle("Comparativo TCP: Cubic vs Reno", fontsize=18, fontweight='bold')

# --- 1. Janela de Congestionamento (Cwnd) ---
ax1.plot(df_cubic['cwnd'], label='CUBIC', color='#1f77b4', alpha=0.7, linewidth=2)
ax1.plot(df_reno['cwnd'], label='RENO', color='#d62728', alpha=0.5, linewidth=2)
ax1.set_ylabel("Janela (Cwnd)")
ax1.legend()
ax1.grid(True, linestyle='--', alpha=0.6)

# --- 2. Throughput Estimado (Mbps) ---
# Cálculo: (Cwnd * MSS * 8) / (SRTT_s) -> Aqui usamos uma estimativa simplificada
# Assumindo MSS de 1460 bytes. SRTT está em microssegundos (us).
df_cubic['throughput'] = (df_cubic['cwnd'] * 1460 * 8) / (df_cubic['srtt'] + 1)
df_reno['throughput'] = (df_reno['cwnd'] * 1460 * 8) / (df_reno['srtt'] + 1)

ax2.plot(df_cubic['throughput'] / 1e6, label='CUBIC', color='#1f77b4', alpha=0.7, linewidth=2)
ax2.plot(df_reno['throughput'] / 1e6, label='RENO', color='#d62728', alpha=0.5, linewidth=2)
ax2.set_ylabel("Throughput Estimado (Mbps)")
ax2.legend()
ax2.grid(True, linestyle='--', alpha=0.6)

# --- 3. Retransmissões Acumuladas ---
ax3.plot(df_cubic['retrans'], label='CUBIC', color='#1f77b4', linewidth=2)
ax3.plot(df_reno['retrans'], label='RENO', color='#d62728', linewidth=2)
ax3.set_ylabel("Retransmissões")
ax3.set_xlabel("Amostras de Tempo")
ax3.legend()
ax3.grid(True, linestyle='--', alpha=0.6)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
plt.savefig("Comparativo_Final_Aprimorado.png", dpi=300)
plt.show()


# In[64]:


# CÉLULA: Gráfico Comparativo Acadêmico (CUBIC vs RENO)
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Carrega os dados (certifique-se que os CSVs estão na mesma pasta)
df_cubic = pd.read_csv("dados_cubic.csv")
df_reno = pd.read_csv("dados_reno.csv")

# Define o tamanho da janela para a Média Móvel
# Valor 15 abstrai o ruído e mostra a tendência real de performance
WINDOW = 15 
df_cubic['cwnd_ma'] = df_cubic['cwnd'].rolling(window=WINDOW, min_periods=1).mean()
df_reno['cwnd_ma'] = df_reno['cwnd'].rolling(window=WINDOW, min_periods=1).mean()

# Cálculo Correto: (Cwnd [pacotes] * 1460 [bytes] * 8 [bits]) / SRTT [us] = bits/us = Mbps
df_cubic['throughput'] = (df_cubic['cwnd'] * 1460 * 8) / (df_cubic['srtt'] + 1)
df_reno['throughput'] = (df_reno['cwnd'] * 1460 * 8) / (df_reno['srtt'] + 1)

# Aplicando média móvel também ao Throughput
df_cubic['thr_ma'] = df_cubic['throughput'].rolling(window=WINDOW, min_periods=1).mean()
df_reno['thr_ma'] = df_reno['throughput'].rolling(window=WINDOW, min_periods=1).mean()

plt.style.use('default')
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 15))
fig.suptitle("Comparativo Avançado TCP: Cubic vs Reno", fontsize=20, fontweight='bold')

# Cores Acadêmicas (Colorblind-friendly / Alto Contraste)
COLOR_CUBIC = '#005b96' # Azul escuro/profundo
COLOR_RENO = '#d62728'  # Vermelho clássico

# Dados brutos no fundo (translúcidos e em degraus)
ax1.plot(df_cubic['cwnd'], drawstyle='steps-post', color=COLOR_CUBIC, alpha=0.25, linewidth=1.5, label='CUBIC (Bruto)')
ax1.plot(df_reno['cwnd'], drawstyle='steps-post', color=COLOR_RENO, alpha=0.25, linewidth=1.5, label='RENO (Bruto)')
# Média Móvel na frente (opaca e grossa)
ax1.plot(df_cubic['cwnd_ma'], color=COLOR_CUBIC, alpha=1.0, linewidth=3, label=f'CUBIC (Média Móvel {WINDOW})')
ax1.plot(df_reno['cwnd_ma'], color=COLOR_RENO, alpha=1.0, linewidth=3, label=f'RENO (Média Móvel {WINDOW})')

ax1.set_ylabel("Janela (Cwnd) - Pacotes", fontsize=12, fontweight='bold')
ax1.legend(loc='upper left', ncol=2) # ncol=2 espalha a legenda
ax1.grid(True, linestyle='--', alpha=0.6)

ax2.plot(df_cubic['throughput'], drawstyle='steps-post', color=COLOR_CUBIC, alpha=0.25, linewidth=1.5)
ax2.plot(df_reno['throughput'], drawstyle='steps-post', color=COLOR_RENO, alpha=0.25, linewidth=1.5)
ax2.plot(df_cubic['thr_ma'], color=COLOR_CUBIC, alpha=1.0, linewidth=3, label='CUBIC (Média)')
ax2.plot(df_reno['thr_ma'], color=COLOR_RENO, alpha=1.0, linewidth=3, label='RENO (Média)')

ax2.set_ylabel("Throughput (Mbps)", fontsize=12, fontweight='bold')
ax2.legend(loc='upper left')
ax2.grid(True, linestyle='--', alpha=0.6)

# Retransmissões usam sempre degraus pois é uma métrica cumulativa de eventos isolados
ax3.plot(df_cubic['retrans'], drawstyle='steps-post', color=COLOR_CUBIC, linewidth=3, label='CUBIC')
ax3.plot(df_reno['retrans'], drawstyle='steps-post', color=COLOR_RENO, linewidth=3, label='RENO')
ax3.set_ylabel("Retransmissões Acumuladas", fontsize=12, fontweight='bold')
ax3.set_xlabel("Amostras de Tempo", fontsize=12, fontweight='bold')
ax3.legend(loc='upper left')
ax3.grid(True, linestyle='--', alpha=0.6)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
plt.savefig("Comparativo_Academico_Final.png", dpi=300, bbox_inches='tight')
plt.show()


# In[ ]:




