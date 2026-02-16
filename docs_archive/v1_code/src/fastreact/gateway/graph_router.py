"""
Tool Graph API Router - 工具图 REST API

提供创建、执行、管理工具图的 REST API 端点。
"""

import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from fastreact.graph import (
    create_graph,
    create_tool_node,
    execute_graph,
    create_debugger,
    debug_graph,
    record_execution,
    replay_execution,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/graphs", tags=["Tool Graph"])


# ============================================================================
# Request/Response Models
# ============================================================================

class NodeDefinition(BaseModel):
    """节点定义"""
    id: str = Field(..., description="节点 ID")
    type: str = Field(default="tool", description="节点类型")
    tool: str = Field(..., description="工具名称")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="输入参数")


class EdgeDefinition(BaseModel):
    """边定义"""
    from_node: str = Field(..., alias="from", description="源节点 ID")
    to_node: str = Field(..., alias="to", description="目标节点 ID")


class GraphDefinition(BaseModel):
    """图定义"""
    name: str = Field(..., description="图名称")
    description: Optional[str] = Field(None, description="图描述")
    nodes: List[NodeDefinition] = Field(default_factory=list, description="节点列表")
    edges: List[EdgeDefinition] = Field(default_factory=list, description="边列表")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "my_workflow",
                "description": "Example workflow",
                "nodes": [
                    {"id": "node1", "type": "tool", "tool": "search", "inputs": {}},
                    {"id": "node2", "type": "tool", "tool": "summarize", "inputs": {}}
                ],
                "edges": [
                    {"from": "node1", "to": "node2"}
                ]
            }
        }


class ExecuteRequest(BaseModel):
    """执行请求"""
    inputs: Dict[str, Any] = Field(default_factory=dict, description="输入参数")
    debug: bool = Field(default=False, description="是否启用调试")
    breakpoints: List[str] = Field(default_factory=list, description="断点列表")
    record: bool = Field(default=False, description="是否记录执行历史")


class ExecuteResponse(BaseModel):
    """执行响应"""
    success: bool
    execution_time: float
    completed_nodes: int
    failed_nodes: int
    total_nodes: int
    outputs: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class GraphInfo(BaseModel):
    """图信息"""
    id: str
    name: str
    description: Optional[str] = None
    node_count: int
    edge_count: int
    created_at: str


# ============================================================================
# In-Memory Storage
# ============================================================================

# 存储: graph_id -> GraphDefinition
_graphs: Dict[str, Dict[str, Any]] = {}

# 存储: execution_id -> ExecutionReport
_executions: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Helper Functions
# ============================================================================


