"""
Deep Research 工具

实现类似 Perplexity 的深度研究报告生成功能。
通过多轮搜索和 LLM 综合分析，生成结构化的研究报告。
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ResearchSection:
    """研究报告章节"""
    title: str
    content: str
    subsections: List['ResearchSection'] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

    def to_markdown(self, level: int = 2) -> str:
        """转换为 Markdown 格式"""
        prefix = "#" * level
        md = f"\n{prefix} {self.title}\n\n{self.content}\n"

        # 子章节
        for subsection in self.subsections:
            md += subsection.to_markdown(level + 1)

        # 来源列表
        if self.sources:
            md += f"\n**Sources:**\n"
            for i, source in enumerate(self.sources, 1):
                md += f"{i}. {source}\n"

        return md


@dataclass
class ResearchReport:
    """研究报告"""
    topic: str
    title: str
    sections: List[ResearchSection] = field(default_factory=list)
    summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    all_sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """转换为完整的 Markdown 报告"""
        md = f"# {self.title}\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        if self.summary:
            md += f"## Executive Summary\n\n{self.summary}\n\n"

        if self.key_findings:
            md += "## Key Findings\n\n"
            for finding in self.key_findings:
                md += f"- {finding}\n"
            md += "\n"

        for section in self.sections:
            md += section.to_markdown(2)

        if self.all_sources:
            md += "\n## All Sources\n\n"
            for i, source in enumerate(set(self.all_sources), 1):
                md += f"{i}. {source}\n"

        return md


class DeepResearchEngine:
    """
    深度研究引擎

    执行多轮搜索和综合分析，生成研究报告。
    """

    def __init__(
        self,
        llm_client,
        search_client=None,
        max_iterations: int = 3,
        max_sources: int = 10,
        enable_tavily: bool = True,
    ):
        """
        初始化研究引擎

        Args:
            llm_client: LLM 客户端（用于查询生成和综合）
            search_client: 搜索客户端（可选，如果不提供将使用内置）
            max_iterations: 最大搜索轮数
            max_sources: 最大收集来源数量
            enable_tavily: 是否启用 Tavily（如果有）
        """
        self.llm_client = llm_client
        self.search_client = search_client
        self.max_iterations = max_iterations
        self.max_sources = max_sources
        self.enable_tavily = enable_tavily

        # 收集的信息
        self._collected_info: List[Dict[str, Any]] = []
        self._search_queries: List[str] = []

    async def research(
        self,
        topic: str,
        depth: str = "standard",
        focus_areas: Optional[List[str]] = None,
    ) -> ResearchReport:
        """
        执行深度研究

        Args:
            topic: 研究主题
            depth: 研究深度（quick/standard/deep）
            focus_areas: 关注领域列表

        Returns:
            ResearchReport: 研究报告
        """
        # 根据深度设置迭代次数
        iterations_map = {
            "quick": 2,
            "standard": 4,
            "deep": 6,
        }
        max_iterations = iterations_map.get(depth, self.max_iterations)

        logger.info(f"Starting deep research on '{topic}' (depth={depth}, iterations={max_iterations})")

        # Phase 1: 生成初始研究问题
        initial_queries = await self._generate_research_queries(topic, focus_areas)

        # Phase 2: 多轮搜索
        for i, query in enumerate(initial_queries[:max_iterations]):
            logger.info(f"Research iteration {i+1}/{max_iterations}: {query}")
            await self._search_and_collect(query, topic)

            # 避免请求过快
            await asyncio.sleep(0.5)

        # Phase 3: 生成报告结构
        report_structure = await self._generate_report_structure(topic)

        # Phase 4: 填充各个章节
        sections = []
        for section_def in report_structure.get("sections", []):
            section = await self._generate_section(section_def, topic)
            sections.append(section)

        # Phase 5: 生成摘要和关键发现
        summary = await self._generate_summary(topic, sections)
        key_findings = await self._generate_key_findings(topic, sections)

        # 整合所有来源
        all_sources = []
        for info in self._collected_info:
            if "url" in info:
                all_sources.append(info["url"])
            elif "title" in info:
                all_sources.append(f"{info.get('title', '')} - {info.get('source', '')}")

        # 创建报告
        report = ResearchReport(
            topic=topic,
            title=report_structure.get("title", f"Research Report: {topic}"),
            sections=sections,
            summary=summary,
            key_findings=key_findings,
            all_sources=list(set(all_sources))[:self.max_sources],
            metadata={
                "depth": depth,
                "iterations": len(initial_queries[:max_iterations]),
                "total_sources": len(all_sources),
                "generated_at": datetime.now().isoformat(),
            },
        )

        logger.info(f"Research completed: {len(all_sources)} sources collected")

        return report

    async def _generate_research_queries(
        self,
        topic: str,
        focus_areas: Optional[List[str]] = None
    ) -> List[str]:
        """生成研究查询问题"""
        prompt = f"""Given the research topic: "{topic}"

Generate {self.max_iterations} specific search queries that would help gather comprehensive information about this topic.

