import streamlit as st
import ollama

st.title("ChatGPT-like Chatbot")

# Set the Ollama model.
# NOTE: Ensure this model is installed via `ollama pull [model_name]`
OLLAMA_MODEL = "gpt-oss:20b" 

# Initialize chat history in Streamlit's session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("How can I help you?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response
    with st.chat_message("assistant"):
        # Use a placeholder to stream the response
        message_placeholder = st.empty()
        full_response = ""
        
        # Display the "thinking" status
        with st.spinner("Thinking..."):
            try:
                # Call Ollama chat API with streaming enabled
                response_stream = ollama.chat(model=OLLAMA_MODEL, messages=st.session_state.messages, stream=True)
                
                # Iterate through the stream to get chunks of the response
                for chunk in response_stream:
                    full_response += chunk['message']['content']
                    message_placeholder.markdown(full_response + "▌") # Add blinking cursor
                
                # Display the final response
                message_placeholder.markdown(full_response)
            
            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.error(f"Please ensure that the '{OLLAMA_MODEL}' model is installed and Ollama is running.")
            
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})