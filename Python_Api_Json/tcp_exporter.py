import subprocess
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = '0.0.0.0'
PORT = 8080

# NOVO: Filtro direto no Backend para acelerar a API!
# Mude para 0 se quiser capturar TODAS as portas novamente.
PORTA_FILTRO = 5202 

def coletar_dados_ebpf():
    """ Extrai os dados do mapa usando o bpftool em formato JSON """
    try:
        resultado = subprocess.run(
            ["sudo", "bpftool", "map", "dump", "name", "tcp_metrics_map", "-j"],
            capture_output=True, text=True, check=True
        )
        return json.loads(resultado.stdout)
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Erro bpftool: {e}")
        return []

class MetricasHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        dados_kernel = coletar_dados_ebpf()

        # 1. ROTA PARA JUPYTER NOTEBOOK / RAW JSON
        if self.path == '/api/json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') 
            self.end_headers()
            
            dados_filtrados = []
            
            # FILTRAGEM NO BACKEND (Muito mais rápido!)
            for elemento in dados_kernel:
                src_port, dst_port = 0, 0
                formatado = elemento.get('formatted')
                
                if formatado:
                    chave = formatado.get('key', {})
                    src_port = chave.get('src_port', 0)
                    dst_port = chave.get('dst_port', 0)
                else:
                    raw_key = elemento.get('key', [])
                    if len(raw_key) >= 12:
                        src_port = int(raw_key[8], 16) | (int(raw_key[9], 16) << 8)
                        dst_port = int(raw_key[10], 16) | (int(raw_key[11], 16) << 8)
                
                # Só anexa ao JSON final se pertencer à porta desejada (ou se o filtro for 0)
                if PORTA_FILTRO == 0 or src_port == PORTA_FILTRO or dst_port == PORTA_FILTRO:
                    dados_filtrados.append(elemento)
            
            resposta = {
                "timestamp": datetime.now().isoformat(),
                "total_conexoes_rastreadas": len(dados_kernel),
                "conexoes_filtradas_enviadas": len(dados_filtrados),
                "porta_alvo": PORTA_FILTRO,
                "dados": dados_filtrados
            }
            self.wfile.write(json.dumps(resposta, indent=2).encode('utf-8'))

        # 2. ROTA PARA GRAFANA / PROMETHEUS
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()

            resposta_prometheus = "# HELP tcp_cwnd Janela de Congestionamento TCP\n"
            resposta_prometheus += "# TYPE tcp_cwnd gauge\n\n"

            btf_ausente = False

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
                        snd_cwnd = int(raw_value[0], 16) | (int(raw_value[1], 16) << 8) | \
                                   (int(raw_value[2], 16) << 16) | (int(raw_value[3], 16) << 24)
                
                if snd_cwnd > 0:
                    labels = f'src_port="{src_port}",dst_port="{dst_port}"'
                    resposta_prometheus += f"tcp_cwnd{{{labels}}} {snd_cwnd}\n"
            
            if btf_ausente:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛠️ MODO TRADUTOR BTF ativo.")
            
            self.wfile.write(resposta_prometheus.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def iniciar_servidor():
    servidor = HTTPServer((HOST, PORT), MetricasHandler)
    print(f"🚀 Observatório Blindado iniciado!")
    print(f"🎯 FILTRO ATIVO: Porta {PORTA_FILTRO}")
    print(f"📊 Grafana/Prometheus : http://localhost:{PORT}/metrics")
    print(f"📓 Jupyter / JSON     : http://localhost:{PORT}/api/json")
    print("Pressione Ctrl+C para parar...")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        servidor.server_close()

if __name__ == '__main__':
    iniciar_servidor()