Focus on:
1. Overview and background information
2. Current state and recent developments
3. Key concepts and terminology
4. Applications and use cases
5. Challenges and limitations

Return your response as a numbered list of search queries (one per line)."""

        try:
            response = await self._call_llm(prompt, temperature=0.5)
            queries = self._parse_numbered_list(response)

            # 如果解析失败，使用默认查询
            if not queries:
                queries = [
                    f"{topic} overview introduction",
                    f"latest developments {topic}",
                    f"applications use cases {topic}",
                    f"challenges limitations {topic}",
                ]

            self._search_queries = queries
            return queries

        except Exception as e:
            logger.error(f"Failed to generate research queries: {e}")
            # 返回默认查询
            return [
                f"{topic} overview",
                f"{topic} recent developments",
                f"{topic} applications",
                f"{topic} challenges",
            ]

    async def _search_and_collect(self, query: str, context: str) -> None:
        """执行搜索并收集信息"""
        # 尝试使用 Tavily
        if self.enable_tavily and self.search_client:
            try:
                results = await self._search_with_tavily(query)
                if results:
                    self._collected_info.extend(results)
                    return
            except Exception as e:
                logger.warning(f"Tavily search failed: {e}")

        # Fallback: 使用 LLM 生成模拟搜索结果
        # （在实际使用中，应该集成真实的搜索 API）
        synthetic_result = await self._generate_synthetic_result(query, context)
        self._collected_info.append(synthetic_result)

    async def _search_with_tavily(self, query: str) -> List[Dict[str, Any]]:
        """使用 Tavily 搜索"""
        if not self.search_client or not hasattr(self.search_client, 'search'):
            return []

        try:
            results = await asyncio.to_thread(
                self.search_client.search,
                query,
                search_depth="advanced",
                max_results=5,
            )

            formatted_results = []
            for result in results.get("results", []):
                formatted_results.append({
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0),
                    "source": "tavily",
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []

    async def _generate_synthetic_result(self, query: str, context: str) -> Dict[str, Any]:
        """生成模拟搜索结果（用于无搜索 API 时）"""
        prompt = f"""Act as a search engine for the query: "{query}"

Context: {context}

Provide a comprehensive answer with:
1. Key information about the topic
2. Important facts or data points
3. Notable aspects or considerations

Format your response as a concise summary (2-3 paragraphs)."""

        try:
            response = await self._call_llm(prompt, temperature=0.7)

            return {
                "title": f"Research: {query}",
                "content": response,
                "query": query,
                "source": "llm_synthetic",
            }
        except Exception as e:
            logger.error(f"Failed to generate synthetic result: {e}")
            return {
                "title": f"Research: {query}",
                "content": f"Information about {query} related to {context}.",
                "query": query,
                "source": "fallback",
            }

    async def _generate_report_structure(self, topic: str) -> Dict[str, Any]:
        """生成报告结构"""
        context = self._format_collected_info()[:2000]  # 限制上下文长度

        prompt = f"""Based on research about: {topic}

Collected information:
{context}

Design a comprehensive research report structure. Include:
1. An engaging title
2. 4-6 main sections with clear focus areas
3. Logical flow and organization

Return in JSON format:
{{
    "title": "Report Title",
    "sections": [
        {{"title": "Section Title", "focus": "What this section covers"}},
        ...
    ]
}}"""

        try:
            response = await self._call_llm(prompt, temperature=0.5)

            # 尝试解析 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                import json
                return json.loads(json_match.group(0))

        except Exception as e:
            logger.error(f"Failed to parse report structure: {e}")

        # 默认结构
        return {
            "title": f"Research Report: {topic}",
            "sections": [
                {"title": "Overview", "focus": "Background and introduction"},
                {"title": "Key Concepts", "focus": "Core concepts and terminology"},
                {"title": "Applications", "focus": "Use cases and implementations"},
                {"title": "Challenges", "focus": "Limitations and considerations"},
            ],
        }

    async def _generate_section(self, section_def: Dict[str, Any], topic: str) -> ResearchSection:
        """生成报告章节"""
        title = section_def.get("title", "")
        focus = section_def.get("focus", "")

        # 筛选相关内容
        relevant_info = self._filter_relevant_info(title, focus)

        context = "\n\n".join([
            f"- {info.get('title', '')}: {info.get('content', '')[:500]}"
            for info in relevant_info[:5]
        ])

        prompt = f"""Write a detailed section for a research report about: {topic}

Section: {title}
Focus: {focus}

Relevant information:
{context}

Write 2-3 comprehensive paragraphs covering this aspect of the topic.
Include specific details and insights."""

        try:
            content = await self._call_llm(prompt, temperature=0.7)

            # 提取来源
            sources = [info.get("url", info.get("title", "")) for info in relevant_info[:3]]

            return ResearchSection(
                title=title,
                content=content,
                sources=[s for s in sources if s],
            )
        except Exception as e:
            logger.error(f"Failed to generate section {title}: {e}")
            return ResearchSection(
                title=title,
                content=f"Information about {focus} related to {topic}.",
                sources=[],
            )

    async def _generate_summary(self, topic: str, sections: List[ResearchSection]) -> str:
        """生成执行摘要"""
        sections_overview = "\n".join([f"- {s.title}" for s in sections])

        prompt = f"""Write a concise executive summary (150-200 words) for a research report about: {topic}

