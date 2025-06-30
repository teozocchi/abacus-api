# abacus-api - a hybrid financial reconciliation engine

**version:** 1.0  
**author:** Matteo Zocchi

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/downloads/release/python-310/)
[![Flask](https://img.shields.io/badge/Flask-2.x-black.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-20.10-blue.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.25-blue.svg)](https://kubernetes.io/)

---

## 1. Project Overview

abacus-api is a high-performance, containerized web service designed to solve a complex **financial reconciliation problem**. Given a single payment (`bonifico`), it intelligently searches through a large set of invoices (`fatture`) to find the exact combination that sums up to the payment amount.
This project was conceived to tackle a computationally "impossible" NP-hard problem (subset sum) in order to transform it from a manual, multi-hour process into an automated task that completes in seconds.

### 1.1. Key Features

*   **Hybrid Algorithmic Core:** Intelligently switches between a perfect, **exact backtracking algorithm** for small, solvable datasets and a fast, reliable **greedy heuristic** for larger ones.
*   **Business-Aware Logic:** Includes sophisticated features like credit note (`nota di credito`) netting and an ambiguity resolver that selects the most plausible solution among multiple perfect matches.
*   **Stateless, Scalable Architecture:** Built as a stateless Flask API, containerized with Docker, and designed for orchestration with Kubernetes, this allowing for horizontal scalability.
*   **High-Performance Runtime:** Leverages the **PyPy** Just-in-Time (JIT) compiler for significant performance gains on the computationally intensive core logic.

### 1.2. System Architecture

The system follows a modern, decoupled client-server model designed for cloud-native deployment.

---

## 2. Technical Deep Dive

The core of abacus-api is its **triage system**. Before attempting to solve the reconciliation, the engine first analyzes the complexity of the request:

1.  **Complexity Check:** It counts the number of candidate invoices.
2.  **Strategy Selection:**
    *   If the count is below a configurable threshold (`backtracking_threshold`), it deploys the **exact backtracking solver**, which guarantees a mathematically perfect solution.
    *   If the count exceeds the threshold, it falls back to the **greedy heuristic solver**, which provides a fast and highly plausible business solution.

This hybrid approach ensures both **accuracy** when possible and **performance** when necessary.

---

## 3. Deployment Guide (Kubernetes)

This section covers the one-time setup required to get the Janus service running in a Kubernetes cluster.

### 3.1. Prerequisites

*   `kubectl` access to a Kubernetes cluster.
*   `docker` installed and running locally.
*   Credentials configured for a container registry (e.g., Docker Hub, GCR).

### 3.2. Step 1: Build & Push the Docker Image

1.  Navigate to the project's root directory.
2.  Build the Docker image, replacing `<your-registry>/<image-name>:<tag>` with your details.
    ```bash
    # Example: docker build -t my-dockerhub-user/abacus-api:v1.0 .
    docker build -t <your-registry>/<image-name>:<tag> .
    ```
3.  Push the image to the registry.
    ```bash
    # Example: docker push my-dockerhub-user/abacus-api:v1.0
    docker push <your-registry>/<image-name>:<tag>
    ```

### 3.3. Step 2: Configure and Deploy to Kubernetes

1.  Open `kubernetes/deployment.yaml` and update the `image` field to match the image you just pushed.
2.  Apply the Kubernetes manifests to the cluster.
    ```bash
    # Apply the Service to create a stable network endpoint
    kubectl apply -f kubernetes/service.yaml

    # Apply the Deployment to start the application pods
    kubectl apply -f kubernetes/deployment.yaml
    ```
3.  Verify that the deployment was successful:
    ```bash
    kubectl get pods -l app=abacus-api
    ```
    The pods should have a `STATUS` of `Running`.

---

## 4. How to Use (Client-Side Workflow)

This is the standard procedure for running a new batch of reconciliations.

1.  **Establish a Local Connection (Port Forwarding)**  
    If running the client script from a machine outside the Kubernetes cluster, create a network tunnel. Open a dedicated terminal and leave this command running:
    ```bash
    kubectl port-forward svc/janus-api-service 8080:80
    ```

2.  **Execute the Demo Workflow**  
    In a separate terminal, navigate to the project root and run the client script. The provided `run_demo.py` demonstrates how to orchestrate a series of tasks.
    ```bash
    python client/run_demo.py
    ```
    The script will call the service for each task defined within it, dynamically passing the correct invoice dataset and parameters. The final, consolidated report will be saved to `final_workflow_report.json`.

---

## 5. Troubleshooting Guide

| Problem / Error                                     | Probable Cause                                                                          | Solution                                                                                                                               |
| --------------------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Build Error:** `no space left on device`          | The `.dockerignore` file is missing or not configured, causing large files (like `.venv`) to be copied into the image. | Ensure a comprehensive `.dockerignore` file exists in the project root.                                                            |
| **Build Error:** `Unknown compiler(s): [['cc']...`  | The `Dockerfile` is missing the command to install the C compiler required by `pandas`. | Ensure `RUN apt-get update && apt-get install -y build-essential` is present in the `Dockerfile` before the `pip install` command. |
| **Pod `CrashLoopBackOff`** with `ModuleNotFoundError` | A required Python package is not installed in the Docker image.                         | Verify that `requirements.txt` is complete. Re-run the full Docker build and push process (Step 3.2).                                 |
| **Client Error:** `Connection refused`              | The `kubectl port-forward` command is not running, or the client is using the wrong URL/port. | Ensure the `port-forward` command is active in a separate terminal before running the client script.                                 |
| **Client Error:** `TypeError: Timestamp...`         | The client is sending a `pandas.Timestamp` object, which is not valid JSON.             | Ensure the client script converts datetime objects to strings (e.g., with `.isoformat()`) before sending them in the API call.  |
