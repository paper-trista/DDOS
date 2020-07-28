s1_ip_list = ['192.168.1.1','192.168.1.2','192.168.1.3','192.168.1.4']

s2_ip_list = ['192.168.2.1','192.168.2.2','192.168.2.3','192.168.2.4']

s3_ip_list = ['192.168.3.1','192.168.3.2','192.168.3.3','192.168.3.4']

s4_ip_list = ['192.168.4.1','192.168.4.2','192.168.4.3','192.168.4.4']


s1_ports = [21, 23, 25, 80]
s2_ports = [21, 22, 23, 25]
s3_ports = [21, 22, 23]
s4_ports = [21, 22, 23]

ext_ports = [1599, 2233]


k1 = s1_ports
k2 = s2_ports + ext_ports
k3 = s3_ports + ext_ports
k4 = s4_ports + ext_ports


s1_dst_list = s2_ip_list +s3_ip_list + s4_ip_list
s2_dst_list = s1_ip_list +s3_ip_list + s4_ip_list
s3_dst_list = s2_ip_list +s1_ip_list + s4_ip_list
s4_dst_list = s2_ip_list +s3_ip_list + s1_ip_list
