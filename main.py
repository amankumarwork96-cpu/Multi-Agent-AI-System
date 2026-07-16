from workflow.graph import build_graph

DATASET_PATH = "data/WA_Fn-UseC_-Telco-Customer-Churn.csv"
USER_QUESTION = "What factors are driving customer churn?"

def print_dataset_profile(profile: dict) -> None:
    """Print the dataset profile in a readable, labeled format."""
    print("=" * 60)
    print("DATASET_PROFILE")
    print("=" * 60)
    print(f"Rows: {profile['rows']}")
    print(f"Columns: {profile['columns']}")
    print(f"Numerical columns: {','.join(profile['numerical_columns'])}")
    print(f"Categorical columns: {', '.join(profile['categorical_columns'])}")
    print(f"Binary columns: {', '.join(profile['binary_columns'])}")

    if profile["missing_values"]:
        print("Missing values")
        for col, pct in profile["missing_values"].items():
            print(f"    -{col}: {pct}%")
    else:
        print("Missing values: none")

    print(f"Target candidates: {', '.join(profile['target_candidates'])}")
    print()


def print_analysis_plan(plan: list[dict]) -> None:
    """Print the analysis plan as a numbered, readable list."""
    print("=" * 60)
    print("ANALYSIS PLAN")
    print("=" * 60)
    for i, task in enumerate(plan, start=1):
        print(f"{i}. {task['description']}")
    print()


def main() -> None:
    graph = build_graph()

    initial_state = {
        "dataset_path": DATASET_PATH,
        "user_question": USER_QUESTION,
    }

    result = graph.invoke(initial_state)

    print_dataset_profile(result["dataset_profile"])
    print_analysis_plan(result["analysis_plan"])


if __name__ == "__main__":
    main()