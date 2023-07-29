#! /bin/bash


echo "Restarting wired network"
sudo ifconfig eth0 down
#sudo ifconfig eth1 down
sleep 10
echo "setting IP addresses for LIDARs"
sudo ifconfig eth0 192.168.2.102 netmask 255.255.255.0
sleep 5
#sudo ifconfig eth1 192.168.2.102 netmask 255.255.255.0

trap ctrl_c SIGINT

function ctrl_c(){
	echo "killing pids"
	kill $pids
	exit
}

source /opt/ros/foxy/setup.bash &
source /media/nvidia/ssd/home/nvidia/ros2f/install/setup.bash
ros2 launch velodyne velodyne-all-nodes-VLP16-launch.py &
pids="$!"
sleep 5

source /media/nvidia/ssd/home/nvidia/tirtos/install/setup.bash
ros2 run pointcloud_generation cloud &
pids="$pids $!"
sleep 2

while true
do 
	sleep 1
done
