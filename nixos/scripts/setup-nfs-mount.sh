#!/bin/bash
# Setup NFS auto-mount for NixOS VM on macOS
# This script configures autofs to automatically mount the VM filesystem at /vm/mines

set -e

echo "=== NFS Auto-Mount Setup for NixOS VM ==="
echo

# Step 1: Get VM IP address
echo "Step 1: Getting VM IP address..."
VM_IP=$(ssh ghilston@mines 'hostname -I | awk "{print \$1}"' 2>/dev/null)

if [ -z "$VM_IP" ]; then
    echo "ERROR: Could not reach VM 'mines'. Make sure:"
    echo "  1. VM is running: 'just vm-start mines' or 'just vmsa mines'"
    echo "  2. You've deployed the NFS config: 'just fr mines'"
    echo "  3. SSH is working: 'ssh ghilston@mines'"
    exit 1
fi

echo "VM IP: $VM_IP"
echo

# Step 2: Create mount point using synthetic.conf (required for macOS root directories)
echo "Step 2: Creating mount point..."
if [ ! -d /vm ]; then
    # Add vm to synthetic.conf if not already there
    if ! grep -q "^vm" /etc/synthetic.conf 2>/dev/null; then
        echo "Adding 'vm' to /etc/synthetic.conf..."
        echo "vm" | sudo tee -a /etc/synthetic.conf > /dev/null
        echo "NOTE: You need to REBOOT your Mac for /vm to be created."
        echo "After reboot, run this script again."
        exit 0
    else
        echo "ERROR: 'vm' is in /etc/synthetic.conf but /vm doesn't exist."
        echo "Please reboot your Mac first, then run this script again."
        exit 1
    fi
else
    echo "/vm directory exists"
fi
echo

# Step 3: Create NFS auto_map file
echo "Step 3: Creating /etc/auto_nfs..."
# Remove if it exists as a directory
if [ -d /etc/auto_nfs ]; then
    sudo rmdir /etc/auto_nfs 2>/dev/null || sudo rm -rf /etc/auto_nfs
fi
echo "mines -fstype=nfs,rw,bg,hard,intr,tcp,noresvport $VM_IP:/home/ghilston" | sudo tee /etc/auto_nfs > /dev/null
echo "Created /etc/auto_nfs"
echo

# Step 4: Update auto_master
echo "Step 4: Updating /etc/auto_master..."
if ! grep -q "^/vm" /etc/auto_master 2>/dev/null; then
    echo "/vm /etc/auto_nfs" | sudo tee -a /etc/auto_master > /dev/null
    echo "Added /vm mount point to /etc/auto_master"
else
    echo "/vm mount point already exists in /etc/auto_master"
fi
echo

# Step 5: Restart autofs
echo "Step 5: Restarting autofs..."
sudo automount -vc
echo "Restarted autofs"
echo

# Step 6: Test the mount
echo "Step 6: Testing mount..."
echo "Triggering auto-mount by accessing /System/Volumes/Data/vm/mines..."
if ls /System/Volumes/Data/vm/mines > /dev/null 2>&1; then
    echo "✓ SUCCESS! VM filesystem mounted at /System/Volumes/Data/vm/mines"
else
    echo "✗ Mount test failed. Checking status..."
    mount | grep nfs || echo "No NFS mounts found"
    echo
    echo "Troubleshooting:"
    echo "  1. Check VM firewall is disabled in config"
    echo "  2. Verify NFS is running in VM: ssh ghilston@mines 'systemctl status nfs-server'"
    echo "  3. Test manual mount: sudo mount -t nfs -o noresvport $VM_IP:/home/ghilston /tmp/test"
    exit 1
fi

# Step 7: Create convenience symlink
echo
echo "Step 7: Creating convenience symlink..."
if [ -L ~/mines ]; then
    echo "Symlink ~/mines already exists"
elif [ -e ~/mines ]; then
    echo "WARNING: ~/mines exists but is not a symlink. Skipping symlink creation."
    echo "If you want the symlink, remove ~/mines first."
else
    ln -s /System/Volumes/Data/vm/mines ~/mines
    echo "Created symlink: ~/mines -> /System/Volumes/Data/vm/mines"
fi

echo
echo "=== Setup Complete ==="
echo "Mount point: /System/Volumes/Data/vm/mines"
echo "Convenience symlink: ~/mines"
echo "VM IP: $VM_IP"
echo
echo "The mount will:"
echo "  • Auto-mount when you access the path"
echo "  • Survive reboots (both host and guest)"
echo "  • Unmount automatically when not in use"
echo
echo "Access your VM files at:"
echo "  ~/mines/Git/toolbox/"
echo "  or"
echo "  /System/Volumes/Data/vm/mines/Git/toolbox/"
