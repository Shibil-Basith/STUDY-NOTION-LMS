
# StudyNotion LMS - Cloud & DevOps Architecture Documentation

**Project Name:** StudyNotion LMS
**Architecture:** Cloud-Native, GreenOps Compliant, AI-Monitored
**Deployment Platform:** Red Hat OpenShift
**Database:** MongoDB Atlas (Cloud)

-----

## **1. Executive Summary**

This document details the architectural transformation of the StudyNotion Learning Management System. The project was migrated from a local monolithic setup to a distributed, cloud-native architecture. Key enhancements include containerization via Docker, orchestration via OpenShift, automated CI/CD pipelines, sustainable "GreenOps" resource management, and AI-driven operational monitoring ("AIOps").

-----

## **2. Database Migration (MongoDB Atlas)**

**Objective:** Move data storage from local development (`localhost`) to a managed cloud cluster to support a distributed application accessible from the public internet.

### **Configuration**

  * **Provider:** MongoDB Atlas (Cloud)
  * **Cluster Strategy:** Shared Cluster with Logical Partitioning.
  * **Connection String Logic:** We appended `/StudyNotion` to the connection string. This instructs MongoDB to create a specific, isolated database for this application, preventing data collisions with other projects.

### **Code Implementation**

**File:** `backend/config/database.js`

```javascript
const mongoose = require("mongoose");
require("dotenv").config();

exports.connectDB = () => {
    // connect using the Environment Variable injected by OpenShift Secrets
    mongoose.connect(process.env.MONGODB_URL, {
        useNewUrlParser: true,
        useUnifiedTopology: true,
    })
    .then(() => console.log("✅ Database connected successfully"))
    .catch((error) => {
        console.log("❌ DB Connection Failed");
        process.exit(1); // Critical failure: Stop server if DB is unreachable
    });
};
```

-----

## **3. Backend Security & Cross-Domain Configuration**

**Objective:** Enable secure communication between the Frontend (hosted on one domain) and the Backend (hosted on a different domain) over HTTPS.

### **CORS (Cross-Origin Resource Sharing)**

**File:** `backend/server.js`
Standard browser security blocks requests between different domains. We configured the backend to explicitly trust the OpenShift Frontend Route.

```javascript
const cors = require("cors");
// ...
app.use(
    cors({
        // ⚠️ CRITICAL: We strictly allow only the specific Frontend URL.
        // Wildcards ("*") are insecure and block cookies.
        origin: "https://studynotion-frontend-route-shibilbasithcp-dev.apps.rm2.thpm.p1.openshiftapps.com",
        credentials: true // Allows session cookies (JWT) to be passed
    })
);
```

### **Secure Cookie Management**

**File:** `backend/controllers/auth.js`
Since OpenShift enforces HTTPS, standard HTTP cookies are blocked by modern browsers. We updated the cookie settings during the Login controller execution.

```javascript
const cookieOptions = {
    expires: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000),
    httpOnly: true,     // Security: Prevents JavaScript (XSS) from reading the token
    secure: true,       // REQUIRED: Only sends cookie over HTTPS
    sameSite: "none",   // REQUIRED: Allows cookie to travel between Frontend domain and Backend domain
}
```

-----

## **4. Containerization Strategy (Docker)**

**Objective:** Package the application into lightweight, portable, and secure images.

### **A. Backend Dockerfile**

**File:** `backend/Dockerfile`
**Key Feature:** Security & Size.

```dockerfile
# 1. Base Image: Use Alpine Linux (GreenOps: Reduces image size by ~600MB)
FROM node:18-alpine

# 2. Set working directory
WORKDIR /app

# 3. Permissions: Create permission for the 'node' user to own this folder
RUN chown -R node:node /app

# 4. Security: SWITCH USER. OpenShift blocks 'root' users by default.
USER node

# 5. Caching: Copy package.json first to utilize Docker Layer Caching
COPY --chown=node:node package*.json ./

# 6. GreenOps: Install only production dependencies to save space
RUN npm ci --only=production

# 7. Copy Source Code
COPY --chown=node:node . .

# 8. Expose Port
EXPOSE 4000

# 9. Start Command
CMD ["npm", "start"]
```

### **B. Frontend Dockerfile**

**File:** `frontend/Dockerfile`
**Key Feature:** Multi-Stage Build & Nginx Optimization.

```dockerfile
# --- STAGE 1: BUILDER ---
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Compiles React code into static HTML/CSS/JS in 'dist' folder
RUN npm run build

# --- STAGE 2: RUNNER ---
# Use unprivileged Nginx (Runs as non-root for OpenShift security)
FROM nginxinc/nginx-unprivileged:alpine

# Copy ONLY the built files from Stage 1 (Discards node_modules, saving huge space)
COPY --from=build /app/dist /usr/share/nginx/html

# Open port 8080 (Standard for unprivileged Nginx)
EXPOSE 8080

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
```

