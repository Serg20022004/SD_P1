# SD P1: Scaling Distributed Systems

## Sergi Izquierdo Segarra - 48280130W (2024-2025)

This repository contains the solutions for Practical Assignment 1 (P1) for the Distributed Systems (Sistemes Distribuïts) course at Universitat Rovira i Virgili. The project implements two main services, an `InsultService` and an `InsultFilter` service, using four different communication middleware technologies: XMLRPC, Pyro4, Redis, and RabbitMQ. The project also includes performance analysis for these implementations.

## Project Structure

The repository is organized as follows:

*   **/docs**: Contains the final PDF report for the assignment.
*   **/xmlrpc_insult_service**: Implementation of InsultService using XMLRPC.
*   **/xmlrpc_filter_service**: Implementation of InsultFilter service using XMLRPC.
*   **/pyro_insult_service**: Implementation of InsultService using Pyro4.
*   **/pyro_filter_service**: Implementation of InsultFilter service using Pyro4.
*   **/redis_insult_service**: Implementation of InsultService using Redis.
*   **/redis_filter_service**: Implementation of InsultFilter service using Redis.
*   **/rabbitmq_insult_service**: Implementation of InsultService using RabbitMQ.
*   **/rabbitmq_filter_service**: Implementation of InsultFilter service using RabbitMQ.
*   **/stress_tests**: Scripts used for performance analysis (single-node, multi-node static scaling, and dynamic scaling tests).
*   `run_*.sh` scripts within each service folder are for basic demonstration of functionality.
*   `requirements.txt`: Lists the Python dependencies for this project.
*   `README.md`: This file.

## Environment Setup

1.  **Python:** Python 3.8 or higher.
2.  **Virtual Environment:** It is recommended to use a Python virtual environment.
    ```bash
    # Navigate to the project root (e.g., P1_Sistemes_Distribuits)
    python3 -m venv SD-env
    source SD-env/bin/activate 
    # On Windows: SD-env\Scripts\activate
    ```
3.  **Dependencies:** Install the required Python packages.
    ```bash
    pip install -r requirements.txt
    ```
4.  **External Services (Middleware Brokers/Servers):**
    *   **Redis:** A Redis server instance is required. It can be run using Docker:
        ```bash
        docker run --name my-redis -d -p 6379:6379 redis
        # To start an existing container: docker start my-redis
        ```
    *   **RabbitMQ:** A RabbitMQ server instance is required. It can be run using Docker:
        ```bash
        docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management
        # To start an existing container: docker start rabbitmq
        # Management UI: http://localhost:15672 (guest/guest)
        ```
    *   **Pyro4 Name Server:** For all Pyro4 services, the Pyro4 Name Server must be running in a dedicated terminal (with the virtual environment activated):
        ```bash
        python -m Pyro4.naming
        ```

## Running the Services and Demonstrations

Each service implementation (e.g., `xmlrpc_insult_service`, `pyro_filter_service`) contains its own set of Python scripts (server(s), client(s), worker(s), etc.) and a `run_*.sh` script for automated demonstration.

**General Instructions to run a specific service demonstration:**

1.  Ensure all prerequisites for the chosen middleware are met (e.g., Redis server running, Pyro Name Server running).
2.  Activate the virtual environment: `source SD-env/bin/activate`.
3.  Navigate to the specific service directory, for example:
    ```bash
    cd xmlrpc_insult_service
    ```
4.  Make the run script executable (one time only):
    ```bash
    chmod +x run_xmlrpc_insult_service.sh 
    ```
5.  Execute the run script:
    ```bash
    ./run_xmlrpc_insult_service.sh
    ```
This will typically open multiple terminal windows showcasing the server, client, and subscriber/worker interactions for that specific service and middleware.

Refer to the individual `run_*.sh` scripts or the "How to Run" sections in the PDF documentation for more detailed manual steps if preferred.

## Running Performance Tests

The performance test scripts are located in the `/stress_tests` directory.

1.  **Prerequisites:**
    *   Ensure the relevant middleware server (Redis, RabbitMQ, Pyro Name Server) is running.
    *   Ensure the specific service's server/dispatcher components are running (as per the "How to Run" section for that service, but generally the stress test scripts for static/dynamic scaling will manage starting their own worker instances).
    *   Activate the virtual environment: `source SD-env/bin/activate`.
    *   Navigate to the `stress_tests` directory: `cd stress_tests`.
    *   **Important:** Before running scaling tests, ensure the `PYTHON_EXECUTABLE` variable at the top of the `test_static_scaling_*.py` and `dynamic_scaler_rabbit.py` scripts is correctly set to the **absolute path** of the Python interpreter within your `SD-env` virtual environment (e.g., `/home/user/P1_Sistemes_Distribuits/SD-env/bin/python`).

2.  **Single-Node Performance Tests (Phase 1):**
    *   These scripts test throughput against a single server/worker instance with varying client concurrency.
    *   Example: `python stress_add_insult_xmlrpc.py`
    *   Run each of the 8 scripts in this category as needed. The output will be printed to the console.

3.  **Multi-Node Static Scaling Tests (Phase 2):**
    *   These scripts test throughput and calculate speedup with 1, 2, and 3 worker processes.
    *   Example: `python test_static_scaling_filter_redis.py`
    *   Run for Pyro4, Redis, and RabbitMQ versions of `InsultFilter`. The output summary includes execution time and speedup.

4.  **Multi-Node Dynamic Scaling Test (Phase 3 - RabbitMQ `InsultFilter`):**
    *   This demonstrates dynamic adjustment of worker processes based on queue load.
    *   Setup:
        1.  Terminal 1: RabbitMQ Server (Docker).
        2.  Terminal 2 (Optional): `cd ../rabbitmq_filter_service && python filter_results_collector_rabbit.py` (to observe results).
        3.  Terminal 3: `cd . && python dynamic_scaler_rabbit.py
        4.  Terminal 4 cd ../rabbitmq_filter_service && python dynamic_filter_producer_rabbit.py` (to generate variable load).
    *   Worker logs will be in `worker_X_log.txt`.

## Documentation

The full documentation, including design, architecture, performance analysis, plots, and conclusions, is available in the `/docs` directory (e.g., `P1_Report_Sergi_Izquierdo.pdf`).

---
