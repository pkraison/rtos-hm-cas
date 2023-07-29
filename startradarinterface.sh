#! /bin/bash


echo "Establishing connection with Radar in Real Time Mode"
sudo putty /dev/ttyUSB0 -serial -sercfg 115200
sleep 2

while true
do 
	sleep 1
done
