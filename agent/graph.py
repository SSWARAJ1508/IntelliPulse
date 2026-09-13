from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes import classify_question, retrieve_monitoring_context, generate_response

def build_graph(llm):
    workflow = StateGraph(AgentState)
    
    # Wrap nodes to inject LLM
    def node_classify(state): return classify_question(state, llm)
    def node_retrieve(state): return retrieve_monitoring_context(state)
    def node_generate(state): return generate_response(state, llm)
    
    workflow.add_node("classify", node_classify)
    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("generate", node_generate)
    
    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()
