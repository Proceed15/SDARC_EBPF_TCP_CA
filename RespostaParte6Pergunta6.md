# Resposta
Parte 6 - Análise Crítica, a Pergunta 6 questiona: "Quais limitações foram encontradas no uso do eBPF para observabilidade TCP?".  
Você poderá argumentar brilhantemente que testar perdas de pacotes enviando tráfego para a própria interface no WSL2 mascara as retransmissões reais 
porque o roteamento local burla o qdisc onde as falhas são injetadas. Para capturar as retransmissões e avaliar o ssthresh na prática, 
o tráfego precisará ser disparado contra um servidor externo real na internet.
