import streamlit as st
import pandas as pd
from PIL import Image
import os

from querif.analyze.clustering import semantic_cluster_dbpedia, plot_clusters
from querif.nl2sparql import generate_and_execute_query
from querif.nl2sparql.utils import configs
from querif.rdf_graph_builder import RDFGraphBuilder
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="querIF", page_icon="💬", layout="centered")

st.title("💬 NL 2 SPARQL")

# Sidebar controls
st.sidebar.header("⚙️ Settings")
config_key = st.sidebar.selectbox(
    "LLM Config", options=list(configs.keys()), index=0, help="Select the LLM configuration to use for query generation"
)

if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "stop_execution" not in st.session_state:
    st.session_state.stop_execution = False

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message.get("content", ""))
            # Show config and status badges
            config_used = message.get("config", "")
            status = message.get("status", "pending")
            status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⏳"
            if config_used:
                st.caption(f"{status_icon} **{config_used}** | Status: {status}")
        elif message.get("is_structured"):
            if "sparql" in message and message["sparql"]:
                with st.expander("📝 Generated SPARQL Query", expanded=True):
                    st.code(message["sparql"], language="sparql")
            if "results" in message:
                with st.expander("📊 Query Results", expanded=True):
                    if message["results"]:
                        st.dataframe(pd.DataFrame(message["results"]), use_container_width=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Analyse", key=f"analyze_{message.get('sparql', '')[:100]}"):
                                if "raw_json" in message:
                                    df_clustered = semantic_cluster_dbpedia(message["raw_json"])
                                    fig = plot_clusters(df_clustered)
                                    st.plotly_chart(fig, use_container_width=True)
                        with col2:
                            if st.button("📈 RDF Graph", key=f"graph_prev_{message.get('sparql', '')[:100]}"):
                                with st.spinner("Generating RDF graph..."):
                                    try:
                                        rdf_builder = RDFGraphBuilder()
                                        rdf_builder.build_from_results(message["sparql"], message["raw_json"], max_results=10)
                                        import time
                                        filename = f"rdf_graph_{int(time.time())}"
                                        rdf_builder.export_to_turtle(filename + ".ttl")
                                        
                                        # Create interactive Plotly visualization
                                        fig = rdf_builder.visualize_interactive(title="RDF Graph")
                                        if fig:
                                            st.success("✅ RDF Graph generated!")
                                            st.plotly_chart(fig, use_container_width=True, config={
                                                'responsive': True,
                                                'displayModeBar': True,
                                                'displaylogo': False,
                                                'modeBarButtonsToRemove': ['lasso2d']
                                            })
                                            
                                            with open(filename + ".ttl", "r") as f:
                                                turtle_content = f.read()
                                            st.download_button(
                                                label="⬇️ Download Turtle RDF",
                                                data=turtle_content,
                                                file_name=filename + ".ttl",
                                                mime="text/turtle"
                                            )
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
                    else:
                        st.warning("No results found.")
            if "error" in message:
                st.error(message["error"])
        else:
            st.markdown(message.get("content", ""))

user_input = st.chat_input("Ask something...")

if user_input:
    # Store user message with config (status will be updated after execution)
    user_message_index = len(st.session_state.messages)
    user_message = {"role": "user", "content": user_input, "config": config_key, "status": "pending"}
    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(user_input)
        st.caption(f"⏳ **{config_key}** | Status: pending")

    with st.chat_message("assistant"):
        # Create placeholder for stop button
        stop_placeholder = st.empty()

        with st.spinner("Processing your query..."):
            stop_placeholder.button("⏹️ Stop Execution", key="stop_btn", on_click=lambda: setattr(st.session_state, "stop_execution", True))

            if st.session_state.stop_execution:
                st.session_state.stop_execution = False
                # Update user message status to interrupted
                st.session_state.messages[user_message_index]["status"] = "interrupted"
                st.warning("Query execution interrupted.")
                st.session_state.messages.append({"role": "assistant", "is_structured": True, "error": "Query execution interrupted by user."})
                st.rerun()

            sparql_query, raw_results = generate_and_execute_query(prompt=user_input, config_key=config_key)

        # Remove stop button after execution
        stop_placeholder.empty()

        # Build structured message for storage
        message_data = {
            "role": "assistant",
            "is_structured": True,
            "raw_json": raw_results,
        }

        if sparql_query:
            message_data["sparql"] = sparql_query
            with st.expander("📝 Generated SPARQL Query", expanded=True):
                st.code(sparql_query, language="sparql")

            # Parse and display results
            if raw_results and "results" in raw_results:
                bindings = raw_results["results"].get("bindings", [])
                if bindings:
                    # Convert bindings to a cleaner format for display
                    results_data = []
                    for binding in bindings:
                        row = {k: v.get("value", "") for k, v in binding.items()}
                        results_data.append(row)

                    message_data["results"] = results_data
                    with st.expander("📊 Query Results", expanded=True):
                        st.dataframe(pd.DataFrame(results_data), use_container_width=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Analyse", key=f"analyze_new_{sparql_query[:50]}"):
                                df_clustered = semantic_cluster_dbpedia(raw_results)
                                fig = plot_clusters(df_clustered)
                                st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            if st.button("📈 RDF Graph", key=f"graph_new_{sparql_query[:50]}"):
                                with st.spinner("Generating RDF graph..."):
                                    try:
                                        rdf_builder = RDFGraphBuilder()
                                        rdf_builder.build_from_results(sparql_query, raw_results, max_results=10)
                                        
                                        import time
                                        filename = f"rdf_graph_{int(time.time())}"
                                        
                                        rdf_builder.export_to_turtle(filename + ".ttl")
                                        
                                        # Create interactive Plotly visualization
                                        fig = rdf_builder.visualize_interactive(title="RDF Graph")
                                        if fig:
                                            st.success("✅ RDF Graph generated successfully!")
                                            st.plotly_chart(fig, use_container_width=True, config={
                                                'responsive': True,
                                                'displayModeBar': True,
                                                'displaylogo': False,
                                                'modeBarButtonsToRemove': ['lasso2d']
                                            })
                                            
                                            with open(filename + ".ttl", "r") as f:
                                                turtle_content = f.read()
                                            st.download_button(
                                                label="⬇️ Download Turtle RDF",
                                                data=turtle_content,
                                                file_name=filename + ".ttl",
                                                mime="text/turtle"
                                            )
                                    except Exception as e:
                                        st.error(f"❌ Error generating RDF graph: {str(e)}")
                else:
                    message_data["results"] = []
                    with st.expander("📊 Query Results", expanded=True):
                        st.warning("No results found.")
            else:
                message_data["results"] = []
                with st.expander("📊 Query Results", expanded=True):
                    st.warning("No results returned from query execution.")
            
            # Update user message status to success
            st.session_state.messages[user_message_index]["status"] = "success"
        else:
            message_data["error"] = "Failed to generate a SPARQL query for your input. Please try rephrasing."
            st.error(message_data["error"])
            # Update user message status to failed
            st.session_state.messages[user_message_index]["status"] = "failed"

        st.session_state.messages.append(message_data)
        # Rerun to update the status display
        st.rerun()
