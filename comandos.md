# Comandos para Linux (Ubuntu):
Todos para serem executados no Linux (Ubuntu).
## Comandos de instalação:
sudo apt update
sudo apt install -y iperf3
## Comandos de execução (eth0):
tc qdisc add dev eth0 root netem delay 100ms
tc qdisc add dev eth0 root netem loss 2%
tc qdisc add dev eth0 root tbf rate 10mbit burst 32k latency 400ms
tc qdisc add dev eth0 root handle 1: netem delay 50ms loss 1%
tc qdisc add dev eth0 parent 1:1 handle 10: tbf rate 5mbit burst 32k latency 400ms
## Comandos de execução (loopback, o "lo" no comando):

### Comando de Limpeza:
sudo tc qdisc del dev lo root
### Comandos de Aumento de RTT:
sudo tc qdisc add dev lo root netem delay 100ms
### Comando de Perda de Pacotes (3%):
sudo tc qdisc add dev lo root netem loss 3%
### Comando de Limitação de Banda:
sudo tc qdisc add dev lo root tbf rate 10mbit burst 32k latency 400ms
### Comandos para a Combinação de Falhas (Atraso+Perda+Limitação):
sudo tc qdisc add dev lo root handle 1: netem delay 50ms loss 1%
sudo tc qdisc add dev lo parent 1:1 handle 10: tbf rate 5mbit burst 32k latency 400ms

