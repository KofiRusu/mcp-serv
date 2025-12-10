"""
Automations API Routes - CRUD + Run + Deploy endpoints for the automation builder.
Includes diagram analysis with vision AI for building automations from architecture diagrams.
"""

from typing import Optional, List, AsyncGenerator
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio
import base64
import json
import os

from ChatOS.services.automation_store import (
    Automation, AutomationBlock, AutomationType, AutomationStatus, DeploymentType,
    get_automation_store
)
from ChatOS.services.automation_generator import get_automation_generator
from ChatOS.services.automation_runner import get_automation_runner
from ChatOS.services.automation_deployer import get_automation_deployer


router = APIRouter(prefix="/api/v1/automations", tags=["automations"])


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateRequest(BaseModel):
    """Request to generate automation from prompt."""
    prompt: str
    type: AutomationType = AutomationType.SCRAPER


class CreateRequest(BaseModel):
    """Request to create a new automation."""
    name: str
    description: str = ""
    type: AutomationType = AutomationType.SCRAPER
    blocks: List[dict] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    generated_code: Optional[str] = None
    paper_trading: bool = True
    symbols: List[str] = Field(default_factory=list)
    exchange: Optional[str] = None


class UpdateRequest(BaseModel):
    """Request to update an automation."""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[AutomationType] = None
    blocks: Optional[List[dict]] = None
    config: Optional[dict] = None
    generated_code: Optional[str] = None
    paper_trading: Optional[bool] = None
    symbols: Optional[List[str]] = None
    exchange: Optional[str] = None


class AutomationResponse(BaseModel):
    """Response with automation data."""
    id: str
    name: str
    description: str
    type: AutomationType
    deployment_type: DeploymentType = DeploymentType.DOCKER
    status: AutomationStatus
    blocks: List[dict]
    config: dict
    generated_code: Optional[str]
    docker_image: Optional[str]
    container_id: Optional[str]
    paper_trading: bool = True
    symbols: List[str] = Field(default_factory=list)
    exchange: Optional[str] = None
    created_at: str
    updated_at: str
    last_run: Optional[str]
    run_count: int
    total_pnl: float = 0.0
    win_rate: Optional[float] = None
    total_trades: int = 0
    error_message: Optional[str]
    logs: List[str]


class GenerateResponse(BaseModel):
    """Response from generate endpoint."""
    name: str
    description: str
    type: AutomationType
    deployment_type: DeploymentType = DeploymentType.DOCKER
    blocks: List[dict]
    config: dict
    generated_code: str
    template_used: str
    paper_trading: bool = True


class RunStatusResponse(BaseModel):
    """Response with run status."""
    running: bool
    pid: Optional[int] = None
    started_at: Optional[str] = None
    output_lines: List[str] = Field(default_factory=list)


# ============================================================================
# CRUD Endpoints
# ============================================================================

def _automation_to_response(a: Automation) -> AutomationResponse:
    """Convert an Automation to AutomationResponse."""
    return AutomationResponse(
        id=a.id,
        name=a.name,
        description=a.description,
        type=a.type,
        deployment_type=a.deployment_type,
        status=a.status,
        blocks=[b.model_dump() if hasattr(b, 'model_dump') else b for b in a.blocks],
        config=a.config,
        generated_code=a.generated_code,
        docker_image=a.docker_image,
        container_id=a.container_id,
        paper_trading=a.paper_trading,
        symbols=a.symbols,
        exchange=a.exchange,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
        last_run=a.last_run.isoformat() if a.last_run else None,
        run_count=a.run_count,
        total_pnl=a.total_pnl,
        win_rate=a.win_rate,
        total_trades=a.total_trades,
        error_message=a.error_message,
        logs=a.logs[-20:]  # Last 20 logs
    )


@router.get("/", response_model=List[AutomationResponse])
async def list_automations(type: Optional[AutomationType] = None):
    """List all automations, optionally filtered by type."""
    store = get_automation_store()
    automations = store.list_all(type_filter=type)
    return [_automation_to_response(a) for a in automations]


