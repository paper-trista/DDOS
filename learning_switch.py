# -*- coding: UTF-8 -*-

from ryu.lib.packet import *
from ryu.lib.packet import in_proto
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import ether_types
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
import csv
import math

#  idle_timeout

filename = "numberip.csv"

class IcmpResponder(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(IcmpResponder, self).__init__(*args, **kwargs)
        self.mac_to_port = {}#mac到port的映射
        self.ip_to_port = {}#ip到port的映射
        self.idle_timeout = 10
        total = 0

    # switch IN
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # 发一条 匹配不到交换机的数据要上传给控制器的流表项。默认流表项。
        match = ofp_parser.OFPMatch()#match不到任何东西。
        actions = [ofp_parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )] #output动作，发送给controller，不缓存。
        self.add_flow(datapath, 0, match, actions)#优先级为0的默认流表项。

    # 发送流表项并且安装到交换机上的函数。
    def add_flow(self,datapath, priority, match, actions, idle_timeout = 0):
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        #构建一个flow_mod消息并且发送
        inst = [ofp_parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS,
            actions)]#给他一个“即刻应用动作集”的指令
        #构建流表项
        mod = ofp_parser.OFPFlowMod(
            datapath = datapath,
            priority = priority,
            match = match,
            instructions = inst,
            idle_timeout = self.idle_timeout
        )#整个流表项
        datapath.send_msg(mod)#发送

    # packet_in handler
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg#提取msg
        datapath = msg.datapath#提取datapath
        ofproto = datapath.ofproto#提取版本
        parser = datapath.ofproto_parser#提取对应解析模块
        in_port = msg.match['in_port']#提取入端口，下发流表的时候用


        pkt = packet.Packet(msg.data) #解析一个报文，把字节流传给pkt，ryu会自动解析
        eth = pkt.get_protocols(ethernet.ethernet)[0]#解析以太网协议

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst#获取目的mac地址
        src = eth.src#获取源mac地址

        dpid = datapath.id#获取交换机id
        self.mac_to_port.setdefault(dpid, {})#创建子字典，key=dpid，值=字典{mac_to_port键值对}
        self.ip_to_port.setdefault(dpid, {})


        # 控制器学习新消息的mac地址和入端口的映射关系，以便后续使用，避免下次泛洪
        self.mac_to_port[dpid][src] = in_port
        #mac学习
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst] #如果已经存在，直接读取，决定用哪个端口转发
        else:#如果没有就泛洪FLOOD
            out_port = ofproto.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port, ofproto.OFPCML_NO_BUFFER)]
        data = None#动作集和数据
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:#不缓存
            data = msg.data#提取数据

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)#发送泛洪消息
        #学习结束


        #如果是arp报文，记录源ip的进端口
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            arp_ip_src = pkt_arp.src_ip
            arp_ip_dst = pkt_arp.dst_ip
            #print(arp_ip_dst)

            self.ip_to_port[dpid][arp_ip_src] = in_port
            if arp_ip_dst in self.ip_to_port[dpid]:
                out_port = self.ip_to_port[dpid][arp_ip_dst]
            else:
                out_port = ofproto.OFPP_FLOOD

            actions = [parser.OFPActionOutput(out_port, ofproto.OFPCML_NO_BUFFER)]

            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions,
                data=msg.data
            )
            datapath.send_msg(out)
            return

        #如果是ipv4报文，则要对报文进行分类，分出icmp、tcp、udp报文，并执行相应的流表下发规则
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        #if pkt_ipv4:
        if pkt_ipv4:

            ip4_src = pkt_ipv4.src
            ip4_dst = pkt_ipv4.dst
            ip4_pro = pkt_ipv4.proto
            #print(ip4_dst)
            f = open('numberip.csv','a')
            csv_writer = csv.writer(f)
            csv_writer.writerow([ip4_src, ip4_dst])
            f.close()
            reader = csv.reader(open(filename, "r"))  # 读取csv文件
            lines=0
            for item in reader:  # 读取每一行
                lines+=1
            if lines>=50:
                print("dayu 50 le")
                #duqu csv
                csv_reader = csv.reader(open(filename))
                dataSet=[]
                for row in csv_reader:
                    dataSet.append(row)
                print("Read All!")
                #jisuan shang
                numEntries = len(dataSet)
                labelCounts = {}
                for featvec in dataSet:
                    currentLbel = featvec[-1]
                    if currentLbel not in labelCounts.keys():
                        labelCounts[currentLbel] = 0
                    labelCounts[currentLbel] += 1
                shannonEnt = 0.0
                for key in labelCounts:
                    prob = float(labelCounts[key])/numEntries
                    shannonEnt -= prob * math.log(prob, 2) # log base 2
                print(shannonEnt)
                #qingkong csv
                file = open('numberip.csv','w')
                file.seek(0)
                file.truncate()
                file.close()
            else:
                pass #sha ye bu zuo

            self.ip_to_port[dpid][ip4_src] = in_port

            if ip4_dst in self.ip_to_port[dpid]:
                out_port = self.ip_to_port[dpid][ip4_dst]
            else:
                out_port = 5#ofproto.OFPP_FLOOD #

            actions = [parser.OFPActionOutput(out_port)]

            if out_port != ofproto.OFPP_FLOOD:
                # icmp
                if ip4_pro == in_proto.IPPROTO_ICMP:
                    #if dpid == 1:
                    #    print('icmp', self.ip_to_port[dpid])
                    match = parser.OFPMatch(
                        #in_port=in_port,
                        eth_type=ether_types.ETH_TYPE_IP,
                        ip_proto = ip4_pro,
                        ipv4_src=ip4_src, ipv4_dst=ip4_dst
                    )
                    self.add_flow(datapath, 1, match, actions, self.idle_timeout)
                    return

                # tcp
                if ip4_pro == in_proto.IPPROTO_TCP:
                    #print(pkt_ipv4)
                    #if dpid == 1:
                    #    print('tcp', self.ip_to_port[dpid])

                    pkt_tcp = pkt.get_protocol(tcp.tcp)
                    tcp_src_port = pkt_tcp.src_port
                    tcp_dst_port = pkt_tcp.dst_port

                    match = parser.OFPMatch(
                        #in_port=in_port,
                        eth_type=ether_types.ETH_TYPE_IP,
                        ip_proto=ip4_pro,
                        ipv4_src=ip4_src, ipv4_dst=ip4_dst,
                        tcp_src = tcp_src_port,
                        tcp_dst = tcp_dst_port
                    )
                    self.add_flow(datapath, 1, match, actions, self.idle_timeout)
                    return

                # udp
                if ip4_pro == in_proto.IPPROTO_UDP:
                    #if dpid == 1:
                    #    print('udp', self.ip_to_port[dpid])

                    pkt_udp = pkt.get_protocol(udp.udp)
                    udp_src_port = pkt_udp.src_port
                    udp_dst_port = pkt_udp.dst_port

                    match = parser.OFPMatch(
                        #in_port=in_port,
                        eth_type=ether_types.ETH_TYPE_IP,
                        ip_proto=ip4_pro,
                        ipv4_src=ip4_src, ipv4_dst=ip4_dst,
                        udp_src=udp_src_port,
                        udp_dst=udp_dst_port
                    )
                    self.add_flow(datapath, 1, match, actions, self.idle_timeout)
                    return

            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions,
                data=msg.data
            )
            datapath.send_msg(out)
            return
