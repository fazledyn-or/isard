#!/bin/sh -i

export DOMAIN
export HYPER_ID
export VIEWER_BROWSER
export VIEWER_SPICE
export BLACKLIST_IPTABLES

# Will remove hyper on docker shutdown
remove_hyper()
{
  python3 /src/lib/hypervisor.py delete
}
trap remove_hyper SIGTERM SIGINT SIGQUIT 

echo "---> Cleaning old libvirt info dirs..."
rm -rf /run/libvirt/*
rm -r /var/lib/libvirt/dnsmasq

ln -s /src/lib/api_client.py /src/vlans/api_client.py

echo "---> Setting ssh password to API_HYPERVISORS_SECRET"
echo "root:$API_HYPERVISORS_SECRET" |chpasswd

echo "---> Starting sshd server..."
ssh-keygen -A
/usr/sbin/sshd -D -e -f /etc/ssh/sshd_config &

echo "---> Setting up hypervisor certificates from api..."
python3 /src/lib/hypervisor.py setup
chmod 440 /etc/pki/libvirt-spice/*
chown qemu:root /etc/pki/libvirt-spice/*

echo "---> Setting up hypervisor wg VPNc from api..."
python3 /src/lib/vpnc.py

echo "---> Setting up OpenVswitch over wg..."
sh -c "/src/ovs/setup.sh"

env > /tmp/env # This is needed by the dnsmasq-hook to get the envvars
# This is the route needed, should be added from above python script
#ip r a $WG_USERS_NET via ${WG_HYPER_NET_WG_PEER}

echo "---> Starting libvirt daemon..."
chown root:kvm /dev/kvm
/usr/sbin/virtlogd &
sleep 2
/usr/sbin/libvirtd &
sleep 1

#echo "---> Setting vlans..."
#sh -c "/src/vlans/vlans-discover.sh"

FILES=/etc/libvirt/qemu/networks/*
for f in $FILES
do
  filename=$(basename -- "$f")
  filename="${filename%.*}"
  if [ $filename != "autostart" ]; then
    echo "Activating network: $filename"
    /usr/bin/virsh net-start $filename
    /usr/bin/virsh net-autostart $filename
  fi
done

echo "---> Securing network connections from guests to dockers..."
# Block traffic from guests to other dockers
iptables -I FORWARD -o eth0 -d $(ip -o -4 addr show dev eth0 | awk '{print $4}') -j REJECT
# Block traffic from guests default isolated network to hypervisor itself
iptables -A INPUT -s 192.168.120.0/22  -d $DOCKER_NET.17 -j REJECT --reject-with icmp-port-unreachable
# Block traffic from guests shared network to hypervisor itself
iptables -A INPUT -s 192.168.124.0/22  -d $DOCKER_NET.17 -j REJECT --reject-with icmp-port-unreachable

echo "---> Applying custom BLACKLIST_IPTABLES rules"
BLACKLIST_IPTABLES=$(echo $BLACKLIST_IPTABLES | tr "," " ")
for BLACKLIST_IPTABLES in $BLACKLIST_IPTABLES
do
   echo "$BLACKLIST_IPTABLES"
   iptables -I FORWARD -d "$BLACKLIST_IPTABLES" -o eth0 -j REJECT --reject-with icmp-port-unreachable
done

echo "---> Checking hypervisor by creating/destroying test domain..."
virsh create /src/checks/domain.xml
virsh destroy domain

if [ -z "$HYPER_ENABLED" ] || [ "$HYPER_ENABLED" == "true" ]
then
  echo "---> Enabling hypervisor..."
  python3 /src/lib/hypervisor.py enable
else
  echo "---> NOT enabling hypervisor because HYPER_ENABLED envvar missing or not true."
fi

echo "---> HYPERVISOR READY <---"

while true
do
    ping -c 1 10.1.0.1 >/dev/null 2>&1
    if [[ $? -ne 0 ]]; then
        wg-quick down wg0  >/dev/null 2>&1
        wg-quick up wg0  >/dev/null 2>&1
    fi
    sleep 30 &
    wait $!
done

