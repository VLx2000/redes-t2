import asyncio
import random
from tcputils import *


class Servidor:
    def __init__(self, rede, porta):
        self.rede = rede
        self.porta = porta
        self.conexoes = {}
        self.callback = None
        self.rede.registrar_recebedor(self._rdt_rcv)

    def registrar_monitor_de_conexoes_aceitas(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que uma nova conexão for aceita
        """
        self.callback = callback

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, window_size, checksum, urg_ptr = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return
        if not self.rede.ignore_checksum and calc_checksum(segment, src_addr, dst_addr) != 0:
            print('descartando segmento com checksum incorreto')
            return

        payload = segment[4*(flags>>12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN:
            # A flag SYN estar setada significa que é um cliente tentando estabelecer uma conexão nova
            '''
            1-  O cliente envia um segmento contendo um valor sequencial inicial com o flag Syn activo.
                Esse segmento serve como uma solicitação ao servidor para começar uma sessão.
            2-  O Servidor responde com um segmento contendo um valor de confirmação igual ao valor sequencial mais 1 
                (Ack=Seq100 + 1 = 101 , mais seu próprio valor sequencial de sincronização  Seq=300 , com o flag[Syn,Ack] . 
                O Ack é sempre o próximo Byte ou Octeto esperado.
            3-  O Cliente responde com um valor de confirmação igual ao valor sequencial  
                que ele recebeu mais um,[flag Ack=Seq300 + 1 = 301]. Isso completa o processo de estabelecimento de conexão.
                https://bloghandsonlabs.wordpress.com/2017/02/19/conexao-tcp-hand-shake-triplo/
            '''
            seq_servidor = random.randint(1024, 0xffff)
            seq_esperado = seq_no + 1
            segmento = fix_checksum(make_header(dst_port, src_port, seq_servidor, seq_esperado, (FLAGS_SYN|FLAGS_ACK)), src_addr, dst_addr) 
            # quando servidor vai mandar resposta (segmento) as portas dst e src invertem (o q recebia agora manda e vice-versa)
            ack_enviado = seq_servidor + 1
            conexao = self.conexoes[id_conexao] = Conexao(self, id_conexao, ack_enviado, seq_esperado)
            conexao.servidor.rede.enviar(segmento, src_addr)
            
            if self.callback:
                self.callback(conexao)
        elif id_conexao in self.conexoes:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexoes[id_conexao]._rdt_rcv(seq_no, ack_no, flags, payload)
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Conexao:
    def __init__(self, servidor, id_conexao, ack_enviado, seq_esperado):
        self.servidor = servidor
        self.id_conexao = id_conexao
        self.callback = None
        self.timer = asyncio.get_event_loop().call_later(1, self._exemplo_timer)  # um timer pode ser criado assim; esta linha é só um exemplo e pode ser removida
        #self.timer.cancel()   # é possível cancelar o timer chamando esse método; esta linha é só um exemplo e pode ser removida
        self.ack_enviado = ack_enviado
        self.seq_esperado = seq_esperado

    def _exemplo_timer(self):
        # Esta função é só um exemplo e pode ser removida
        print('Este é um exemplo de como fazer um timer')

    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        # TODO: trate aqui o recebimento de segmentos provenientes da camada de rede.
        # Chame self.callback(self, dados) para passar dados para a camada de aplicação após
        # garantir que eles não sejam duplicados e que tenham sido recebidos em ordem.
        if seq_no == self.seq_esperado and len(payload) > 0:
            (src_addr, src_port, dst_addr, dst_port) = self.id_conexao

            print('recebido payload: %r' % payload)
            self.callback(self, payload)
            self.seq_esperado += len(payload)
            segmento = fix_checksum(make_header(src_port, dst_port, self.ack_enviado, self.seq_esperado, (FLAGS_ACK)), src_addr, dst_addr) 
            self.servidor.rede.enviar(segmento, dst_addr)
        else:
            self.callback(self, b"")


    # Os métodos abaixo fazem parte da API

    def registrar_recebedor(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que dados forem corretamente recebidos
        """
        self.callback = callback

    def enviar(self, dados):
        """
        Usado pela camada de aplicação para enviar dados
        """
        # TODO: implemente aqui o envio de dados.
        # Chame self.servidor.rede.enviar(segmento, dest_addr) para enviar o segmento
        # que você construir para a camada de rede.
        pass

    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        # TODO: implemente aqui o fechamento de conexão
        pass