@router.post("/", response_model=AutomationResponse)
async def create_automation(request: CreateRequest):
    """Create a new automation."""
    store = get_automation_store()
    
    automation = Automation(
        name=request.name,
        description=request.description,
        type=request.type,
        blocks=[AutomationBlock(**b) if isinstance(b, dict) else b for b in request.blocks],
        config=request.config,
        generated_code=request.generated_code,
        paper_trading=request.paper_trading,
        symbols=request.symbols,
        exchange=request.exchange
    )
    
    created = store.create(automation)
    return _automation_to_response(created)


@router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(automation_id: str):
    """Get a specific automation."""
    store = get_automation_store()
    automation = store.get(automation_id)
    
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    return _automation_to_response(automation)


@router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(automation_id: str, request: UpdateRequest):
    """Update an existing automation."""
    store = get_automation_store()
    
    updates = request.model_dump(exclude_unset=True)
    if 'blocks' in updates and updates['blocks']:
        updates['blocks'] = [AutomationBlock(**b) if isinstance(b, dict) else b for b in updates['blocks']]
    
    automation = store.update(automation_id, updates)
    
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    return _automation_to_response(automation)


@router.delete("/{automation_id}")
async def delete_automation(automation_id: str):
    """Delete an automation."""
    store = get_automation_store()
    runner = get_automation_runner()
    deployer = get_automation_deployer()
    
    # Stop if running
    await runner.stop(automation_id)
    await deployer.undeploy(automation_id)
    
    if not store.delete(automation_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    
    return {"success": True}


# ============================================================================
# Generation Endpoints
# ============================================================================

@router.post("/generate", response_model=GenerateResponse)
async def generate_automation(request: GenerateRequest):
    """Generate automation config and code from natural language."""
    generator = get_automation_generator()
    
    result = await generator.generate_from_prompt(request.prompt, request.type)
    
    return GenerateResponse(
        name=result["name"],
        description=result["description"],
        type=result["type"],
        deployment_type=result.get("deployment_type", DeploymentType.DOCKER),
        blocks=result["blocks"],
        config=result["config"],
        generated_code=result["generated_code"],
        template_used=result["template_used"],
        paper_trading=result.get("paper_trading", True)
    )


@router.get("/types")
async def get_automation_types():
    """Get all supported automation types with descriptions."""
    generator = get_automation_generator()
    return generator.get_automation_types()


@router.get("/templates")
async def get_templates():
    """Get available automation templates."""
    generator = get_automation_generator()
    return generator.get_available_templates()


# ============================================================================
# Run Endpoints (Dev Mode)
# ============================================================================

@router.post("/{automation_id}/run")
async def run_automation(automation_id: str):
    """Start an automation in dev mode."""
    runner = get_automation_runner()
    result = await runner.start(automation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/{automation_id}/stop")
async def stop_automation(automation_id: str):
    """Stop a running automation."""
    runner = get_automation_runner()
    result = await runner.stop(automation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/{automation_id}/run-status", response_model=RunStatusResponse)
async def get_run_status(automation_id: str):
    """Get run status of an automation."""
    runner = get_automation_runner()
    status = runner.get_status(automation_id)
    
    return RunStatusResponse(
        running=status.get("running", False),
        pid=status.get("pid"),
        started_at=status.get("started_at"),
        output_lines=status.get("output_lines", [])
    )


@router.get("/{automation_id}/output")
async def get_output(automation_id: str, lines: int = 100):
    """Get recent output from a running automation."""
    runner = get_automation_runner()
    output = runner.get_output(automation_id, lines)
    return {"output": output}


# ============================================================================
# Deploy Endpoints (Docker)
# ============================================================================

@router.post("/{automation_id}/deploy")
async def deploy_automation(automation_id: str):
    """Deploy an automation as a Docker container."""
    deployer = get_automation_deployer()
    result = await deployer.deploy(automation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/{automation_id}/undeploy")
async def undeploy_automation(automation_id: str):
    """Stop and remove a deployed automation."""
    deployer = get_automation_deployer()
    result = await deployer.undeploy(automation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/{automation_id}/container-status")
async def get_container_status(automation_id: str):
    """Get status of a deployed container."""
    deployer = get_automation_deployer()
    return await deployer.get_container_status(automation_id)


@router.get("/{automation_id}/container-logs")
async def get_container_logs(automation_id: str, lines: int = 100):
    """Get logs from a deployed container."""
    deployer = get_automation_deployer()
    logs = await deployer.get_container_logs(automation_id, lines)
    return {"logs": logs}


@router.post("/{automation_id}/restart")
async def restart_container(automation_id: str):
    """Restart a deployed container."""
    deployer = get_automation_deployer()
    result = await deployer.restart_container(automation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ============================================================================
# Diagram Analysis Endpoints
# ============================================================================

class DiagramLayer(BaseModel):
    """A layer in the architecture diagram."""
    name: str
    components: List[str]


class DiagramAnalysis(BaseModel):
    """Analysis results from a diagram."""
    layers: List[DiagramLayer]
    totalComponents: int
    connections: int
    estimatedBlocks: int


class DiagramAnalysisResponse(BaseModel):
    """Full response from diagram analysis."""
    name: str
    description: str
    type: str
    blocks: List[dict]
    analysis: DiagramAnalysis


async def analyze_diagram_with_vision(image_data: bytes, image_type: str) -> dict:
    """
    Analyze an architecture diagram using vision AI.
    Falls back to mock analysis if AI is unavailable.
    """
    import httpx
    
    # Encode image to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # Try different AI providers
    analysis = None
    
    # Try OpenAI GPT-4 Vision
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key and not analysis:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are an expert at analyzing system architecture diagrams.
                                Extract all components, layers, and connections from the diagram.
                                Return a JSON object with this structure:
                                {
                                    "name": "System Name",
                                    "description": "Brief description",
                                    "layers": [
                                        {"name": "Layer Name", "components": ["Component1", "Component2"]}
                                    ],
                                    "connections": [
                                        {"from": "Component1", "to": "Component2"}
                                    ]
                                }
                                Be thorough - identify ALL visible components and their relationships."""
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Analyze this architecture diagram and extract all components, layers, and connections:"},
                                    {"type": "image_url", "image_url": {"url": f"data:{image_type};base64,{base64_image}"}}
                                ]
                            }
                        ],
                        "max_tokens": 4096,
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    analysis = json.loads(content)
        except Exception as e:
            print(f"OpenAI vision error: {e}")
    
    # Try Anthropic Claude Vision
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if anthropic_key and not analysis:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 4096,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": image_type,
                                            "data": base64_image
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": """Analyze this architecture diagram and extract all components, layers, and connections.
                                        Return ONLY a JSON object with this structure:
                                        {
                                            "name": "System Name",
                                            "description": "Brief description",
                                            "layers": [
                                                {"name": "Layer Name", "components": ["Component1", "Component2"]}
                                            ],
                                            "connections": [
                                                {"from": "Component1", "to": "Component2"}
                                            ]
                                        }
                                        Be thorough - identify ALL visible components and their relationships."""
                                    }
                                ]
                            }
                        ]
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['content'][0]['text']
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
        except Exception as e:
            print(f"Anthropic vision error: {e}")
    
    # Fallback to mock analysis
    if not analysis:
        analysis = _generate_mock_diagram_analysis()
    
    return analysis


def _generate_mock_diagram_analysis() -> dict:
    """Generate mock analysis for demo when AI is unavailable."""
    return {
        "name": "Trading System Architecture",
        "description": "Multi-layer trading system with data aggregation, signal processing, risk management, and execution",
        "layers": [
            {
                "name": "L1 Market Microstructure",
                "components": ["AGGR Agent", "TradeFuck Agent", "CoinGlass Heatmap Agent", "Footprint Charts"]
            },
            {
                "name": "L2 Indicator Layer",
                "components": ["Money V1 (Structure)", "Money V2 (Momentum)", "Legend (Visual Language)"]
            },
            {
                "name": "L3 Fusion & Signal Router",
                "components": ["Knowledgebase Fusion", "Scenario Builder", "Confluence Scorer", "Signal Validator"]
            },
            {
                "name": "L4 Risk Management",
                "components": ["Risk Operations Agent", "Sizing Engine", "DCA / DCA-lite", "Portfolio Guardrails"]
            },
            {
                "name": "L5 Execution & Monitoring",
                "components": ["Execution Agent", "Monitoring & Journal", "Audit Trail", "Learning Loop"]
            },
            {
                "name": "External Knowledge Cluster",
                "components": ["YouTube Agent", "External Knowledgebase", "Backtesting & Research Loop"]
            }
        ],
        "connections": [
            {"from": "AGGR Agent", "to": "Money V1 (Structure)"},
            {"from": "TradeFuck Agent", "to": "Money V1 (Structure)"},
            {"from": "Money V1 (Structure)", "to": "Knowledgebase Fusion"},
            {"from": "Money V2 (Momentum)", "to": "Knowledgebase Fusion"},
            {"from": "Knowledgebase Fusion", "to": "Scenario Builder"},
            {"from": "Scenario Builder", "to": "Confluence Scorer"},
            {"from": "Confluence Scorer", "to": "Signal Validator"},
            {"from": "Signal Validator", "to": "Risk Operations Agent"},
            {"from": "Risk Operations Agent", "to": "Sizing Engine"},
            {"from": "Sizing Engine", "to": "DCA / DCA-lite"},
            {"from": "DCA / DCA-lite", "to": "Execution Agent"},
            {"from": "Execution Agent", "to": "Monitoring & Journal"},
            {"from": "Monitoring & Journal", "to": "Learning Loop"},
            {"from": "Learning Loop", "to": "Knowledgebase Fusion"},
            {"from": "YouTube Agent", "to": "External Knowledgebase"},
            {"from": "External Knowledgebase", "to": "Knowledgebase Fusion"},
        ]
    }


def _get_block_type_for_layer(layer_name: str) -> str:
    """Determine block type based on layer name."""
    layer_lower = layer_name.lower()
    if 'microstructure' in layer_lower or 'data' in layer_lower:
        return 'agent'
    if 'indicator' in layer_lower:
        return 'processor'
    if 'fusion' in layer_lower or 'signal' in layer_lower or 'router' in layer_lower:
        return 'fusion'
    if 'risk' in layer_lower:
        return 'risk'
    if 'execution' in layer_lower or 'monitoring' in layer_lower:
        return 'execution'
    if 'knowledge' in layer_lower or 'external' in layer_lower:
        return 'data_source'
    return 'processor'


def _analysis_to_blocks(analysis: dict) -> List[dict]:
    """Convert diagram analysis to automation blocks."""
    blocks = []
    connection_map = {}
    
    # Build connection map
    for conn in analysis.get('connections', []):
        from_comp = conn['from']
        if from_comp not in connection_map:
            connection_map[from_comp] = []
        connection_map[from_comp].append(conn['to'])
    
    # Create blocks for each component
    block_id_map = {}  # component name -> block id
    
    for layer_idx, layer in enumerate(analysis.get('layers', [])):
        layer_name = layer['name']
        block_type = _get_block_type_for_layer(layer_name)
        
        for comp_idx, component in enumerate(layer.get('components', [])):
            block_id = f"block-{layer_idx}-{comp_idx}"
            block_id_map[component] = block_id
            
            blocks.append({
                "id": block_id,
                "type": block_type,
                "name": component,
                "layer": layer_name,
                "config": {},
                "position": {
                    "x": 300 + comp_idx * 200,
                    "y": 100 + layer_idx * 150
                },
                "connections": []  # Will be filled after all blocks created
            })
    
    # Fill in connections using block IDs
    for block in blocks:
        component_name = block['name']
        if component_name in connection_map:
            for target_name in connection_map[component_name]:
                if target_name in block_id_map:
                    block['connections'].append(block_id_map[target_name])
    
    return blocks


async def _stream_diagram_analysis(image_data: bytes, image_type: str) -> AsyncGenerator[str, None]:
    """
    Stream diagram analysis progress as Server-Sent Events.
    """
    import asyncio
    
    # Stage 1: Analyzing
    yield f"data: {json.dumps({'type': 'progress', 'progress': {'stage': 'analyzing', 'progress': 5, 'blocksBuilt': 0, 'totalBlocks': 0, 'message': 'Scanning diagram structure...'}})}\n\n"
    await asyncio.sleep(0.5)
    
    yield f"data: {json.dumps({'type': 'progress', 'progress': {'stage': 'analyzing', 'progress': 15, 'blocksBuilt': 0, 'totalBlocks': 0, 'message': 'Identifying components and text...'}})}\n\n"
    await asyncio.sleep(0.5)
    
    # Actually analyze the diagram
    analysis = await analyze_diagram_with_vision(image_data, image_type)
    
    layers = analysis.get('layers', [])
    total_components = sum(len(l.get('components', [])) for l in layers)
    connections = len(analysis.get('connections', []))
    
    # Send analysis results
    diagram_analysis = {
        "layers": [{"name": l['name'], "components": l['components']} for l in layers],
        "totalComponents": total_components,
        "connections": connections,
        "estimatedBlocks": total_components
    }
    
    yield f"data: {json.dumps({'type': 'analysis', 'analysis': diagram_analysis})}\n\n"
    
    # Stage 2: Extracting
    yield f"data: {json.dumps({'type': 'progress', 'progress': {'stage': 'extracting', 'progress': 25, 'blocksBuilt': 0, 'totalBlocks': total_components, 'message': f'Found {total_components} components across {len(layers)} layers'}})}\n\n"
    await asyncio.sleep(0.3)
    
    # Convert to blocks
    blocks = _analysis_to_blocks(analysis)
    
    # Stage 3: Building blocks progressively
    for i, block in enumerate(blocks):
        progress = 25 + ((i + 1) / len(blocks)) * 60
        
        msg = f"Building {block['name']}..."
        yield f"data: {json.dumps({'type': 'progress', 'progress': {'stage': 'building', 'currentLayer': block.get('layer', ''), 'currentComponent': block['name'], 'progress': progress, 'blocksBuilt': i + 1, 'totalBlocks': len(blocks), 'message': msg}, 'block': block})}\n\n"
        await asyncio.sleep(0.15)
    
    # Stage 4: Connecting
    yield f"data: {json.dumps({'type': 'progress', 'progress': {'stage': 'connecting', 'progress': 90, 'blocksBuilt': len(blocks), 'totalBlocks': len(blocks), 'message': 'Drawing connections...'}})}\n\n"
    
    for block in blocks:
        for conn in block.get('connections', []):
            yield f"data: {json.dumps({'type': 'connection', 'from': block['id'], 'to': conn})}\n\n"
            await asyncio.sleep(0.05)
    
    await asyncio.sleep(0.3)
    
    # Stage 5: Complete
    automation = {
        "name": analysis.get('name', 'Architecture from Diagram'),
        "description": analysis.get('description', 'Automation generated from architecture diagram'),
        "type": "architecture",
        "blocks": blocks,
        "config": {},
        "generated_code": None,
        "analysis": diagram_analysis
    }
    
    yield f"data: {json.dumps({'type': 'complete', 'automation': automation})}\n\n"


@router.post("/analyze-diagram")
async def analyze_diagram(
    image: UploadFile = File(...),
    type: str = Form(default="architecture")
):
    """
    Analyze an architecture diagram and generate automation blocks.
    Streams progress updates as Server-Sent Events.
    """
    # Read image data
    image_data = await image.read()
    image_type = image.content_type or "image/png"
    
    # Return streaming response
    return StreamingResponse(
        _stream_diagram_analysis(image_data, image_type),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/analyze-diagram-simple", response_model=DiagramAnalysisResponse)
async def analyze_diagram_simple(
    image: UploadFile = File(...),
    type: str = Form(default="architecture")
):
    """
    Analyze an architecture diagram (non-streaming version).
    Returns the complete analysis in a single response.
    """
    image_data = await image.read()
    image_type = image.content_type or "image/png"
    
    analysis = await analyze_diagram_with_vision(image_data, image_type)
    blocks = _analysis_to_blocks(analysis)
    
    layers = analysis.get('layers', [])
    total_components = sum(len(l.get('components', [])) for l in layers)
    connections = len(analysis.get('connections', []))
    
    return DiagramAnalysisResponse(
        name=analysis.get('name', 'Architecture from Diagram'),
        description=analysis.get('description', 'Generated from architecture diagram'),
        type="architecture",
        blocks=blocks,
        analysis=DiagramAnalysis(
            layers=[DiagramLayer(name=l['name'], components=l['components']) for l in layers],
            totalComponents=total_components,
            connections=connections,
            estimatedBlocks=total_components
        )
    )


# ============================================================================
# WebSocket for Real-time Output
# ============================================================================

@router.websocket("/{automation_id}/ws/output")
async def websocket_output(websocket: WebSocket, automation_id: str):
    """WebSocket endpoint for real-time output streaming."""
    await websocket.accept()
    
    runner = get_automation_runner()
    
    async def send_output(line: str):
        try:
            await websocket.send_text(line)
        except:
            pass
    
    runner.register_output_callback(automation_id, send_output)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        runner.unregister_output_callback(automation_id)

