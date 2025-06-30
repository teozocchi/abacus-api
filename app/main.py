# main.py
try:
    from flask import Flask, request, jsonify
    import sys
    from datetime import datetime
    # update imports to use the new standardized report creator
    from engine.core_logic import (
        find_exact_combinations,
        select_invoices_advanced_greedy,
        create_standardized_report
    )

except ImportError as e:
    print(f"FATAL: A required module is missing: {e}", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


@app.route('/reconcile', methods=['POST'])
def reconcile():
    data = request.get_json()
    if not data or 'target_amount' not in data or 'invoices' not in data:
        return jsonify({
            "error": "Request body must contain 'target_amount' and a list of 'invoices'"
        }), 400

    try:
        candidate_invoices = data['invoices']
        target_amount = float(data['target_amount'])

        # prepare and validate invoice data
        current_timestamp = datetime.now()
        for invoice in candidate_invoices:
            # add defaults for optional fields
            invoice.setdefault('ID', 0)
            invoice.setdefault('Customer', 0)
            invoice.setdefault('Supplier', 'N/A')

            # parse date strings, with a fallback
            date_str = invoice.get('Date')
            if isinstance(date_str, str):
                try:
                    invoice['Date'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    invoice['Date'] = current_timestamp
            elif 'Date' not in invoice:
                invoice['Date'] = current_timestamp

            # calculate cents amount
            invoice['Amount_Cents'] = int(round(float(invoice.get('Amount', 0.0)) * 100))

        backtracking_threshold = int(data.get('backtracking_threshold', 40))
        tolerance = float(data.get('tolerance', 2.0))

    except (ValueError, TypeError, KeyError) as e:
        return jsonify({"error": f"Invalid data in request body: {e}"}), 400

    print(f"Received stateless request for {target_amount} with {len(candidate_invoices)} invoices.")

    base_metadata = {
        'input_file': 'payload-data',
        'target_amount': target_amount,
        'backtracking_threshold': backtracking_threshold,
        'set_tolerance': tolerance,
        'execution_timestamp': datetime.now().isoformat()
    }

    final_json_report = None

    if len(candidate_invoices) <= backtracking_threshold:
        # Run Backtracking
        found_solutions = find_exact_combinations(
            candidate_invoices,
            int(round(target_amount * 100)),
            10,  # find up to 10 solutions for ambiguity
            int(round(tolerance * 100))
        )
        # the report function handles all cases: no solution, 1 solution, or many
        final_json_report = create_standardized_report(base_metadata, backtracking_solutions=found_solutions)
    else:
        # run greedy
        final_solution, total_cents, suggestions = select_invoices_advanced_greedy(
            candidate_invoices,
            int(round(target_amount * 100))
        )
        # the report function handles the greedy case
        final_json_report = create_standardized_report(base_metadata,
                                                       greedy_solution=(final_solution, total_cents, suggestions))

    return jsonify(final_json_report)


@app.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
