# 🚀 AWS EC2 Deployment Guide — NovaWorks HR Copilot
> Complete step-by-step guide to deploying NovaWorks HR Copilot on **AWS Free Tier (Amazon EC2)**.

---

## 📋 Architecture Summary

```
Internet (User Browser)
         │ HTTP (Port 80)
         ▼
┌────────────────────────────────────────────────────────┐
│ Amazon EC2 Instance (Amazon Linux 2023 / t2.micro)     │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Docker Network: novaworks-hr-copilot_default     │  │
│  │                                                  │  │
│  │  ┌────────────────────┐    ┌──────────────────┐  │  │
│  │  │ novaworks-frontend │───>│ novaworks-backend│  │  │
│  │  │ (React + Nginx :80)│    │ (FastAPI :8000)  │  │  │
│  │  └────────────────────┘    └────────┬─────────┘  │  │
│  └─────────────────────────────────────┼────────────┘  │
│                                        ▼               │
│                               EBS Host Volume          │
│                               ├── novaworks.db (SQLite)│
│                               └── qdrant_data/ (Vectors)│
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ Step 1: Launch the AWS EC2 Instance

1. Log into the [AWS Management Console](https://console.aws.amazon.com/ec2).
2. Ensure you are in your desired region (e.g., **ap-south-1 (Mumbai)** or **us-east-1 (N. Virginia)**).
3. Navigate to **EC2** $\rightarrow$ Click **Launch Instance**.
4. Configure the instance settings:
   - **Name**: `novaworks-hr-copilot`
   - **Application and OS Images (AMI)**: `Amazon Linux 2023 AMI` *(Free tier eligible)*.
   - **Architecture**: `64-bit (x86)`.
   - **Instance Type**: `t2.micro` (or `t3.micro` depending on region) — *1 vCPU, 1 GiB Memory (Free tier eligible)*.
   - **Key Pair (login)**:
     - Click **Create new key pair** (or select an existing one).
     - Key pair name: `novaworks-key`
     - Key pair type: `RSA`
     - Private key file format: `.pem`
     - Download and save `novaworks-key.pem` to your local computer (e.g. in `Downloads` or `~/.ssh/`).
   - **Network Settings**:
     - Auto-assign public IP: **Enable**
     - Check: ✅ **Allow SSH traffic from** (`My IP` or `0.0.0.0/0`)
     - Check: ✅ **Allow HTTP traffic from the internet** (Port 80)
     - Check: ✅ **Allow HTTPS traffic from the internet** (Port 443)
   - **Configure Storage**:
     - `30 GiB` `gp3` *(Free tier allows up to 30 GB of EBS storage)*.
5. Click **Launch Instance**.
6. Wait 1–2 minutes until the **Instance State** changes to `Running` and copy the **Public IPv4 address** (e.g., `3.25.129.3`).

---

## 🔑 Step 2: Connect to the Instance via SSH

Open **PowerShell** (Windows) or **Terminal** (Mac/Linux) in the folder where your `.pem` file is saved:

```powershell
# (On Windows PowerShell)
ssh -i .\novaworks-key.pem ec2-user@<YOUR-EC2-PUBLIC-IP>
```

> If prompted: *"The authenticity of host can't be established. Are you sure you want to continue connecting?"*  
> Type **`yes`** and press **Enter**.

---

## 🐳 Step 3: Install Docker, Compose & Configure Swap Memory

Once connected to the EC2 terminal `[ec2-user@ip-... ~]$`, run these commands:

### 1. Install Docker and Git:
```bash
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

### 2. Install Docker Compose (Standalone Binary):
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/bin/docker-compose
sudo chmod +x /usr/bin/docker-compose
sudo cp /usr/bin/docker-compose /usr/local/bin/docker-compose
```

### 3. Create 2GB Swap Memory (Crucial for 1GB RAM instances):
*Swap space prevents out-of-memory crashes during container builds.*
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

---

## 📦 Step 4: Clone Code & Configure Environment Secrets

### 1. Clone the GitHub Repository:
```bash
git clone https://github.com/JananiJagadeesanDev/novaworks-hr-copilot.git
cd novaworks-hr-copilot
```

### 2. Create the Production Environment File (`backend/.env`):
Run this command block directly in the terminal:

```bash
cat << 'EOF' > backend/.env
DATABASE_URL=sqlite:///./novaworks.db
JWT_SECRET_KEY=b40ce81e5b653a142e173e66835d32bf48d90455702505b3452c942adbf7d82c
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

GOOGLE_API_KEY=your_google_ai_studio_key_here
EMBEDDING_MODEL=models/gemini-embedding-2
LLM_MODEL=gemini-3.1-flash-lite

QDRANT_URL=
QDRANT_API_KEY=
QDRANT_PATH=./qdrant_data
POLICY_COLLECTION=hr_policies

