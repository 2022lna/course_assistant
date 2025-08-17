import os
import uuid
from typing import List, Dict
from langchain.vectorstores import Chroma
from langchain.embeddings import DashScopeEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, CSVLoader
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate,MessagesPlaceholder
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv(r"课程助手/lna.env")
class RAGProcess:
    def __init__(self, persist_directory="课程助手/course_knowledge_base"):
        self.embeddings = DashScopeEmbeddings(
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        # 固定的本地课程知识库
        self.course_kb_path = os.path.join(persist_directory, "course_db")
        self.course_vector_store = self._init_course_kb()

        # 用户上传文档的存储路径
        self.upload_directory = "课程助手/user_uploads"
        self.user_kb_path = os.path.join(persist_directory, "user_db")
        self.user_vector_store = self._init_user_kb()

        # 确保目录存在
        os.makedirs(self.upload_directory, exist_ok=True)

    def _init_course_kb(self):
        """初始化课程知识库"""
        if os.path.exists(self.course_kb_path):
            return Chroma(persist_directory=self.course_kb_path,
                          embedding_function=self.embeddings)
        else:
            return Chroma(persist_directory=self.course_kb_path,
                          embedding_function=self.embeddings)

    def _init_user_kb(self):
        """初始化用户文档知识库"""
        if os.path.exists(self.user_kb_path):
            return Chroma(persist_directory=self.user_kb_path,
                          embedding_function=self.embeddings)
        else:
            return Chroma(persist_directory=self.user_kb_path,
                          embedding_function=self.embeddings)

    def load_course_documents(self, documents_path="./course_materials"):
        """加载课程文档到固定知识库"""
        documents = self._load_documents_from_directory(documents_path)
        split_docs = self.text_splitter.split_documents(documents)

        self.course_vector_store.add_documents(split_docs)
        self.course_vector_store.persist()

        return len(split_docs)

    def upload_document(self, file_path: str, user_id: str = "default") -> Dict:
        """用户上传文档并存储（带用户隔离）"""
        try:
            # 1. 加载文档
            documents = self._load_single_document(file_path)

            # 2. 处理文档元数据
            saved_paths = []
            for doc in documents:
                original_file = os.path.basename(file_path)
                upload_id = str(uuid.uuid4())
                doc.metadata.update({
                    'user_id': user_id,
                    'original_file': original_file,
                    'upload_id': upload_id,
                })
                saved_paths.append(original_file)

            # 3. 分割文档
            split_docs = self.text_splitter.split_documents(documents)

            # 4. 存储到用户知识库
            self.user_vector_store.add_documents(split_docs)
            self.user_vector_store.persist()

            # 5. 保存原始文件到 upload 目录
            filename = os.path.basename(file_path)
            new_filename = f"{user_id}_{uuid.uuid4()}_{filename}"
            save_path = os.path.join(self.upload_directory, new_filename)
            os.rename(file_path, save_path)

            return {
                'success': True,
                'document_count': len(split_docs),
                'saved_path': save_path,
                'uploaded_files': list(set(saved_paths)),
                'message': f'成功上传并处理文档: {", ".join(set(saved_paths))}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'文档上传失败: {str(e)}'
            }

    def _load_single_document(self, file_path: str):
        """加载单个文档"""
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        elif file_path.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        elif file_path.endswith('.csv'):
            loader = CSVLoader(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path}")

        return loader.load()

    def _load_documents_from_directory(self, directory_path: str) -> List:
        """从目录加载所有文档"""
        documents = []
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                try:
                    docs = self._load_single_document(file_path)
                    documents.extend(docs)
                except Exception as e:
                    print(f"加载文件 {filename} 时出错: {e}")
        return documents

    def hybrid_search(self, query: str, user_id: str = "default", top_k: int = 6):
        """混合检索：同时检索课程知识库和当前用户的上传文档"""
        # 课程知识库（所有人共享）
        course_results = self.course_vector_store.similarity_search_with_score(
            query, k=top_k // 2
        )

        # 用户知识库：仅当前用户
        user_results = self.user_vector_store.similarity_search_with_score(
            query,
            k=top_k // 2,
            where={"user_id": user_id}  # ✅ 关键：按 user_id 过滤
        )

        all_results = []

        for doc, score in course_results:
            doc.metadata['source'] = 'course_knowledge_base'
            all_results.append((doc, score))

        for doc, score in user_results:
            doc.metadata['source'] = 'user_uploaded'
            all_results.append((doc, score))

        # 按相似度排序（score 越小越相关）
        return sorted(all_results, key=lambda x: x[1])[:top_k]

    def get_hybrid_retriever(self, user_id: str = "default"):
        """返回一个支持用户隔离的混合检索器"""
        class HybridRetriever:
            def __init__(self, course_store, user_store, user_id):
                self.course_store = course_store
                self.user_store = user_store
                self.user_id = user_id

            def get_relevant_documents(self, query):
                course_docs = self.course_store.similarity_search(query, k=5)
                user_docs = self.user_store.similarity_search(
                    query,
                    k=5,
                    where={"user_id": self.user_id}  # ✅ 用户隔离
                )
                for doc in course_docs:
                    doc.metadata['source'] = 'course_knowledge_base'
                for doc in user_docs:
                    doc.metadata['source'] = 'user_uploaded'
                return course_docs + user_docs

        return HybridRetriever(self.course_vector_store, self.user_vector_store, user_id)

    def answer_question(self, query: str, user_id: str = "default", source: str = "hybrid"):
            """
            回答问题，支持三种检索模式。
            :param query: 用户的问题
            :param user_id: 用户ID
            :param source: 检索来源，可选 'course', 'user', 'hybrid'
            :yield: 包含答案和来源的字典
            """
            # --- 1. 根据 source 创建不同的检索器 ---
            if source == "course":
                # 仅从课程库检索
                retriever = self.course_vector_store.as_retriever(search_kwargs={"k": 6})
            elif source == "user":
                # 仅从用户库检索，并过滤 user_id
                retriever = self.user_vector_store.as_retriever(
                    search_kwargs={
                        "k": 6,
                        "filter": {"user_id": user_id}  # ✅ 内置过滤
                    }
                )
            else:  # hybrid
                # 混合检索：创建一个支持混合的检索器
                # from langchain_core.retrievers import RetrieverLike
                from typing import List
                def hybrid_retriever(query) -> List:
                    course_docs = self.course_vector_store.similarity_search(query, k=3)
                    for doc in course_docs:
                        doc.metadata['source'] = 'course_knowledge_base'

                    user_docs = self.user_vector_store.similarity_search(
                        query,
                        k=3,
                        filter={"user_id": user_id}  # ✅ 过滤
                    )
                    for doc in user_docs:
                        doc.metadata['source'] = 'user_uploaded'

                    return course_docs + user_docs

                # 包装成 LangChain 可用的 Runnable
                from langchain_core.runnables import RunnableLambda
                retriever = RunnableLambda(hybrid_retriever)

            # --- 2. 创建 RAG 链 ---
            llm = ChatOpenAI(
                    model="qwen-max",
                    api_key=os.getenv("DASHSCOPE_API_KEY"),
                    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    temperature=0,
                    streaming=True
                    )

            system_prompt = (
                """
                    你是一个课程助手，请根据以下上下文信息回答问题。如果信息不足，请说明。
                    不要直接复制上下文，而是根据上下文信息进行推理和回答。
                    不要编造答案，只能根据上下文信息进行回答。
                    如果用户提问了与文档内容无关的问题，忽略他的问题并回答：“我是课程咨询助手，请不要提与课程内容无关的问题”
                    并根据用户问题的意图推荐用户切换“联网查询”或者“普通对话”模式，语气稍微耐心一些。
                    回答尽可能简洁明了，注意文字排版要美观，不要一行就几个字。
                """
                "Context: {context}"
            )

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    # MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                ]
            )

            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(retriever, question_answer_chain)
            answer = ''
            # --- 3. 执行链 ---
            for chunk in rag_chain.stream({"input": query}):
                if 'context' in chunk:
                    yield{"type":"rag","content":"正在查询本地知识库...\n"}
                if 'answer' in chunk:
                    yield {"type":"answer","answer":chunk['answer']}
            
            # answer = result["answer"]

            # --- 4. 手动构建 sources 列表（用于前端展示）---
            search_results = []
            if source == "course":
                results = self.course_vector_store.similarity_search_with_score(query, k=6)
                for doc, score in results:
                    doc.metadata['source'] = 'course_knowledge_base'
                    search_results.append((doc, score))
            elif source == "user":
                results = self.user_vector_store.similarity_search_with_score(
                    query, k=6, filter={"user_id": user_id}
                )
                for doc, score in results:
                    doc.metadata['source'] = 'user_uploaded'
                    search_results.append((doc, score))
            else:  # hybrid
                course_results = self.course_vector_store.similarity_search_with_score(query, k=3)
                user_results = self.user_vector_store.similarity_search_with_score(
                    query, k=3, filter={"user_id": user_id}
                )
                all_results = [(doc, score) for doc, score in course_results] + \
                            [(doc, score) for doc, score in user_results]
                search_results = sorted(all_results, key=lambda x: x[1])[:6]

            sources = []
            for doc, score in search_results:
                sources.append({
                    'content': doc.page_content[:200] + "...",
                    'source': doc.metadata.get('source', 'unknown'),
                    'file': doc.metadata.get('original_file', 'unknown'),
                    'score': float(score)
                })

            # yield {
            #     'type':'sources',
            #     'sources': sources,
            #     'context_used': len(search_results)
            # }

    def get_user_documents(self, user_id: str = "default") -> List[Dict]:
        """获取某用户上传的文档列表"""
        # try:
            # 查询该用户的所有文档元数据
        results = self.user_vector_store._collection.get(
            where={"user_id": user_id},
            include=["metadatas"]                 # 只需要元数据
        )
        seen = set()
        user_docs = []
        for item in results["metadatas"]:
            filename = item["original_file"]
            if filename not in seen:
                seen.add(filename)
                user_docs.append({
                    "file": filename,
                    "upload_time": item.get("upload_id", "unknown"),
                    "source": "user_uploaded"
                })
        return user_docs
        # except Exception as e:
        #     print(f"获取用户文档失败: {e}")
        #     return []


if __name__ == "__main__":
    # 初始化课程助手
    assistant = RAGProcess()

    # # 1. 加载课程文档（一次性设置）
    # assistant.load_course_documents("课程助手/local_course")

    # # 2. 用户 A 上传文档
    upload_result_a = assistant.upload_document("课程助手/gradio_tmp/毕设论文6页.pdf", "")
    print("用户 A 上传结果:", upload_result_a)

    user_docs = assistant.get_user_documents("")
    print(user_docs)

    # question = "管理员表有哪些字段"
    # answer_a = assistant.answer_question(question, "user123","user")
    # print("\n用户 A 的回答:")
    # # print(answer_a['answer'])
    # for chunk in answer_a:
    #     if chunk['type'] == 'answer':
    #         print(chunk['answer'],end='',flush=True)
    #     elif chunk['type'] == 'sources':
    #         print(chunk['sources'])



    # print(answer_a['answer'])
    #  查看用户 A 上传了哪些文档
    # print("\n用户 A 的上传记录:")
    # for doc in assistant.get_user_documents("user123"):
    #     print(f"  - {doc['file']}")