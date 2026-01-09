"""
RAG引擎 - 检索增强生成
提供基于历史知识的场景理解增强
"""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant as LangChainQdrant
from qdrant_client import QdrantClient
from typing import Dict, List
import json

class RAGEngine:
    def __init__(self, qdrant_url: str, openai_api_key: str):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model="gpt-4",
            temperature=0.3
        )
        
        self.embeddings = OpenAIEmbeddings(
            api_key=openai_api_key,
            model="text-embedding-3-small"
        )
        
        self.qdrant_client = QdrantClient(url=qdrant_url)
        
        self.vectorstore = LangChainQdrant(
            client=self.qdrant_client,
            collection_name="api_knowledge",
            embeddings=self.embeddings
        )
    
    async def enhance_scenario_understanding(
        self,
        user_input: str,
        project_id: str
    ) -> Dict:
        """RAG增强场景理解"""
        # 1. 检索相关API
        relevant_apis = await self._retrieve_relevant_apis(user_input, project_id)
        
        # 2. 检索相似场景
        similar_scenarios = await self._retrieve_similar_scenarios(user_input, project_id)
        
        # 3. 构建增强Prompt
        enhanced_prompt = self._build_enhanced_prompt(
            user_input,
            relevant_apis,
            similar_scenarios
        )
        
        # 4. 调用LLM
        response = await self.llm.ainvoke(enhanced_prompt)
        
        try:
            understanding = json.loads(response.content)
        except:
            understanding = {"raw_response": response.content}
        
        return {
            "understanding": understanding,
            "context": {
                "relevant_apis": relevant_apis,
                "similar_scenarios": similar_scenarios
            }
        }
    
    async def _retrieve_relevant_apis(
        self,
        query: str,
        project_id: str,
        k: int = 5
    ) -> List[Dict]:
        """检索相关API"""
        retriever = self.vectorstore.as_retriever(
            search_kwargs={
                "k": k,
                "filter": {
                    "type": "api",
                    "project_id": project_id
                }
            }
        )
        
        docs = await retriever.aget_relevant_documents(query)
        
        return [
            {
                "api_id": doc.metadata.get('api_id'),
                "name": doc.metadata.get('name'),
                "path": doc.metadata.get('path'),
                "method": doc.metadata.get('method'),
                "description": doc.metadata.get('description', '')
            }
            for doc in docs
        ]
    
    async def _retrieve_similar_scenarios(
        self,
        query: str,
        project_id: str,
        k: int = 3
    ) -> List[Dict]:
        """检索相似场景"""
        retriever = self.vectorstore.as_retriever(
            search_kwargs={
                "k": k,
                "filter": {
                    "type": "scenario",
                    "project_id": project_id
                }
            }
        )
        
        docs = await retriever.aget_relevant_documents(query)
        
        return [
            {
                "scenario_id": doc.metadata.get('scenario_id'),
                "name": doc.metadata.get('name'),
                "description": doc.metadata.get('description', '')
            }
            for doc in docs
        ]
    
    def _build_enhanced_prompt(
        self,
        user_input: str,
        relevant_apis: List[Dict],
        similar_scenarios: List[Dict]
    ) -> str:
        """构建增强Prompt"""
        prompt = f"""用户想要测试以下场景：
{user_input}

根据知识库检索，找到了以下相关信息：

## 相关接口
"""
        if relevant_apis:
            for i, api in enumerate(relevant_apis, 1):
                prompt += f"{i}. {api['method']} {api['path']} - {api['name']}\n"
        else:
            prompt += "（未找到相关接口）\n"
        
        if similar_scenarios:
            prompt += "\n## 相似的测试场景\n"
            for i, scenario in enumerate(similar_scenarios, 1):
                prompt += f"{i}. {scenario['name']}\n"
        
        prompt += """
请基于以上信息，分析用户的测试意图，并以JSON格式返回：
{
  "intent": "测试意图",
  "recommended_apis": ["推荐的API列表"],
  "confidence": 0.9
}
"""
        return prompt
