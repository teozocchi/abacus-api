import os
import requests
import json

DEFAULT_URL = "http://localhost:8080/reconcile"
RECONCILIATION_SERVICE_URL = os.environ.get("RECO_SERVICE_URL", DEFAULT_URL)

class ReconciliationAPIError(Exception):
    pass

def reconcile(
        target_amount: float,
        invoices: list[dict],
        backtracking_threshold: int = None,
        tolerance: float = None,
        timeout_seconds: int = 60
) -> dict:
    """
    Executes a stateless reconciliation and includes debug printing of the JSON payload.
    """

    print(
        f"INFO: Preparing stateless request for {target_amount} with {len(invoices)} invoices.")

    payload = {
        'target_amount': target_amount,
        'invoices': invoices
    }

    if backtracking_threshold is not None:
        payload['backtracking_threshold'] = backtracking_threshold

    if tolerance is not None:
        payload['tolerance'] = tolerance

    try:
        # manually serialize the payload to a JSON string
        json_to_send = json.dumps(payload, default=str)
        print("\nDEBUG: About to send this exact JSON string over the network:")

        # print first 700 characters to avoid floding the terminal
        print(json_to_send[:700] + ("..." if len(json_to_send) > 700 else ""))
        print("-" * 20)

    except Exception as e:
        # if JSON conversion fails, we'll know
        print(f"DEBUG: Failed to serialize payload to JSON. Error: {e}")
        raise ReconciliationAPIError(f"Unable to create JSON for request: {e}")
    # --------------------------------

    try:
        # send the manually serialized JSON string, specifying the correct header
        response = requests.post(
            RECONCILIATION_SERVICE_URL,
            data=json_to_send,
            headers={'Content-Type': 'application/json'},
            timeout=timeout_seconds
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise ReconciliationAPIError(f"API request failed: {e}")