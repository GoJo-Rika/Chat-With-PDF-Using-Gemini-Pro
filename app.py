import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
import time ## to check the response speed

from dotenv import load_dotenv
load_dotenv() ## Loading all the environment variables

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, 
                                                   chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectore_store = FAISS.from_texts(texts=text_chunks, 
                                     embedding=embeddings)
    vectore_store.save_local("faiss_index")

def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, 
    if the answer is not in provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="models/gemini-2.0-flash-lite", 
                                   temperature=0.3)

    prompt = PromptTemplate(template=prompt_template, 
                            input_variables=["context", "question"])
    
    chain = load_qa_chain(llm=model, 
                          chain_type="stuff", 
                          prompt=prompt)
    
    return chain

def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    new_db = FAISS.load_local(folder_path="faiss_index", 
                              embeddings=embeddings,
                              allow_dangerous_deserialization=True)
    
    docs = new_db.similarity_search(query=user_question)

    chain = get_conversational_chain()
    
    start_time = time.process_time()
    response = chain(
        {"input_documents": docs, "question": user_question},
        return_only_outputs=True
    )
    print("Response time :", time.process_time() - start_time)
    
    st.write("Reply: ", response["output_text"])

def main():
    st.set_page_config(page_title="Chat PDF")

    st.header("Chat with PDF using Gemini💁")

    user_question = st.text_input("Ask a Question from the PDF Files")

    if user_question:
        user_input(user_question=user_question)

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF File(s) and click on the Submit & Process Button", 
                                    accept_multiple_files=True)
        
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs=pdf_docs)
                text_chunks = get_text_chunks(text=raw_text)
                get_vector_store(text_chunks=text_chunks)
                st.success("Done")

if __name__ == "__main__":
    main()
