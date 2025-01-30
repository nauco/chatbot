import streamlit as st
import dotenv
import boto3

import os
import random
import json

dotenv.load_dotenv()

# Reference: https://docs.streamlit.io/knowledge-base/tutorials/build-conversational-apps
st.title('Chat Bot Demo')
st.subheader("Powered by Amazon Berock with Anthropic Claude v2",
             divider="rainbow")


@st.cache_data
def get_welcome_message() -> str:
    return random.choice(
        [
            "Hello there! How can I assist you today?",
            "Hi there! Is there anything I can help you with?",
            "Do you need help?",
        ]
    )


@st.cache_resource
def get_bedrock_client():
    return boto3.client(service_name='bedrock-runtime', region_name='ap-northeast-2')


def get_history() -> str:
    hisotry_list = [
        f"{record['role']}: {record['content']}" for record in st.session_state.messages
    ]
    return '\n\n'.join(hisotry_list)


client = get_bedrock_client()
modelId = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
accept = 'application/json'
contentType = 'application/json'


welcome_message = get_welcome_message()
with st.chat_message('assistant'):
    st.markdown(welcome_message)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    display_role = 'user'
    if message['role'] == 'Assistant':
        display_role = 'assistant'

    with st.chat_message(display_role):
        st.markdown(message["content"])


def parse_stream(stream):
    full_response = ""
    for event in stream:
        chunk = event.get('chunk')
        if chunk:
            message = json.loads(chunk.get("bytes").decode())
            if message['type'] == "content_block_delta":
                yield message['delta']['text'] or ""
            elif message['type'] == "message_stop":
                return "\n"
    st.session_state.messages.append(
        {"role": "Assistant", "content": full_response}
    )


if prompt := st.chat_input("What's up?"):
    st.session_state.messages.append({"role": "Human", "content": prompt})
    with st.chat_message("Human"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        history = get_history()
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }
        )
        response = client.invoke_model_with_response_stream(
            body=body,
            modelId=modelId,
        )
        stream = response.get('body')
        if stream:
            # st.write_stream is introduced in streamlit v1.31.0
            st.write_stream(parse_stream(stream))


if DEBUG := os.getenv("DEBUG", False):
    st.subheader("History", divider="rainbow")
    history_list = [
        f"{record['role']}: {record['content']}" for record in st.session_state.messages
    ]
    st.write(history_list)
