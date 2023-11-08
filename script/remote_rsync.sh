#!/bin/bash
# extra="--delete --dry-run"
extra="--delete"

logthis() {
   # Log on file:
   echo "[INFO] $(date): $@" >> /backup/usb/remote_log.txt

   # Log on screen:
   echo "[INFO] $(date): $@"
}

# -----------------------------------------------------------------------------
# Parameters:
# -----------------------------------------------------------------------------
mp1=bddacd5f-6897-4cbc-bcd2-c9f30b13cb79
mp2=b81f4dca-53ab-4e6e-a4ee-c49d3b738939
# mp2=7c1425dd-4a70-4977-bd8d-cc9ee705383d  todo verify if is correct MP2

mount_point=/backup/usb/remote
test_file=${mount_point}/whoami.remote

# -----------------------------------------------------------------------------
# Mount operation:
# -----------------------------------------------------------------------------
mount -U ${mp1} ${mount_point}

if [ -f ${test_file} ]
then
    echo "Use mount point 1"
else
    echo "Mount point 1 not found, checking 2 ..."
    mount -U ${mp2} ${mount_point}

    if [ -f ${test_file} ]
    then

        echo "Use mount point 2"
    else
        echo "Error no mount point is valid! (send mail?)"
        exit 1
    fi
fi

# -----------------------------------------------------------------------------
# Update module:
# -----------------------------------------------------------------------------
cd /backup/git
git pull

# Backup operations:
# -----------------------------------------------------------------------------
logthis 1. START Backup Rsync Mexal Folders
destination=${mount_point}/files/mexal
mkdir -p ${destination}
rsync -avh ${extra} /backup/files/mexal/0/ ${destinatiom}
logthis 1. STOP Backup Rsync Mexal Folders

logthis 2. START Backup Snap Samba server
destination=${mount_point}/files/snapsamba
mkdir -p ${destination}
rsync -avh ${extra} /backup/cluster/files/snap/0/ ${destination}
logthis 2. STOP Backup Snap Samba server

logthis 3. START Backup Proxmox Cluster dump
destination=${mount_point}/dump/cluster
mkdir -p ${destination}
rsync -avh ${extra} /backup/cluster/dump/ ${destination}
logthis 3. STOP Backup Proxmox Cluster dump

logthis 4. START Backup Proxmox Mirror dump
destination=${mount_point}/dump/mirror
mkdir -p ${destination}
rsync -avh ${extra} /backup/cluster/mirror/dump/ ${destination}
logthis 4. STOP Backup Proxmox Mirror dump

logthis 5. START Backup Proxmox .3 dump
destination=${mount_point}/dump/px.3
mkdir -p ${destination}
rsync -avh ${extra} /backup/cluster/proxmox11/dump/ ${destination}
logthis 5. STOP Backup Proxmox .3 dump

# logthis 6. START Backup Rsync Samba Folders
# rsync -avh ${extra} /backup/files/samba/0 ${base}/files/samba
# logthis 6. START Backup Rsync Samba Folders
# Note: Keep only SNAPSHOT folder (is complete)

# -----------------------------------------------------------------------------
# Closing operations:
# -----------------------------------------------------------------------------
umount -l  ${mount_point}
# todo send mail

cd /backup/logger
python ./send_mail.py "roberto.gatti@fiam.it" "Backup USB disco da cambiare" "Backup terminato, cambiare il disco USB esterno collegato al dispositivo HP Cube"
python ./send_mail.py "nicola.riolini@micronaet.com" "Backup USB disco da cambiare" "Backup terminato, cambiare il disco USB esterno collegato al dispositivo HP Cube"

