# start.py
import random
from datetime import datetime
from typing import Any, Dict, List, Tuple


COL_ID = 'ID'
COL_AMOUNT = 'Amount'
COL_DATE = 'Date'
COL_AMOUNT_CENTS = 'Amount_Cents'
COL_CUSTOMER = 'Customer'
COL_SUPPLIER = 'Supplier'


def get_average_date(solution: List[Dict]) -> datetime:
    """Calculates the average date of invoices in a solution."""
    if not solution:
        return datetime.max
    timestamps = [f[COL_DATE].timestamp() for f in solution if isinstance(f.get(COL_DATE), datetime)]
    if not timestamps:
        return datetime.max
    return datetime.fromtimestamp(sum(timestamps) / len(timestamps))


def get_solution_id_hash(solution_tuple: Tuple[List[Dict], int]) -> int:
    """Creates a stable hash from the invoice IDs in a solution for tie-breaking."""
    if not solution_tuple or not solution_tuple[0]:
        return 0
    # sort thru IDs to ensure the hash is consistent regardless of the internal list order
    ids = sorted([inv[COL_ID] for inv in solution_tuple[0]])
    return hash(tuple(ids))


def find_exact_combinations(
        invoices: List[Dict],
        target_amount_cents: int,
        solution_limit: int,
        tolerance_cents: int = 0
) -> List[Tuple[List[Dict], int]]:
    """Finds all combinations of invoices that sum to a target amount within a tolerance.
    Uses backtracking to explore combinations efficiently."""
    candidates = sorted(
        [(f, f.get(COL_AMOUNT_CENTS, 0)) for f in invoices if f.get(COL_AMOUNT_CENTS, 0) > 0],
        key=lambda x: x[1], reverse=True
    )

    found_solutions = []

    def backtrack(start_index: int, remaining_target_cents: int, current_combination: List[Dict]):
        """Recursive backtracking function to find valid combinations."""
        if len(found_solutions) >= solution_limit: 
            return

        if -tolerance_cents <= remaining_target_cents <= tolerance_cents:
            current_sum_cents = target_amount_cents - remaining_target_cents
            found_solutions.append((list(current_combination), current_sum_cents))

        if start_index >= len(candidates) or remaining_target_cents < -tolerance_cents: 
            return
        
        for i in range(start_index, len(candidates)):
            invoice, amount_cents = candidates[i]

            if amount_cents > remaining_target_cents + tolerance_cents: 
                continue

            current_combination.append(invoice)

            backtrack(i + 1, remaining_target_cents - amount_cents, current_combination)
            current_combination.pop()

    backtrack(0, target_amount_cents, [])
    return found_solutions


def select_invoices_advanced_greedy(
        invoices: List[Dict],
        target_amount_cents: int
) -> Tuple[List[Dict], int, List[Dict]]:
    """Selects invoices using an advanced greedy approach that prioritizes
    larger invoices first, ensuring the total does not exceed the target amount."""
    if target_amount_cents <= 0:
        candidates = sorted(
            [f for f in invoices if f.get(COL_AMOUNT_CENTS, 0) > 0],
            key=lambda x: x.get(COL_AMOUNT_CENTS, 0), reverse=True
        )

    solution, current_sum_cents = [], 0
    used_ids = set()
    
    for invoice in candidates:
        if current_sum_cents + invoice.get(COL_AMOUNT_CENTS, 0) <= target_amount_cents:
            solution.append(invoice)
            current_sum_cents += invoice.get(COL_AMOUNT_CENTS, 0)
            used_ids.add(invoice.get(COL_ID))

    remaining_invoices = [f for f in candidates if f.get(COL_ID) not in used_ids]
    discrepancy_cents = target_amount_cents - current_sum_cents
    suggestions = []

    if discrepancy_cents > 0:
        suggestions = sorted(
            [f for f in remaining_invoices if f.get(COL_AMOUNT_CENTS, 0) <= discrepancy_cents],
            key=lambda x: x.get(COL_AMOUNT_CENTS, 0), reverse=True
        )[:5]

    return solution, current_sum_cents, suggestions


def select_solution_by_strategy(
        solution_list: List[Tuple[List[Dict], int]],
        strategy: str
) -> Tuple[List[Dict], int]:
    """
    Selects the best solution from a list based on a strategy, using robust
    tie-breaking to ensure a deterministic choice.
    """
    if not solution_list:
        return None  # return None if the list is empty

    if len(solution_list) == 1:
        return solution_list[0]

    if strategy == 'largest-first':
        # tie-break by sum, then bytable hash 
        key_func = lambda x: (len(x[0]), x[1], get_solution_id_hash(x))
        return sorted(solution_list, key=key_func, reverse=True)[0]

    if strategy == 'smallest-first':
        key_func = lambda x: (len(x[0]), x[1], get_solution_id_hash(x))
        return sorted(solution_list, key=key_func)[0]

    if strategy == 'oldest-first':
        # tie-break by paying off more invoices (desc), then by stable hash
        key_func = lambda x: (get_average_date(x[0]), -len(x[0]), get_solution_id_hash(x))
        return sorted(solution_list, key=key_func)[0]

    if strategy == 'youngest-first':
        # tie-break by paying off more invoices (desc), then by stable hash
        key_func = lambda x: (get_average_date(x[0]), len(x[0]), get_solution_id_hash(x))
        return sorted(solution_list, key=key_func, reverse=True)[0]

    if strategy == 'random':
        return random.choice(solution_list)

    return solution_list[0]  # fallback