ENVIRONMENT=production
LLM_PROVIDER=google
EOF
```

---

## 🏗️ Step 5: Build and Launch Containers

### 1. Initialize SQLite Database File on Host:
```bash
touch backend/novaworks.db
chmod 666 backend/novaworks.db
```

### 2. Build the Docker Images:
```bash
sudo docker build -t novaworks-hr-copilot-backend ./backend
sudo docker build -t novaworks-hr-copilot-frontend ./frontend
```

### 3. Start Containers with Docker Compose:
```bash
sudo /usr/bin/docker-compose up -d
```

### 4. Verify Both Containers are Running:
```bash
sudo /usr/bin/docker-compose ps
```
*Expected Output:*
```text
NAME                 IMAGE                           COMMAND                  SERVICE    STATUS
novaworks-backend    novaworks-hr-copilot-backend    "uvicorn app.main:ap…"   backend    Up (healthy)
novaworks-frontend   novaworks-hr-copilot-frontend   "/docker-entrypoint.…"   frontend   Up
```

---

## 🌱 Step 6: Seed Database & Embed HR Policies

Run the seed script inside the running backend container to populate all tables and embed policies into Qdrant:

```bash
sudo docker exec -it novaworks-backend python seed.py
```

*Expected Output:*
```text
Seed complete.
  Departments     : 5
  Employees       : 7  (admin / 2 managers / 4 staff)
  HR Policies     : 8
  Skills          : 7
  Projects        : 2
  Tickets         : 2
  Announcements   : 3
  Job Histories   : 11
  Onboarding Tasks: 4
```

---

## 🌐 Step 7: Access Your Live Application

Open your browser and navigate to:
```text
http://<YOUR-EC2-PUBLIC-IP>
```

### Demo Login Accounts:
| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@novaworks.com` | `Admin@123` |
| **HR Manager** | `priya.sharma@novaworks.com` | `Manager@123` |
| **Engineering Manager** | `arjun.mehta@novaworks.com` | `Manager@123` |
| **Software Engineer** | `raj.kumar@novaworks.com` | `Employee@123` |

---

## 🔄 Day-to-Day Maintenance & Operations

### 1. How to Redeploy after a Code Push (GitHub $\rightarrow$ EC2)
Whenever you push new code to your GitHub repo and want to update your live EC2 app:

```bash
cd ~/novaworks-hr-copilot

# 1. Pull the latest commits from GitHub
git pull

# 2. Rebuild the updated Docker images
sudo docker build -t novaworks-hr-copilot-backend ./backend
sudo docker build -t novaworks-hr-copilot-frontend ./frontend

# 3. Recreate and start the containers with the new images
sudo /usr/bin/docker-compose down
sudo /usr/bin/docker-compose up -d

# 4. (Optional) Prune old dangling Docker images to save EC2 disk space
sudo docker image prune -f
```

---

### 2. Container Lifecycle Commands (Start, Stop, Restart)

| Action | Command | Description |
|---|---|---|
| **Start Services** | `sudo /usr/bin/docker-compose up -d` | Creates & starts containers in the background. |
| **Stop Services** | `sudo /usr/bin/docker-compose stop` | Pauses containers without removing them or networks. |
| **Resume Services** | `sudo /usr/bin/docker-compose start` | Resumes stopped containers. |
| **Shut Down Services** | `sudo /usr/bin/docker-compose down` | Stops and removes container instances & internal networks. |
| **Restart Everything** | `sudo /usr/bin/docker-compose restart` | Restarts both frontend and backend. |
| **Restart Backend Only** | `sudo /usr/bin/docker-compose restart backend` | Restarts only the FastAPI backend (e.g. after editing `.env`). |
| **Restart Frontend Only** | `sudo /usr/bin/docker-compose restart frontend` | Restarts only the Nginx frontend. |

---

### 3. Monitoring & Debugging

#### Check Container Status & Health:
```bash
sudo /usr/bin/docker-compose ps
```

#### Stream Live Logs in Real-Time:
```bash
# Stream logs for all services
sudo /usr/bin/docker-compose logs -f --tail 50

# Stream backend AI execution logs only
sudo docker logs -f --tail 50 novaworks-backend

# Stream frontend Nginx access/proxy logs only
sudo docker logs -f --tail 50 novaworks-frontend
```

#### Inspect Resource Usage (CPU & RAM):
```bash
sudo docker stats
```

---

### 4. Database & Vector Index Management

#### Run Database Reseed / Refresh:
```bash
sudo docker exec -it novaworks-backend python seed.py --force
```

#### Re-index HR Policies into Qdrant:
```bash
sudo docker exec -it novaworks-backend python ingest_policies.py
```

#### Open a Shell Inside the Backend Container:
```bash
sudo docker exec -it novaworks-backend /bin/bash
```

