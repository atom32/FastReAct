#!/usr/bin/env python3
"""
诊断技能选择逻辑
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact import Agent


def analyze_skill_selection(query: str):
    """分析为什么选择了这些技能"""
    print("=" * 70)
    print(f"查询: {query}")
    print("=" * 70)

    agent = Agent()

    # 1. 提取关键词
    print("\n[1] 关键词提取")
    print("-" * 70)

    query_lower = query.lower()

    # 英文单词
    en_words = set(re.findall(r'\b[a-zA-Z]{2,}\b', query_lower))
    print(f"英文关键词: {en_words}")

    # 中文字符和n-grams
    chinese_chars = [c for c in query_lower if '\u4e00' <= c <= '\u9fff']
    chinese_ngrams = set()
    for i in range(len(chinese_chars)):
        chinese_ngrams.add(chinese_chars[i])
        if i < len(chinese_chars) - 1:
            chinese_ngrams.add(chinese_chars[i] + chinese_chars[i+1])
        if i < len(chinese_chars) - 2:
            chinese_ngrams.add(chinese_chars[i] + chinese_chars[i+1] + chinese_chars[i+2])

    print(f"中文关键词: {chinese_ngrams}")

    keywords = en_words | chinese_ngrams
    print(f"\n所有关键词: {keywords}")

    # 2. 检查两个技能的匹配情况
    print("\n[2] 技能匹配分析")
    print("-" * 70)

    skills_to_check = ["news_aggregator", "graphrag_workflow"]

    for skill_name in skills_to_check:
        skill = agent._skills.get(skill_name)
        if not skill:
            print(f"\n{skill_name}: 未找到")
            continue

        print(f"\n{skill_name}:")
        print(f"  名称: {skill.name}")
        print(f"  描述: {skill.description[:80]}...")
        print(f"  标签: {skill.metadata.tags}")

        # 检查名称匹配
        name_match = skill.name.lower() in query_lower
        print(f"  名称匹配: {name_match} (+10 分)" if name_match else "  名称匹配: 否")

        # 检查标签匹配
        tag_matches = []
        for tag in skill.metadata.tags:
            tag_lower = tag.lower()
            if tag_lower in query_lower:
                tag_matches.append(tag)
                print(f"  标签匹配: '{tag}' 在查询中 (+3 分)")

        # 检查描述关键词匹配
        desc_lower = skill.description.lower()
        desc_en_words = set(re.findall(r'\b[a-zA-Z]{2,}\b', desc_lower))
        desc_chinese_chars = [c for c in desc_lower if '\u4e00' <= c <= '\u9fff']

        desc_chinese_ngrams = set()
        for i in range(len(desc_chinese_chars)):
            desc_chinese_ngrams.add(desc_chinese_chars[i])
            if i < len(desc_chinese_chars) - 1:
                desc_chinese_ngrams.add(desc_chinese_chars[i] + desc_chinese_chars[i+1])

        desc_keywords = desc_en_words | desc_chinese_ngrams

        overlap = keywords & desc_keywords
        if overlap:
            print(f"  描述关键词匹配: {overlap} (+{len(overlap) * 2} 分)")

    # 3. 实际选择的技能
    print("\n[3] 实际选择的技能")
    print("-" * 70)

    selected = agent._select_skills_auto(query, max_skills=10)

    for i, skill_name in enumerate(selected, 1):
        print(f"{i}. {skill_name}")

    # 4. 问题诊断
    print("\n[4] 问题诊断")
    print("-" * 70)

    if "graphrag_workflow" in selected:
        print("\n⚠️ graphrag_workflow 被选中，可能原因：")
        print("   - 标签包含 'search', 'query', 'retrieval'")
        print("   - 中文标签包含 '检索'")
        print("   - '获取' 可能匹配 '检索'")
        print("   - '最新的' 可能暗示 'search' 或 'query'")

    if "news_aggregator" in selected:
        print("\n✅ news_aggregator 被选中，正确匹配：")
        print("   - 标签包含 'news', 'hackernews'")
        print("   - 描述包含 'news', 'aggregation'")

    # 5. 建议
    print("\n[5] 建议")
    print("-" * 70)

    if "graphrag_workflow" in selected and "news_aggregator" in selected:
        print("\n💡 减少 graphrag_workflow 的误匹配：")
        print("   1. 移除或修改 'search', 'query', 'retrieval' 等通用标签")
        print("   2. 移除中文标签 '检索'（太通用）")
        print("   3. 添加更具体的标签，如 '知识图谱查询', '实体关系'")
        print("\n💡 优化 news_aggregator 的匹配：")
        print("   1. 添加更多新闻相关标签")
        print("   2. 确保标签独特性")


if __name__ == "__main__":
    query = "获取 HackerNews 最新的 3 条热门新闻并生成中文摘要"
    analyze_skill_selection(query)
