from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import subprocess
import json

import os

# Set a writable KUBECONFIG path
os.environ["KUBECONFIG"] = "/tmp/kubeconfig"

app = FastAPI()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ALLOWS ALL ORIGINS (Use carefully)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure OpenShift login
def login_openshift():
    oc_token = "sha256~Rcb_mQTySEzbkyPeimqe55MD0RfBq6JLxufrGWqEjU8"  # Use OpenShift token
    oc_server = "https://api.rm3.7wse.p1.openshiftapps.com:6443"  # OpenShift API server
    if not oc_token or not oc_server:
        raise Exception("OCP_TOKEN and OCP_SERVER environment variables must be set!")
    
    login_cmd = f"oc login {oc_server} --token={oc_token} --insecure-skip-tls-verify"
    try:
        subprocess.run(login_cmd, shell=True, check=True)
        print("✅ OpenShift login successful!")
    except subprocess.CalledProcessError as e:
        print("❌ OpenShift login failed:", e)
        raise


def get_pod_metrics():
    """Fetch pod resource usage and status from OpenShift."""
    
    # Get CPU & memory usage
    resource_command = "oc adm top pods -n t4nm4y-dev --no-headers"
    status_command = "oc get pods -n t4nm4y-dev -o json"
    
    try:
        # Fetch resource metrics
        resource_output = subprocess.check_output(resource_command, shell=True, text=True)
        pod_resources = {}
        for line in resource_output.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                pod_resources[parts[0]] = {"cpu": parts[1], "memory": parts[2]}

        # Fetch pod status
        status_output = subprocess.check_output(status_command, shell=True, text=True)
        pod_data = json.loads(status_output)

        pods = []
        for pod in pod_data["items"]:
            name = pod["metadata"]["name"]
            status = pod["status"]["phase"]  # Running, Pending, CrashLoopBackOff, etc.
            restarts = sum(container["restartCount"] for container in pod["status"].get("containerStatuses", []))
            start_time = pod["status"].get("startTime", "")

            # Mark unhealthy pods
            unhealthy = status not in ["Running", "Succeeded"]
            slow = restarts > 2  # Example: Restart count > 2 means slow pod

            pods.append({
                "name": name,
                "cpu": pod_resources.get(name, {}).get("cpu", "0m"),
                "memory": pod_resources.get(name, {}).get("memory", "0Mi"),
                "status": status,
                "restarts": restarts,
                "unhealthy": unhealthy,
                "slow": slow
            })

        return pods

    except subprocess.CalledProcessError as e:
        print("❌ Error fetching pod data:", e)
        return []




@app.get("/")
def read_root():
    return {"message": "Welcome to OpenShift Monitoring API!"}

@app.get("/metrics")
def fetch_metrics():
    login_openshift()
    return {"pods": get_pod_metrics()}
