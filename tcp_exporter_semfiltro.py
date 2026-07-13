import subprocess
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuração da API
HOST = '0.0.0.0'
PORT = 8080

# Definição da porta alvo para filtragem em user-space, otimizando o processamento de pacotes irrelevantes.
PORTA_FILTRO = 0 
# 5202
def coletar_dados_ebpf():
    """ 
    Extração dos dados do mapa eBPF alocado no Kernel Linux.
    A execução ocorre via subprocesso utilizando o utilitário 'bpftool'.
    """
    try:
        # Chamada de sistema. O parâmetro '-j' força o retorno dos dados formatados em JSON.
        resultado = subprocess.run(
            ["sudo", "bpftool", "map", "dump", "name", "tcp_metrics_map", "-j"],
            capture_output=True, text=True, check=True
        )
        # Deserialização do objeto JSON.
        return json.loads(resultado.stdout)
    except Exception as e:
        # Tratamento de exceções para falhas de acesso ou ausência do mapa eBPF.
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Erro bpftool: {e}")
        return []

class MetricasHandler(BaseHTTPRequestHandler):
    """
    Classe manipuladora de requisições HTTP GET para exportação das métricas.
    """
    def do_GET(self):
        # Coleta das métricas atualizadas no Kernel.
        dados_kernel = coletar_dados_ebpf()

        # =====================================================================
        # ROTA 1: Endpoint JSON para consumo via Jupyter Notebook.
        # =====================================================================
        if self.path == '/api/json':
            # Definição do código de status 200 (OK).
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            # Configuração de CORS para permissão de acesso externo.
            self.send_header('Access-Control-Allow-Origin', '*') 
            self.end_headers()
            
            dados_filtrados = []
            
            # Iteração sobre as conexões TCP capturadas.
            for elemento in dados_kernel:
                src_port, dst_port = 0, 0
                
                # Verificação de suporte a BTF (BPF Type Format) para conversão automática das estruturas em C.
                formatado = elemento.get('formatted')
                
                if formatado:
                    # Extração direta via BTF.
                    chave = formatado.get('key', {})
                    src_port = chave.get('src_port', 0)
                    dst_port = chave.get('dst_port', 0)
                else:
                    # Modo de contingência para extração de dados brutos (Hexadecimal) em ambientes sem BTF.
                    raw_key = elemento.get('key', [])
                    if len(raw_key) >= 12:
                        # Reconstrução de variáveis inteiras de 16 bits (Little Endian) via operações bit a bit (Bitwise OR e Shift).
                        src_port = int(raw_key[8], 16) | (int(raw_key[9], 16) << 8)
                        dst_port = int(raw_key[10], 16) | (int(raw_key[11], 16) << 8)
                
                # Aplicação da regra de filtragem de porta.
                if PORTA_FILTRO == 0 or src_port == PORTA_FILTRO or dst_port == PORTA_FILTRO:
                    dados_filtrados.append(elemento)
            
            # Construção da estrutura de resposta JSON.
            resposta = {
                "timestamp": datetime.now().isoformat(),
                "total_conexoes_rastreadas": len(dados_kernel),
                "conexoes_filtradas_enviadas": len(dados_filtrados),
                "porta_alvo": PORTA_FILTRO,
                "dados": dados_filtrados
            }
            # Codificação e transmissão dos dados via rede.
            self.wfile.write(json.dumps(resposta, indent=2).encode('utf-8'))

        # =====================================================================
        # ROTA 2: Endpoint para consumo via Prometheus/Grafana.
        # =====================================================================
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()

            # Configuração do formato de texto plano exigido pelo Prometheus.
            resposta_prometheus = "# HELP tcp_cwnd Janela de Congestionamento TCP\n"
            resposta_prometheus += "# TYPE tcp_cwnd gauge\n\n"

            btf_ausente = False

            # Processamento idêntico ao endpoint JSON.
            for elemento in dados_kernel:
                src_port, dst_port, snd_cwnd = 0, 0, 0
                formatado = elemento.get('formatted')
                
                if formatado:
                    chave = formatado.get('key', {})
                    valor = formatado.get('value', {})
                    src_port = chave.get('src_port', 0)
                    dst_port = chave.get('dst_port', 0)
                    snd_cwnd = valor.get('snd_cwnd', 0)
                else:
                    btf_ausente = True
                    raw_key = elemento.get('key', [])
                    raw_value = elemento.get('value', [])
                    
                    if len(raw_key) >= 12 and len(raw_value) >= 4:
                        src_port = int(raw_key[8], 16) | (int(raw_key[9], 16) << 8)
                        dst_port = int(raw_key[10], 16) | (int(raw_key[11], 16) << 8)
                        # Reconstrução de variável inteira de 32 bits (4 bytes).
                        snd_cwnd = int(raw_value[0], 16) | (int(raw_value[1], 16) << 8) | \
                                   (int(raw_value[2], 16) << 16) | (int(raw_value[3], 16) << 24)
                
                # Inclusão no payload de resposta caso a conexão esteja ativa (cwnd > 0).
                if snd_cwnd > 0:
                    labels = f'src_port="{src_port}",dst_port="{dst_port}"'
                    resposta_prometheus += f"tcp_cwnd{{{labels}}} {snd_cwnd}\n"
            
            # Registro de log indicando o uso do modo de contingência sem BTF.
            if btf_ausente:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] AVISO: Modo tradutor BTF ativo.")
            
            self.wfile.write(resposta_prometheus.encode('utf-8'))
            
        # Resposta para rotas não mapeadas (Erro 404).
        else:
            self.send_response(404)
            self.end_headers()

def iniciar_servidor():
    """ 
    Inicialização do servidor HTTP.
    """
    servidor = HTTPServer((HOST, PORT), MetricasHandler)
    print("Observatorio de Congestionamento TCP iniciado.")
    print(f"Filtro ativo na porta: {PORTA_FILTRO}")
    print(f"Endpoint Prometheus: http://localhost:{PORT}/metrics")
    print(f"Endpoint JSON: http://localhost:{PORT}/api/json")
    print("Aguardando conexoes. Pressione Ctrl+C para encerrar.")
    
    try:
        # Execução contínua do servidor.
        servidor.serve_forever()
    except KeyboardInterrupt:
        # Tratamento de interrupção (SIGINT) para encerramento seguro.
        print("\nServidor encerrado.")
        servidor.server_close()

# Ponto de entrada do script.
if __name__ == '__main__':
    iniciar_servidor()
