from langchain_community.vectorstores import FAISS
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss


class ToolRegistry:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-2-preview")
        self.vector_store = FAISS(self.embeddings, index=faiss.IndexFlatL2(len(self.embeddings.embed_query("hello world"))), docstore=InMemoryDocstore({}), index_to_docstore_id={})

    def register_tools(self, tools: list[str]):
        docs = [Document(page_content=tool) for tool in tools]
        self.vector_store.add_documents(docs)
        print("Loaded tools into vector store.")

    def search_tools(self, query: str, k: int = 5) -> list[str]:
        results = self.vector_store.similarity_search(query, k=k)
        return [result.page_content for result in results]


tool_registry = None


def get_tool_registry() -> ToolRegistry:
    global tool_registry
    if tool_registry is None:   
        tool_registry = ToolRegistry()
    return tool_registry
