import pandas as pd
import json
from datetime import datetime
import time
from lib.api_handler import (reconcile, ReconciliationAPIError)

def prepare_invoices_for_api(file_path: str) -> list[dict] | None:
    """
    Helper function to load a CSV from a path and prepare it for the API.
    Returns the prepared list of invoice dictionaries, or None in case of error.
    """

    try:
        # load CSV assuming NO header
        df = pd.read_csv(file_path, sep=';', header=None, encoding='utf-8-sig')
        df.columns = ['ID', 'Customer', 'Supplier', 'Amount', 'Date']

        # ensure correct data types
        df['ID'] = df['ID'].astype(int)
        df['Customer'] = df['Customer'].astype(int)
        df['Amount'] = df['Amount'].astype(float)
        df['Date'] = pd.to_datetime(df['Date'])

        # convert to list of dictionaries
        invoice_list = df.to_dict(orient='records')

        # post-process for API requirements (Amount_Cents, stringify dates)
        for invoice in invoice_list:
            invoice['Amount_Cents'] = int(round(invoice['Amount'] * 100))

            if isinstance(invoice.get('Date'), pd.Timestamp):
                invoice['Date'] = invoice['Date'].isoformat(sep=' ')

        print(f"  -> Successfully loaded and prepared {len(invoice_list)} invoices from '{file_path}'.")
        return invoice_list

    except FileNotFoundError:
        print(f"  -> ERROR: File not found at '{file_path}'. Skipping this transfer.")
        return None

    except Exception as e:
        print(f"  -> ERROR: Unable to process file '{file_path}'. Details: {e}")
        return None


def run_complete_demo_workflow():
    """
    Demonstrates a complete and realistic client workflow:
    - Iterates through a list of bank transfers
    - Loads a different invoice file for each
    - Uses custom parameters for each reconciliation
    - Measures the time of the entire process
    """

    # this list simulates client input: each element is a separate reconciliation task
    transfer_tasks = [
        {
            "transfer_amount": 2051.00,
            "invoice_file": "../data/sample/test_invoices_a.csv",
            "tolerance": 0.0,
            "backtracking_threshold": 15
        },
        {
            "transfer_amount": 40000,
            "invoice_file": "../data/sample/test_invoices_b.csv",
            "tolerance": 0.0,
            "backtracking_threshold": 10
        }
    ]

    all_results = []

    print("=" * 60)
    print("=== STARTING COMPLETE RECONCILIATION WORKFLOW DEMO ===")
    print("=" * 60)

    # record start time
    start_time = time.time()
    print(f"Workflow started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # iterate through each task
    for i, task in enumerate(transfer_tasks):
        print(f"\n--- [TASK {i + 1}/{len(transfer_tasks)}] ---")

        # load the specific invoice file for this task
        invoices_for_this_request = prepare_invoices_for_api(task["invoice_file"])

        # if file loading fails, skip to next task
        if invoices_for_this_request is None:
            continue

        try:
            # call the service using standard parameter names
            reconciliation_result = reconcile(
                target_amount=task["transfer_amount"],
                invoices=invoices_for_this_request,
                tolerance=task["tolerance"],
                backtracking_threshold=task["backtracking_threshold"]
            )

            # store result and print it for immediate feedback
            print("\n  [INFO] Complete JSON response received from service:")
            print(json.dumps(reconciliation_result, indent=2, default=str))

            all_results.append(reconciliation_result)

        except ReconciliationAPIError as e:
            print(f"\n  [ERROR] API Call Failed for transfer {task['transfer_amount']}: {e}")
            all_results.append({
                "transfer_amount": task['transfer_amount'],
                "status": "API_ERROR",
                "details": str(e)
            })

    # record end time and calculate duration
    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 60)
    print("=== WORKFLOW COMPLETED ===")
    print(f"Workflow ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total execution time: {duration:.2f} seconds")
    print("=" * 60)

    # save the entire results list to a single large JSON file
    with open("final_workflow_report.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

    print("\nComplete report of all transactions saved to 'final_workflow_report.json'")


if __name__ == "__main__":
    # prerequisite: make sure kubectl port-forward is running in another terminal
    # kubectl port-forward svc/reconciliation-svc 8080:80

    run_complete_demo_workflow()
