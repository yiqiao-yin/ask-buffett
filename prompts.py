import streamlit as st
import openai
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS, Pinecone
from langchain.prompts.prompt import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ChatVectorDBChain # for chatting with the pdf
#from langchain.chains import ConversationalRetrievalChain
import pinecone
# 

TEMPLATE = """ You are an expert SQL developer querying about financials statements. You have to write sql code in a Snowflake database based on the following question. 
display the sql code in the SQL code format (do not assume anything if the column is not available, do not make up code). 
ALSO if you are asked to FIX the sql code, then look what was the error and try to fix that by searching the schema definition.
If you don't know the answer, provide what you think the sql should be. Only include the SQL command in the result.

The user will request for instance what is the last 5 years of net income for Johnson and Johnson. The SQL to generate this would be:

select year, net_income
from financials.prod.income_statement_annual
where ticker = 'JNJ'
order by year desc
limit 5;

Questions about income statement fields should query financials.prod.income_statement_annual
Questions about balance sheet fields (assets, liabilities, etc.) should query  financials.prod.balance_sheet_annual
Questions about cash flow fields (operating cash, investing activities, etc.) should query financials.prod.cash_flow_statement_annual

The financial figure column names include underscores _, so if a user asks for free cash flow, make sure this is converted to FREE_CASH_FLOW. 
Some figures may have slightly different terminology, so find the best match to the question. For instance, if the user asks about Sales and General expenses, look for something like SELLING_AND_GENERAL_AND_ADMINISTRATIVE_EXPENSES

If the user asks about multiple figures from different financial statements, create join logic that uses the ticker and year columns.
The user may use a company name so convert that to a ticker.

Question: {question}
Context: {context}

SQL: ```sql ``` \n
 
"""
QA_PROMPT = PromptTemplate(input_variables=["question", "context"], template=TEMPLATE, )

llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0.1,
    max_tokens=1000, 
    openai_api_key=st.secrets["openai_key"]
)

embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["openai_key"])
vectorstore = FAISS.load_local("faiss_index", embeddings)

qa_chain = RetrievalQA.from_chain_type(llm,
                                       retriever=vectorstore.as_retriever(),
                                       chain_type_kwargs={"prompt": QA_PROMPT})

def execute_chain(query):
    '''
    Execute the chain and handle error recovery.
    
    Args:
        query (str): The query to be executed

    Returns:
        chain_result (dict): The result of the chain execution

    '''
    chain_result = None
    try:
        chain_result = qa_chain({"query": question})
    except Exception as error:
        print("error", error)
    return chain_result['result']


def get_chain(vectorstore):
    """
    pull the chain for enabling chat with the vector database.
    """
    
    chain = RetrievalQA.from_chain_type(
                llm=lm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(),
                chain_type_kwargs=chain_type_kwargs,
                )
    return chain

def load_chain():
    '''
    Load the chain from the local file system

    Returns:
        chain (Chain): The chain object

    '''

    embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["openai_key"])
    vectorstore = FAISS.load_local("faiss_index", embeddings)
    return get_chain(vectorstore)

# chain = load_chain()

"""
def execute_chain(query):
    '''
    Execute the chain and handle error recovery.
    
    Args:
        query (str): The query to be executed

    Returns:
        chain_result (dict): The result of the chain execution

    '''
    chain_result = None
    try:
        chain_result = chain(query)
    except Exception as error:
        print("error", error)
    return chain_result
"""


# pinecone interactions

def pinecone_search():
    """
    perform a doc search in pinecone
    """
    pinecone.init(
        api_key=st.secrets['pinecone_key'], 
        environment=st.secrets['pinecone_env'] 
        )

    index_name = "buffett"
    embeddings = OpenAIEmbeddings(openai_api_key=st.secrets["openai_key"])
    docsearch = Pinecone.from_existing_index(index_name,embeddings)
    return docsearch

def pdf_question(query, temperature=.1,model_name="gpt-3.5-turbo"):
    pdf_qa = ChatVectorDBChain.from_llm(OpenAI(temperature=temperature, model_name=model_name, openai_api_key=st.secrets["openai_key"]),
                    pinecone_search(), return_source_documents=True)
    return pdf_qa({"question": query, "chat_history": ""})