The report covers these sections:
{sections_overview}

The summary should:
1. State the main purpose of the research
2. Highlight 2-3 key findings
3. Mention important implications or takeaways"""

        try:
            return await self._call_llm(prompt, temperature=0.6)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"This research report explores {topic}, covering key aspects including {sections_overview}."

    async def _generate_key_findings(self, topic: str, sections: List[ResearchSection]) -> List[str]:
        """生成关键发现"""
        sections_content = "\n\n".join([
            f"{s.title}: {s.content[:300]}"
            for s in sections
        ])

        prompt = f"""Based on the research about: {topic}

Extract 5-7 key findings as bullet points (one concise sentence each).

Content:
{sections_content}

Return only the bullet points, one per line."""

        try:
            response = await self._call_llm(prompt, temperature=0.5)
            findings = self._parse_bullet_list(response)

            if not findings:
                return [
                    f"Important aspect of {topic}",
                    f"Key consideration for {topic}",
                    f"Notable finding about {topic}",
                ]

            return findings[:7]

        except Exception as e:
            logger.error(f"Failed to generate key findings: {e}")
            return [f"Key finding about {topic}"]

    def _filter_relevant_info(self, title: str, focus: str) -> List[Dict[str, Any]]:
        """筛选相关信息"""
        keywords = [title.lower(), focus.lower()]
        keywords.extend(title.split())

        relevant = []
        for info in self._collected_info:
            score = 0
            text = (info.get("title", "") + " " + info.get("content", "")).lower()

            for keyword in keywords:
                if keyword in text:
                    score += 1

            if score > 0:
                relevant.append({**info, "relevance_score": score})

        # 按相关性排序
        relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return relevant

    def _format_collected_info(self) -> str:
        """格式化收集的信息"""
        formatted = []
        for info in self._collected_info:
            formatted.append(f"## {info.get('title', '')}\n{info.get('content', '')}")
        return "\n\n".join(formatted)

    def _parse_numbered_list(self, text: str) -> List[str]:
        """解析编号列表"""
        items = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            # 匹配 "1. ", "2. ", "1) ", "2) " 等格式
            match = re.match(r'^\d+[\.\)]\s*(.+)', line)
            if match:
                items.append(match.group(1).strip())

        return items

    def _parse_bullet_list(self, text: str) -> List[str]:
        """解析项目符号列表"""
        items = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            # 匹配 "- ", "* ", "• " 等格式
            match = re.match(r'^[-*•]\s*(.+)', line)
            if match:
                items.append(match.group(1).strip())

        return items

    async def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """调用 LLM"""
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.llm_client.model or "gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=1500,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise


# ============================================================================
# 工具函数
# ============================================================================

def create_deep_research_tool(
    llm_client=None,
    search_client=None,
    default_depth: str = "standard",
):
    """
    创建深度研究工具

    Args:
        llm_client: LLM 客户端
        search_client: 搜索客户端（Tavily）
        default_depth: 默认深度

    Returns:
        Tool: 深度研究工具
    """
    from ..tools import Tool

    async def execute(
        topic: str,
        depth: str = default_depth,
        focus_areas: Optional[List[str]] = None,
        output_format: str = "markdown",
    ) -> str:
        """
        执行深度研究

        Args:
            topic: 研究主题
            depth: 研究深度 (quick/standard/deep)
            focus_areas: 关注领域列表
            output_format: 输出格式 (markdown/json)

        Returns:
            研究报告（Markdown 格式）
        """
        engine = DeepResearchEngine(
            llm_client=llm_client,
            search_client=search_client,
            enable_tavily=True,
        )

        report = await engine.research(topic, depth, focus_areas)

        if output_format == "json":
            import json
            return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)

        return report.to_markdown()

    return Tool(
        name="deep_research",
        description="""Generate comprehensive research reports on any topic.

Performs multi-round research and analysis to create detailed reports similar to Perplexity.

Args:
    topic (str): Research topic or question
    depth (str): Research depth - "quick" (2 rounds), "standard" (4 rounds), "deep" (6 rounds)
    focus_areas (list): Optional list of specific areas to focus on
    output_format (str): Output format - "markdown" or "json"

Returns:
    str: Comprehensive research report with:
    - Executive summary
    - Key findings
    - Detailed sections
    - Source references

Example:
    result = deep_research(topic="Artificial Intelligence trends 2024", depth="standard")""",
        parameters={
            "topic": {
                "type": "string",
                "description": "Research topic or question",
            },
            "depth": {
                "type": "string",
                "description": "Research depth: quick, standard, or deep",
                "enum": ["quick", "standard", "deep"],
                "default": "standard",
            },
            "focus_areas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of specific focus areas",
            },
            "output_format": {
                "type": "string",
                "description": "Output format: markdown or json",
                "enum": ["markdown", "json"],
                "default": "markdown",
            },
        },
        execute=execute,
        group="ai",
    )
