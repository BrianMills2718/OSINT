#!/usr/bin/env python3
"""
Investigate 30-Second Hang - Find out exactly what happens at 30-45 second mark
"""
import sys
import time
import signal
import subprocess
import threading
import psutil
import os
sys.path.insert(0, '/home/brian/projects/autocoder4_cc')

def monitor_process_during_hang():
    """Monitor what the process is doing during the 30-45 second hang period"""
    
    print("🔍 MONITORING PROCESS DURING 30-45 SECOND HANG")
    print("=" * 60)
    
    # Start the process
    cmd = ["python3", "autocoder_cc/cli/v2/main.py", "system", "Simple test system", "-o", "/tmp/hang_monitor"]
    
    print(f"🚀 Starting process: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        cwd='/home/brian/projects/autocoder4_cc',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"📊 Process PID: {process.pid}")
    
    # Monitor the process
    start_time = time.time()
    monitor_interval = 2  # Check every 2 seconds
    
    try:
        psutil_process = psutil.Process(process.pid)
        
        while True:
            elapsed = time.time() - start_time
            
            if process.poll() is not None:
                print(f"✅ Process completed after {elapsed:.1f}s")
                break
                
            if elapsed > 60:  # Give up after 60 seconds
                print(f"⏰ Stopping monitoring after {elapsed:.1f}s")
                process.terminate()
                break
            
            # Get process info
            try:
                cpu_percent = psutil_process.cpu_percent()
                memory_mb = psutil_process.memory_info().rss / 1024 / 1024
                status = psutil_process.status()
                
                # Get open files/connections
                open_files = len(psutil_process.open_files())
                connections = len(psutil_process.connections())
                
                # Get thread count
                num_threads = psutil_process.num_threads()
                
                print(f"⏱️ {elapsed:5.1f}s | CPU: {cpu_percent:5.1f}% | RAM: {memory_mb:6.1f}MB | Status: {status:12} | Files: {open_files:2} | Conn: {connections:2} | Threads: {num_threads:2}")
                
                # Check if it's in the critical 30-45s window
                if 25 <= elapsed <= 50:
                    # Get more detailed info during hang period
                    threads = psutil_process.threads()
                    print(f"    🔍 Critical period - Thread details: {len(threads)} threads")
                    
                    # Try to get stack trace if possible (Linux only)
                    try:
                        with open(f"/proc/{process.pid}/stack", 'r') as f:
                            stack = f.read().strip()
                            if stack:
                                print(f"    📚 Kernel stack:")
                                for line in stack.split('\n')[:3]:  # First 3 lines
                                    print(f"         {line.strip()}")
                    except:
                        pass
                        
            except psutil.NoSuchProcess:
                print(f"❌ Process ended unexpectedly at {elapsed:.1f}s")
                break
            except Exception as e:
                print(f"⚠️ Monitor error at {elapsed:.1f}s: {e}")
            
            time.sleep(monitor_interval)
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Monitoring interrupted by user")
        process.terminate()
        
    # Get final output
    try:
        stdout, stderr = process.communicate(timeout=5)
        
        print(f"\n📄 STDOUT (last 500 chars):")
        print(stdout[-500:] if stdout else "No stdout")
        
        print(f"\n📄 STDERR (last 500 chars):")
        print(stderr[-500:] if stderr else "No stderr")
        
    except subprocess.TimeoutExpired:
        print(f"\n⏰ Process didn't respond to terminate")
        process.kill()
        
    return process.returncode

def investigate_network_activity():
    """Check if hanging is related to network calls"""
    
    print("\n🌐 INVESTIGATING NETWORK ACTIVITY DURING HANG")
    print("=" * 60)
    
    # Use netstat to monitor network connections during process
    cmd = ["python3", "autocoder_cc/cli/v2/main.py", "system", "Test for network", "-o", "/tmp/network_test"]
    
    print(f"🚀 Starting process for network monitoring...")
    
    process = subprocess.Popen(
        cmd,
        cwd='/home/brian/projects/autocoder4_cc',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    start_time = time.time()
    
    # Monitor network connections
    initial_connections = set()
    try:
        psutil_process = psutil.Process(process.pid)
        initial_connections = set(str(conn) for conn in psutil_process.connections())
        print(f"📊 Initial connections: {len(initial_connections)}")
        
        while True:
            elapsed = time.time() - start_time
            
            if process.poll() is not None:
                print(f"✅ Process completed after {elapsed:.1f}s")
                break
                
            if elapsed > 50:
                print(f"⏰ Terminating after {elapsed:.1f}s")
                process.terminate()
                break
            
            # Check for new connections
            try:
                current_connections = set(str(conn) for conn in psutil_process.connections())
                new_connections = current_connections - initial_connections
                
                if new_connections:
                    print(f"⏱️ {elapsed:5.1f}s | New connections: {len(new_connections)}")
                    for conn in new_connections:
                        print(f"    🔗 {conn}")
                        
                # In critical period, monitor more closely
                if 25 <= elapsed <= 45:
                    print(f"⏱️ {elapsed:5.1f}s | Total connections: {len(current_connections)}")
                    
            except psutil.NoSuchProcess:
                break
            except Exception as e:
                print(f"⚠️ Network monitor error: {e}")
                
            time.sleep(3)
            
    except Exception as e:
        print(f"❌ Network monitoring failed: {e}")
        
    process.terminate()

if __name__ == "__main__":
    print("🎯 INVESTIGATING WHAT HAPPENS DURING 30-45 SECOND HANG")
    print("=" * 80)
    
    # Monitor process behavior
    monitor_process_during_hang()
    
    # Monitor network activity  
    investigate_network_activity()
    
    print("\n🎯 INVESTIGATION COMPLETE")
    print("Check the output above to see what the process is doing during the hang period")