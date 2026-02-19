#!/usr/bin/env python3
import socket
import time
import hashlib
import os
import sys
import multiprocessing

# Trying to import requests, if we can't use urllib (standard in Python)
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import json
    HAS_REQUESTS = False

# --- config ---
username = "yourUserName" 
devicename = "yourMiningDeviceName"
mining_key = "yourMiningKey" 
cores = multiprocessing.cpu_count() 

def fetch_pools():
    url = "https://server.duinocoin.com/getPool"
    while True:
        try:
            if HAS_REQUESTS:
                response = requests.get(url).json()
                return response["ip"], response["port"]
            else:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    return data["ip"], data["port"]
        except:
            time.sleep(15)

def current_time():
    return time.strftime("%H:%M:%S", time.localtime())

def mine_worker(worker_id):
    """This function runs on its own core"""
    print(f"[{worker_id}] Worker started")
    
    while True:
        soc = None
        try:
            # Get pool-info
            try:
                NODE_ADDRESS, NODE_PORT = fetch_pools()
            except:
                NODE_ADDRESS, NODE_PORT = "server.duinocoin.com", 2813
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.connect((str(NODE_ADDRESS), int(NODE_PORT)))
            server_version = soc.recv(100).decode()
            
            while True:
                soc.send(bytes(f"JOB,{username},LOW,{mining_key}", encoding="utf8"))
                job_data = soc.recv(1024).decode().rstrip("\n")
                job = job_data.split(",")
                
                if len(job) < 3: 
                    continue
                
                expected_hash = job[1]
                difficulty = int(job[2])
                base_hash = hashlib.sha1(str(job[0]).encode("ascii"))
                
                hashingStartTime = time.time()
                
                # hashing HERE
                for result in range(100 * difficulty + 1):
                    temp_hash = base_hash.copy()
                    temp_hash.update(str(result).encode("ascii"))
                    ducos1 = temp_hash.hexdigest()

                    if expected_hash == ducos1:
                        timeDifference = time.time() - hashingStartTime
                        hashrate = result / timeDifference

                        # Send result
                        soc.send(bytes(f"{result},{hashrate},{username}-{devicename}-thread-{worker_id}", encoding="utf8"))
                        feedback = soc.recv(1024).decode().rstrip("\n")
                        
                        if feedback == "GOOD":
                            print(f"{current_time()} [{worker_id}]: Accepted share | {int(hashrate/1000)} kH/s")
                        break
        except Exception as e:
            print(f"Error in worker {worker_id}: {e}")
            if soc:
                soc.close()
            time.sleep(10)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    print(f"--- Starting Duino-Coin miner on {cores} cores ---")
    
    processes = []
    for i in range(cores):
        p = multiprocessing.Process(target=mine_worker, args=(i+1,))
        p.daemon = True # Killing extra processes if main is stopped
        p.start()
        processes.append(p)

    # Main program
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping miner...")