#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>
// Definindo a família de endereços AF_INET caso não esteja definida, os includes acima servem para incluir as definições do kernel e as funções auxiliares do BPF, como bpf_map_update_elem, bpf_core_read, entre outras...
#ifndef AF_INET
#define AF_INET 2
#endif
// A Chave: Identifica a conexão única
struct flow_key {
    u32 src_ip;
    u32 dst_ip;
    u16 src_port;
    u16 dst_port;
};

// Os Valores: Métricas do TCP (Versão com Bônus - Parte 2 do Trabalho)
struct tcp_metrics {
    // Métricas base do TCP
    u32 snd_cwnd;
    u32 ssthresh;
    u32 srtt;
    u32 retransmissions;
    u32 duplicate_acks;
    u64 bytes_acked;
    //Bônus: Estado do algoritmo de congestionamento
    u8  ca_state; 
    
    // --- NOVAS MÉTRICAS ---
    //Bônus: Métricas adicionais do TCP, 
    // o packets_out é o número de pacotes que estão atualmente em voo (enviados, mas não confirmados), 
    // lembrar que o retrans_out é o número de pacotes que foram retransmitidos,
    // o sndbuf é o tamanho do buffer de envio do socket, e o sk_state é o estado atual do socket TCP. 
    u32 packets_out;
    u32 retrans_out;
    u32 sndbuf;
    u8  sk_state;        // Estado TCP (1 = ESTABLISHED)
    //Bônus: Nome do algoritmo de congestionamento
    char ca_name[16];    // Nome do algoritmo (cubic, reno, bbr)
};

// O Mapa
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __type(key, struct flow_key);
    __type(value, struct tcp_metrics);
    __uint(max_entries, 10240);
} tcp_metrics_map SEC(".maps");

// O Hook (gancho) do kprobe para a função tcp_ack
SEC("kprobe/tcp_ack")
int BPF_KPROBE(kprobe_tcp_ack, struct sock *sk)
{
    u16 family = BPF_CORE_READ(sk, __sk_common.skc_family);
    
    // Verifica se é IPv4
    if (family != AF_INET) {
        return 0;
    }
    // Coleta a chave da conexão
    struct flow_key key = {};
    key.src_ip = BPF_CORE_READ(sk, __sk_common.skc_rcv_saddr);
    key.dst_ip = BPF_CORE_READ(sk, __sk_common.skc_daddr);
    key.src_port = BPF_CORE_READ(sk, __sk_common.skc_num);
    key.dst_port = bpf_ntohs(BPF_CORE_READ(sk, __sk_common.skc_dport));
    // Coleta as métricas do TCP
    struct tcp_sock *ts = (struct tcp_sock *)sk;
    struct tcp_metrics metrics = {};

    // Coleta as métricas base
    metrics.snd_cwnd = BPF_CORE_READ(ts, snd_cwnd);
    metrics.ssthresh = BPF_CORE_READ(ts, snd_ssthresh);
    metrics.srtt = BPF_CORE_READ(ts, srtt_us) >> 3; 
    metrics.retransmissions = BPF_CORE_READ(ts, total_retrans);
    metrics.bytes_acked = BPF_CORE_READ(ts, bytes_acked);
    // Coleta os acks duplicados
    // NOTA: Como o kernel não tem um contador global chamado 'dup_acks_in_window', 
    // usamos 'sacked_out', que conta os pacotes confirmados seletivamente 
    // (a representação prática de DUP ACKs recebidos pelo remetente).
    metrics.duplicate_acks = BPF_CORE_READ(ts, sacked_out);
    struct inet_connection_sock *icsk = (struct inet_connection_sock *)sk;
    metrics.ca_state = BPF_CORE_READ_BITFIELD_PROBED(icsk, icsk_ca_state);

    // --- COLETANDO AS NOVAS MÉTRICAS ---
    metrics.packets_out = BPF_CORE_READ(ts, packets_out);
    metrics.retrans_out = BPF_CORE_READ(ts, retrans_out);
    metrics.sndbuf = BPF_CORE_READ(sk, sk_sndbuf);
    metrics.sk_state = BPF_CORE_READ(sk, __sk_common.skc_state);

    // Lendo o NOME do Algoritmo de Congestionamento de forma segura (CO-RE INTO)
    BPF_CORE_READ_INTO(&metrics.ca_name, icsk, icsk_ca_ops, name);
    // Atualiza o mapa com as métricas coletadas
    bpf_map_update_elem(&tcp_metrics_map, &key, &metrics, BPF_ANY);
    // Retorna 0 para indicar sucesso
    return 0;
}
// Definindo a licença do programa eBPF como GPL
char _license[] SEC("license") = "GPL";