def _create_graph_from_definition(graph_def: GraphDefinition) -> 'ToolGraph':
    """从定义创建 ToolGraph"""
    graph = create_graph(graph_def.name)

    # TODO: 这里需要从工具注册表获取实际的工具函数
    # 目前只是占位符实现

    # 创建节点
    for node_def in graph_def.nodes:
        # 暂时跳过，需要集成工具注册系统
        pass

    # 连接节点
    for edge in graph_def.edges:
        graph.connect(edge.from_node, edge.to_node)

    return graph


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/create", response_model=GraphInfo)
async def create_graph_endpoint(graph_def: GraphDefinition):
    """
    创建工具图

    创建一个新的工具图定义。
    """
    try:
        # 生成唯一 ID
        graph_id = str(uuid.uuid4())

        # 存储图定义
        _graphs[graph_id] = {
            "id": graph_id,
            "definition": graph_def.dict(),
            "created_at": datetime.now().isoformat(),
        }

        logger.info(f"Created graph: {graph_id} - {graph_def.name}")

        return GraphInfo(
            id=graph_id,
            name=graph_def.name,
            description=graph_def.description,
            node_count=len(graph_def.nodes),
            edge_count=len(graph_def.edges),
            created_at=_graphs[graph_id]["created_at"],
        )

    except Exception as e:
        logger.error(f"Failed to create graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[GraphInfo])
async def list_graphs():
    """
    列出所有工具图

    获取所有已创建的工具图列表。
    """
    graphs = []
    for graph_id, data in _graphs.items():
        defn = data["definition"]
        graphs.append(GraphInfo(
            id=graph_id,
            name=defn["name"],
            description=defn.get("description"),
            node_count=len(defn.get("nodes", [])),
            edge_count=len(defn.get("edges", [])),
            created_at=data["created_at"],
        ))
    return graphs


@router.get("/{graph_id}", response_model=Dict[str, Any])
async def get_graph(graph_id: str):
    """
    获取工具图详情

    获取指定工具图的完整定义。
    """
    if graph_id not in _graphs:
        raise HTTPException(status_code=404, detail=f"Graph not found: {graph_id}")

    return _graphs[graph_id]


@router.post("/{graph_id}/execute", response_model=ExecuteResponse)
async def execute_graph_endpoint(
    graph_id: str,
    request: ExecuteRequest,
    background_tasks: BackgroundTasks = None,
):
    """
    执行工具图

    执行指定的工具图。
    """
    if graph_id not in _graphs:
        raise HTTPException(status_code=404, detail=f"Graph not found: {graph_id}")

    try:
        graph_def_dict = _graphs[graph_id]["definition"]
        graph_def = GraphDefinition(**graph_def_dict)

        # 创建图
        graph = _create_graph_from_definition(graph_def)

        # 执行
        if request.debug:
            # 调试模式
            debugger = create_debugger()
            for bp in request.breakpoints:
                debugger.add_breakpoint(bp)
            report = await debug_graph(
                graph,
                request.inputs,
                request.breakpoints,
            )
        elif request.record:
            # 记录模式
            report = await record_execution(
                graph,
                request.inputs,
                save_path=f"./data/executions/{graph_id}_{datetime.now().timestamp()}.json",
            )
        else:
            # 普通执行
            report = await execute_graph(graph, request.inputs)

        # 存储执行记录
        execution_id = str(uuid.uuid4())
        _executions[execution_id] = {
            "graph_id": graph_id,
            "report": report,
            "executed_at": datetime.now().isoformat(),
        }

        logger.info(f"Executed graph {graph_id}: success={report.success}")

        return ExecuteResponse(
            success=report.success,
            execution_time=report.execution_time,
            completed_nodes=report.completed_nodes,
            failed_nodes=report.failed_nodes,
            total_nodes=report.total_nodes,
            outputs=report.node_results or {},
            errors=report.errors or [],
        )

    except Exception as e:
        logger.error(f"Failed to execute graph {graph_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{graph_id}")
async def delete_graph(graph_id: str):
    """
    删除工具图

    删除指定的工具图。
    """
    if graph_id not in _graphs:
        raise HTTPException(status_code=404, detail=f"Graph not found: {graph_id}")

    del _graphs[graph_id]
    logger.info(f"Deleted graph: {graph_id}")

    return {"message": f"Graph {graph_id} deleted"}


@router.get("/{graph_id}/history")
async def get_execution_history(
    graph_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    获取执行历史

    获取指定工具图的执行历史记录。
    """
    if graph_id not in _graphs:
        raise HTTPException(status_code=404, detail=f"Graph not found: {graph_id}")

    # 筛选该图的执行记录
    executions = [
        (exec_id, data)
        for exec_id, data in _executions.items()
        if data["graph_id"] == graph_id
    ]

    # 分页
    start = offset
    end = offset + limit
    paged = executions[start:end]

    return {
        "graph_id": graph_id,
        "total": len(executions),
        "limit": limit,
        "offset": offset,
        "executions": [
            {
                "execution_id": exec_id,
                "executed_at": data["executed_at"],
                "success": data["report"].success,
                "execution_time": data["report"].execution_time,
                "completed_nodes": data["report"].completed_nodes,
                "failed_nodes": data["report"].failed_nodes,
            }
            for exec_id, data in paged
        ],
    }


@router.post("/replay/{execution_id}")
async def replay_execution_endpoint(
    execution_id: str,
    replay_mode: str = Query("replay", regex="^(replay|simulate)$"),
):
    """
    回放执行

    从历史记录回放执行。
    """
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    try:
        execution_data = _executions[execution_id]
        graph_id = execution_data["graph_id"]

        if graph_id not in _graphs:
            raise HTTPException(status_code=404, detail=f"Graph not found: {graph_id}")

        graph_def_dict = _graphs[graph_id]["definition"]
        graph_def = GraphDefinition(**graph_def_dict)
        graph = _create_graph_from_definition(graph_def)

        # 从保存的历史文件回放
        # TODO: 这里需要实际的文件路径
        report = await replay_execution(
            graph,
            f"./data/executions/{execution_id}.json",
            replay_mode=replay_mode,
        )

        logger.info(f"Replayed execution {execution_id}: mode={replay_mode}")

        return ExecuteResponse(
            success=report.success,
            execution_time=report.execution_time,
            completed_nodes=report.completed_nodes,
            failed_nodes=report.failed_nodes,
            total_nodes=report.total_nodes,
            outputs=report.node_results or {},
            errors=report.errors or [],
        )

    except Exception as e:
        logger.error(f"Failed to replay execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_graph(graph_def: GraphDefinition):
    """
    验证图定义

    验证图定义的结构是否正确。
    """
    errors = []

    # 基本验证
    if not graph_def.name:
        errors.append("Missing 'name'")

    # 验证节点
    node_ids = set()
    for i, node in enumerate(graph_def.nodes):
        if not node.id:
            errors.append(f"Node {i}: Missing 'id'")
        if not node.tool:
            errors.append(f"Node {node.id}: Missing 'tool'")
        node_ids.add(node.id)

    # 验证边
    for i, edge in enumerate(graph_def.edges):
        if edge.from_node not in node_ids:
            errors.append(f"Edge {i}: Unknown node '{edge.from_node}' in 'from'")
        if edge.to_node not in node_ids:
            errors.append(f"Edge {i}: Unknown node '{edge.to_node}' in 'to'")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