### **C. AIOps Agent Dockerfile**

**File:** `aiops/Dockerfile`
A lightweight Python container to run the anomaly detection script.

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY monitor.py .
CMD ["python", "-u", "monitor.py"]
```

-----

## **5. Cloud Orchestration (OpenShift/Kubernetes)**

**Objective:** Manage deployment, scaling, self-healing, and networking.

### **A. Backend Deployment**

**File:** `openshift/backend.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: studynotion-backend
spec:
  replicas: 2  # High Availability: 2 copies ensure zero downtime during crashes
  selector:
    matchLabels:
      app: studynotion-backend
  template:
    metadata:
      labels:
        app: studynotion-backend
    spec:
      containers:
      - name: backend
        image: shibilbasithcp/studynotion-backend:latest
        ports:
        - containerPort: 4000
        
        # SECRETS INJECTION:
        # Automatically loads MONGODB_URL, JWT_SECRET, etc.
        envFrom:
        - secretRef:
            name: backend-secrets
            
        # GREENOPS (Carbon Budget):
        # Strict limits prevent "zombie" processes from wasting energy
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### **B. Routes (Public Networking)**

**File:** `openshift/frontend.yaml` & `openshift/backend.yaml`
We used OpenShift **Routes** to expose the services to the internet via HTTPS.

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: studynotion-frontend-route
spec:
  to:
    kind: Service
    name: frontend-service
  port:
    targetPort: 8080
  tls:
    termination: edge # Handles SSL/HTTPS automatically
```

-----

## **6. GreenOps (Sustainability Engineering)**

**Objective:** Reduce the carbon footprint of the software lifecycle.

1.  **Alpine Base Images:** Reduced container sizes significantly, lowering bandwidth usage and storage electricity costs.
2.  **Resource Requests/Limits:** Implemented a "Carbon Budget" in YAML files to ensure no pod consumes more CPU cycles than necessary.
3.  **Horizontal Pod Autoscaler (HPA):**
      * **File:** `openshift/hpa.yaml`
      * **Logic:** Automatically scales the backend down to **1 Pod** during idle times (nights/weekends) and scales up only when CPU usage hits 70%.

-----

## **7. AIOps (Artificial Intelligence for Operations)**

**Objective:** Automated system health monitoring using Machine Learning.

**File:** `aiops/monitor.py`

  * **Technology:** Python, Scikit-Learn.
  * **Algorithm:** `IsolationForest` (Unsupervised Anomaly Detection).
  * **Workflow:**
    1.  The agent runs inside the cluster.
    2.  It continuously pings the Backend API to measure latency.
    3.  It trains a model on the last 50 data points in real-time.
    4.  If a request takes unusually long (statistical anomaly), it logs: `⚠️ [ANOMALY DETECTED]`.

-----

## **8. CI/CD Pipeline (GitHub Actions)**

**Objective:** Automate the Build, Test, and Deploy process.

**File:** `.github/workflows/openshift-deploy.yml`

  * **Trigger:** Push to `main`.
  * **Jobs:**
    1.  **Checkout:** Get code.
    2.  **Docker Build:** Build Backend, Frontend, and AIOps images.
    3.  **Docker Push:** Push images to Docker Hub registry.
    4.  **OpenShift Login:** Authenticate using `oc` CLI.
    5.  **Deploy:** Run `oc apply -f openshift/` to update the cluster.
    6.  **Rollout:** Force restart pods to pull the new images.

-----

## **9. Frontend API Configuration (Vite)**

**Objective:** Connect the static React frontend to the dynamic Backend API.

**File:** `frontend/src/services/apis.js`
We updated the API configuration to point to the live OpenShift Backend Route instead of localhost.

```javascript
// Hardcoded to the OpenShift Backend Route for stability
const BASE_URL = "https://studynotion-backend-route-shibilbasithcp-dev.apps.rm2.thpm.p1.openshiftapps.com/api/v1";

// API Endpoints
export const endpoints = {
  LOGIN_API: BASE_URL + "/auth/login",
  SIGNUP_API: BASE_URL + "/auth/signup",
  // ...
}
```

-----

## **10. Secrets Management**

**Objective:** Zero-trust security for sensitive credentials.

  * **Method:** `.env` files are ignored by Git.
  * **Injection:** Secrets were uploaded directly to the OpenShift cluster using the CLI.
      * `oc create secret generic backend-secrets --from-env-file=backend/.env`
  * **Variables Stored:** `MONGODB_URL`, `JWT_SECRET`, `CLOUD_NAME`, `RAZORPAY_KEY`, `MAIL_PASS`.