def create_standardized_report(
        base_metadata: Dict,
        backtracking_solutions: List[Tuple[List[Dict], int]] = None,
        greedy_solution: Tuple[List[Dict], int, List[Dict]] = None
) -> dict:
    """
    Creates the final, standardized JSON report by assigning a UNIQUE solution
    to each strategy slot based on a priority order. Once a solution is used,
    it cannot be assigned to another strategy.
    """
    if backtracking_solutions is None: backtracking_solutions = []
    if greedy_solution is None: greedy_solution = ([], 0, [])

    # priority for picking. 'largest-first' gets first choice
    STRATEGY_PRIORITY = ['largest-first', 'oldest-first', 'smallest-first', 'youngest-first', 'random']
    # guaranteed final order in the JSON output
    STRATEGY_ORDER = STRATEGY_PRIORITY + ['greedy']

    def get_solution_id(solution: Tuple[List[Dict], Any]) -> frozenset:
        """Extracts a unique ID from the solution tuple, which is a frozenset of invoice IDs."""
        if not solution or not solution[0]: return frozenset()
        return frozenset(inv[COL_ID] for inv in solution[0])

    def format_solution(solution_tuple):
        """Formats a solution tuple into a standardized JSON object."""
        solution, sum_cents, *rest = solution_tuple
        suggestions = rest[0] if rest else []

        audit_trail = sorted(
            [{'ID': inv.get(COL_ID), 'Amount': round(inv.get(COL_AMOUNT, 0.0), 2),
              'Date': str(inv.get(COL_DATE)), 'Customer': inv.get(COL_CUSTOMER),
              'Supplier': inv.get(COL_SUPPLIER)} for inv in solution],
            key=lambda x: x['Amount'], reverse=True
        )

        obj = {
            "total_sum": round(sum_cents / 100.0, 2),
            "discrepancy": round(base_metadata['target_amount'] - (sum_cents / 100.0), 2),
            "paid_invoices_count": len(solution), "invoices_audit_trail": audit_trail
        }

        if suggestions:
            obj['discrepancy_suggestions'] = [{'ID': s.get(COL_ID), 'Amount': round(s.get(COL_AMOUNT, 0.0), 2)} for s in
                                              suggestions]
        return obj

    final_solutions = {}
    claimed_solution_ids = set()
    print("\n--- DEBUG: Starting Solution Draft-Pick ---")

    if backtracking_solutions:
        for strategy in STRATEGY_PRIORITY:
            available = [sol for sol in backtracking_solutions if get_solution_id(sol) not in claimed_solution_ids]

            if not available:
                print(f"DEBUG: Strategy '{strategy}' found no available unique solutions.")
                continue

            best_choice = select_solution_by_strategy(available, strategy)

            if best_choice:
                solution_id = get_solution_id(best_choice)
                claimed_solution_ids.add(solution_id)
                final_solutions[strategy] = format_solution(best_choice + ([],))

                print(
                    f"DEBUG: Strategy '{strategy}' claimed solution with {len(best_choice[0])} invoices (ID Hash: {get_solution_id_hash(best_choice)}).")

    # handle greedy solution
    if greedy_solution and greedy_solution[0]:
        greedy_id = get_solution_id(greedy_solution)

        if greedy_id not in claimed_solution_ids:
            print(f"DEBUG: Strategy 'greedy' claimed its unique solution.")
            final_solutions['greedy'] = format_solution(greedy_solution)

        else:
            print("DEBUG: Greedy solution was already found by a backtracking strategy. Discarding.")

    print("--- DEBUG: Draft-Pick Complete ---\n")

    # assemble final report, filling empty slots
    EMPTY_SOLUTION = {"total_sum": 0.0, "discrepancy": base_metadata.get('target_amount', 0.0),
                      "paid_invoices_count": 0, "invoices_audit_trail": []}
    
    solutions_by_strategy_ordered = {
        strategy: final_solutions.get(strategy, EMPTY_SOLUTION)
        for strategy in STRATEGY_ORDER
    }

    # determine final status message
    unique_solutions_count = len({get_solution_id(sol) for sol in backtracking_solutions})

    if not backtracking_solutions and not (greedy_solution and greedy_solution[0]):
        status = "NO_SOLUTION_FOUND"

    elif unique_solutions_count > 1:
        status = f"AMBIGUITY_DETECTED ({unique_solutions_count} unique solutions found)"

    elif unique_solutions_count == 1:
        status = "UNIQUE_SOLUTION_FOUND"

    else:
        status = "GREEDY_SOLUTION_FOUND"

    return {
        "metadata": base_metadata,
        "status": status,
        "solutions_by_strategy": solutions_by_strategy_ordered
    }