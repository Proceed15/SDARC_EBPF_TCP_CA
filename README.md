SDARC_EBPF_TCP_CA

Descrição do Projeto

O SDARC_EBPF_TCP_CA é uma ferramenta de observabilidade de rede voltada à análise de telemetria TCP diretamente no kernel do Linux. Utilizando a tecnologia eBPF (Extended Berkeley Packet Filter), o sistema monitora o comportamento das conexões TCP e métricas de controle de congestionamento, permitindo a extração de dados em tempo real sem a necessidade de instrumentação invasiva ou modificação do código-fonte do sistema operacional.

Requisitos de Sistema

Para o correto funcionamento, o ambiente deve satisfazer as seguintes dependências:

Kernel Linux: Versão 5.x ou superior com suporte a eBPF.

Compilação: clang e llvm.

Gestão eBPF: bpftool.

Análise: Python 3.x com pandas, matplotlib e requests.

Estrutura do Repositório

Arquivo

Descrição

tcp_co_kernel.c

Código-fonte BPF para instrumentação via kprobe/tcp_ack.

tcp_exporter.py

API responsável pela extração da telemetria do mapa BPF.

Analise_TCP.ipynb

Jupyter Notebook para tratamento, análise e visualização de dados.

⚙️ Fluxo de Execução

1. Compilação e Carga do Programa BPF

O programa BPF deve ser compilado e carregado no espaço de kernel.

Compilação:

clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -c tcp_co_kernel.c -o tcp_co_kernel.o


Carga no Kernel:

sudo bpftool prog loadall tcp_co_kernel.o /sys/fs/bpf/tcp_obs autoattach


2. Execução da API de Exportação

A API deve ser iniciada para disponibilizar os dados do mapa BPF via interface JSON.

sudo python3 tcp_exporter.py


O serviço disponibiliza os dados em http://localhost:8080/api/json.

3. Análise de Dados

A análise técnica é realizada no Jupyter Notebook.

Inicie o servidor Jupyter:

jupyter notebook


No notebook Analise_TCP.ipynb, configure a variável URL_API para o endereço da API em execução.

Execute as células de coleta de dados e utilize os métodos de plotagem para a geração dos gráficos de Cwnd, RTT e Retransmissões.

Encerramento da Execução

Para garantir a limpeza dos recursos alocados no subsistema eBPF, remova o diretório de persistência:

sudo rm -rf /sys/fs/bpf/tcp_obs


Este projeto foi desenvolvido como atividade prática focada em instrumentação de sistemas de rede.