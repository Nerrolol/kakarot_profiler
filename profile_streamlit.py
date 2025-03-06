import streamlit as st
from kakarot_profiler.core import calc_final_profiling

def main():
    trace_file = "data/trace.csv"
    program_file = "data/program.json"

    st.title("Kakarot Profiling Results")

    grouped_metrics, percent_with_debug = calc_final_profiling(trace_file, program_file)

    st.write(f"Percentage of mapped PCs: **{percent_with_debug:.2f}%**")

    for func, metric in grouped_metrics.items():
        st.subheader(f"{func}")
        st.write(f"""
        - **Total Steps:** {metric['total_steps']}
        - **Inner Steps:** {metric['inner_steps']}
        - **Nested Steps:** {metric['nested_steps']}
        - **Call Count:** {metric['call_count']}
        """)


if __name__ == "__main__":
    main()
